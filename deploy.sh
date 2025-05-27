#!/bin/bash
# deploy.sh - Script para deployment da infraestrutura

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
ACCOUNTS_FILE="$PROJECT_ROOT/config/accounts.txt"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    log_info "Checking dependencies..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install it."
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform not found. Please install it."
        exit 1
    fi
    
    # Check Terragrunt (optional)
    if command -v terragrunt &> /dev/null; then
        log_info "Terragrunt found - will use for advanced deployment"
        USE_TERRAGRUNT=true
    else
        log_warn "Terragrunt not found - using basic Terraform"
        USE_TERRAGRUNT=false
    fi
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        log_error "jq not found. Please install it."
        exit 1
    fi
    
    # Check pandoc (optional)
    if ! command -v pandoc &> /dev/null; then
        log_warn "Pandoc not found. DOCX conversion will not be available."
    fi
    
    log_info "Dependencies check completed"
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create necessary directories
    mkdir -p "$PROJECT_ROOT/output"
    mkdir -p "$PROJECT_ROOT/config"
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Set up logging
    export LOG_FILE="$PROJECT_ROOT/logs/deployment_$(date +%Y%m%d_%H%M%S).log"
    
    # Get current account info
    CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    CURRENT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
    
    log_info "Current Account: $CURRENT_ACCOUNT"
    log_info "Current Region: $CURRENT_REGION"
    
    # Set trusted account ID for cross-account roles
    export TRUSTED_ACCOUNT_ID=${TRUSTED_ACCOUNT_ID:-$CURRENT_ACCOUNT}
}

deploy_cross_account_roles() {
    log_info "Deploying cross-account roles..."
    
    if [ ! -f "$ACCOUNTS_FILE" ]; then
        log_warn "Accounts file not found. Creating sample file..."
        cat > "$ACCOUNTS_FILE" << EOF
# List of target account IDs (one per line)
# Lines starting with # are comments
$CURRENT_ACCOUNT
EOF
        log_info "Sample accounts file created at: $ACCOUNTS_FILE"
        log_info "Please edit this file to add your target accounts"
    fi
    
    # Read accounts from file
    accounts=$(grep -v '^#' "$ACCOUNTS_FILE" | grep -v '^$' | tr '\n' ' ')
    
    if [ -z "$accounts" ]; then
        log_error "No accounts found in $ACCOUNTS_FILE"
        exit 1
    fi
    
    log_info "Target accounts: $accounts"
    
    # Deploy to each account
    for account in $accounts; do
        log_info "Deploying to account: $account"
        
        if [ "$USE_TERRAGRUNT" = true ]; then
            deploy_with_terragrunt "$account"
        else
            deploy_with_terraform "$account"
        fi
    done
}

deploy_with_terraform() {
    local account_id=$1
    local work_dir="$PROJECT_ROOT/terraform-state/$account_id"
    
    mkdir -p "$work_dir"
    cd "$work_dir"
    
    # Copy terraform files
    cp -r "$TERRAFORM_DIR"/* .
    
    # Initialize and apply
    terraform init
    terraform plan \
        -var="trusted_account_id=$TRUSTED_ACCOUNT_ID" \
        -var="role_name=RunbookGeneratorRole" \
        -out=tfplan
    
    terraform apply tfplan
    
    # Save outputs
    terraform output -json > outputs.json
    
    cd "$PROJECT_ROOT"
}

deploy_with_terragrunt() {
    local account_id=$1
    log_info "Using Terragrunt for account: $account_id"
    # Terragrunt deployment logic would go here
    # This is a placeholder for more advanced scenarios
}

generate_runbook() {
    log_info "Generating AWS Infrastructure Runbook..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables
    export TARGET_ACCOUNTS=$(grep -v '^#' "$ACCOUNTS_FILE" | grep -v '^$' | tr '\n' ',' | sed 's/,$//')
    export REGIONS_TO_SCAN=${REGIONS_TO_SCAN:-us-east-1,us-west-2}
    export CROSS_ACCOUNT_ROLE=${CROSS_ACCOUNT_ROLE:-RunbookGeneratorRole}
    
    log_info "Target Accounts: $TARGET_ACCOUNTS"
    log_info "Target Regions: $REGIONS_TO_SCAN"
    
    # Run the Python orchestrator
    python3 runbook_orchestrator.py
    
    log_info "Runbook generation completed"
}

cleanup() {
    log_info "Cleaning up temporary files..."
    find "$PROJECT_ROOT" -name "runbook_*.md" -not -path "*/output/*" -delete 2>/dev/null || true
    log_info "Cleanup completed"
}

show_usage() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    setup       - Setup environment and check dependencies
    deploy      - Deploy cross-account roles
    generate    - Generate runbook
    all         - Run setup, deploy, and generate
    cleanup     - Clean up temporary files
    help        - Show this help message

Environment Variables:
    TRUSTED_ACCOUNT_ID  - Account ID that will assume roles (default: current account)
    REGIONS_TO_SCAN     - Comma-separated list of regions (default: us-east-1,us-west-2)
    CROSS_ACCOUNT_ROLE  - Name of cross-account role (default: RunbookGeneratorRole)

Examples:
    $0 all                                    # Full deployment and generation
    REGIONS_TO_SCAN=us-east-1 $0 generate   # Generate for specific region
    $0 cleanup                               # Clean up temporary files
EOF
}

main() {
    local command=${1:-help}
    
    case "$command" in
        setup)
            check_dependencies
            setup_environment
            ;;
        deploy)
            check_dependencies
            setup_environment
            deploy_cross_account_roles
            ;;
        generate)
            check_dependencies
            setup_environment
            generate_runbook
            cleanup
            ;;
        all)
            check_dependencies
            setup_environment
            deploy_cross_account_roles
            generate_runbook
            cleanup
            log_info "All operations completed successfully!"
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"