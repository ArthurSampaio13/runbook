import os
import subprocess
import boto3
from datetime import datetime

ACCOUNTS = os.getenv('TARGET_ACCOUNTS', '').split(',') or [boto3.client('sts').get_caller_identity()['Account']]
REGIONS = os.getenv('REGIONS_TO_SCAN', 'us-east-1').split(',')
OUTPUT_DIR = './output'
os.makedirs(OUTPUT_DIR, exist_ok=True)

def assume_role(account_id, role_name="OrganizationAccountAccessRole"):
    sts = boto3.client('sts')
    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="RunbookSession")['Credentials']
    return {
        'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
        'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
        'AWS_SESSION_TOKEN': creds['SessionToken']
    }

def run_collection(account_id, region, env_vars):
    env = os.environ.copy()
    env.update(env_vars)
    env['AWS_DEFAULT_REGION'] = region
    env['ACCOUNT_ID'] = account_id

    print(f"🔍 Coletando {account_id}/{region}")
    result = subprocess.run(['bash', './collect_aws_info.sh'], capture_output=True, text=True, env=env)
    return result.stdout

all_results = []
for acc in ACCOUNTS:
    creds = assume_role(acc) if acc != boto3.client('sts').get_caller_identity()['Account'] else {}
    for reg in REGIONS:
        output = run_collection(acc, reg, creds)
        all_results.append(output)

md_file = os.path.join(OUTPUT_DIR, f'runbook_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md')
with open(md_file, 'w') as f:
    f.write('\n\n---\n\n'.join(all_results))

print(f"✅ Markdown gerado: {md_file}")

try:
    subprocess.run(['pandoc', md_file, '-o', md_file.replace('.md', '.docx')], check=True)
    print(f"✅ DOCX gerado: {md_file.replace('.md', '.docx')}")
except:
    print("⚠️ Pandoc não disponível, apenas Markdown gerado.")
