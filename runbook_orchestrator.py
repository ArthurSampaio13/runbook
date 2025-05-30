import os
import subprocess
import boto3
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AWSRunbookGenerator:
    def __init__(self):
        self.output_dir = Path("./output")
        self.output_dir.mkdir(exist_ok=True)
        
        session = boto3.session.Session()
        sts_client = session.client("sts")
        self.current_account = sts_client.get_caller_identity()["Account"]
        
        self.target_accounts = [self.current_account]
        self.regions = os.getenv("REGIONS_TO_SCAN", "sa-east-1").split(",")
        self.max_workers = int(os.getenv("MAX_WORKERS", "5"))
        logger.info(f"Operating exclusively on AWS Account: {self.current_account}")
        
    def run_collection(self, account_id, region):
        """Run data collection for a specific account/region combination"""
        try:
            env_vars = {}
            env = os.environ.copy()
            env.update(env_vars)
            env["AWS_DEFAULT_REGION"] = region
            env["ACCOUNT_ID"] = account_id
            logger.info(f"Collecting data for Account: {account_id}, Region: {region}")
            result = subprocess.run(
                ["bash", "./collect_aws_info.sh"],
                capture_output=True,
                text=True,
                env=env,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(
                    f"Collection failed for {account_id}/{region}: {result.stderr}"
                )
                return None
            output_file = f"runbook_{account_id}_{region}.md"
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    content = f.read()
                os.remove(output_file)
                return content
            else:
                logger.warning(f"Output file not found for {account_id}/{region}")
                return None
        except subprocess.TimeoutExpired:
            logger.error(f"Collection timeout for {account_id}/{region}")
            return None
        except Exception as e:
            logger.error(f"Error collecting data for {account_id}/{region}: {e}")
            return None

    def generate_master_runbook(self, results):
        """Generate the master runbook combining all results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_file = self.output_dir / f"aws_infrastructure_runbook_{timestamp}.md"
        header = f"""# AWS Infrastructure Runbook
                    Organization Overview
                    - Total Accounts Scanned: {len(self.target_accounts)}
                    - Regions Scanned: {', '.join(self.regions)} 
                    """
        valid_results = [result for result in results if result is not None]
        if not valid_results:
            logger.error("No valid results to generate runbook")
            return None
        with open(md_file, "w") as f:
            f.write(header)
            f.write("\n\n---\n\n".join(valid_results))
        logger.info(f"Master runbook generated: {md_file}")
        return md_file

    def convert_to_docx(self, md_file):
        """Convert markdown to DOCX using pandoc"""
        if not md_file:
            logger.error("Markdown file path is None. Cannot convert to DOCX.")
            return None
        docx_file = md_file.with_suffix(".docx")
        try:
            try:
                subprocess.run(
                    ["pandoc", "--version"], capture_output=True, text=True, check=True
                )
            except FileNotFoundError:
                logger.error(
                    "Pandoc command not found. Please install pandoc and ensure it's in your PATH."
                )
                return None
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Pandoc --version check failed: {e.stderr or e.stdout or str(e)}. Ensure pandoc is correctly installed."
                )
                return None
            pandoc_conversion_cmd = [
                "pandoc",
                str(md_file),
                "-o",
                str(docx_file),
                "--from",
                "markdown",
                "--to",
                "docx",
                "--highlight-style",
                "tango",
            ]
            reference_doc_path = self._get_reference_doc()
            if reference_doc_path:
                pandoc_conversion_cmd.extend(["--reference-doc", reference_doc_path])
            subprocess.run(
                pandoc_conversion_cmd, capture_output=True, text=True, check=True
            )
            logger.info(f"DOCX file generated: {docx_file}")
            return docx_file
        except subprocess.CalledProcessError as e:
            logger.error(
                f"Pandoc conversion failed for '{md_file}'. Error: {e.stderr.strip() if e.stderr else (e.stdout.strip() if e.stdout else str(e))}"
            )
            return None

    def _get_reference_doc(self):
        """Get reference document path for pandoc styling"""
        ref_doc = self.output_dir / "reference.docx"
        if ref_doc.exists():
            return str(ref_doc)
        else:
            logger.info(
                f"Reference DOCX 'reference.docx' not found in {self.output_dir}. Pandoc will use default styling."
            )
            return None

    def run(self):
        """Main execution method"""
        logger.info("Starting AWS Infrastructure Runbook generation")
        logger.info(f"Target accounts: {self.target_accounts}")
        logger.info(f"Target regions: {self.regions}")
        tasks = []
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for account in self.target_accounts:
                for region in self.regions:
                    future = executor.submit(self.run_collection, account, region)
                    tasks.append(future)
            for future in as_completed(tasks):
                result = future.result()
                if result:
                    results.append(result)
        if not results:
            logger.error("No data collected. Exiting.")
            return
        md_file = self.generate_master_runbook(results)
        if not md_file:
            return
        docx_file = self.convert_to_docx(md_file)
        logger.info("=" * 50)
        logger.info("RUNBOOK GENERATION COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Markdown file: {md_file}")
        if docx_file:
            logger.info(f"DOCX file: {docx_file}")
        logger.info(
            f"Successfully processed {len(results)} account/region combinations"
        )


def main():
    """Main entry point"""
    try:
        generator = AWSRunbookGenerator()
        generator.run()
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
