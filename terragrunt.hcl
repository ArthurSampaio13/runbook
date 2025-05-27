locals {
  trusted_account_id = get_env("TRUSTED_ACCOUNT_ID", "")
  region            = get_env("AWS_DEFAULT_REGION", "us-east-1")
  
  account_vars = read_terragrunt_config(find_in_parent_folders("account.hcl"))
  region_vars  = read_terragrunt_config(find_in_parent_folders("region.hcl"))
  
  account_id = local.account_vars.locals.account_id
  role_name  = "RunbookGeneratorRole"
}

remote_state {
  backend = "s3"
  config = {
    bucket         = "terraform-state-${local.account_id}-${local.region}"
    key            = "runbook-generator/${path_relative_to_include()}/terraform.tfstate"
    region         = local.region
    encrypt        = true
    dynamodb_table = "terraform-locks-${local.account_id}"
  }
  
  generate = {
    path      = "backend.tf"
    if_exists = "overwrite_terragrunt"
  }
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
provider "aws" {
  region = "${local.region}"
  
  default_tags {
    tags = {
      Project     = "AWS-Runbook-Generator"
      Environment = "${local.account_vars.locals.environment}"
      ManagedBy   = "Terragrunt"
      Account     = "${local.account_id}"
    }
  }
}
EOF
}

terraform {
  source = "../../terraform"
}

inputs = {
  trusted_account_id = local.trusted_account_id
  role_name         = local.role_name
  external_id       = get_env("EXTERNAL_ID", null)
}

dependencies {
  paths = []
}

terraform {
  before_hook "validate_account" {
    commands = ["plan", "apply"]
    execute  = ["bash", "-c", "aws sts get-caller-identity"]
  }
  
  after_hook "output_role_info" {
    commands     = ["apply"]
    execute      = ["bash", "-c", "echo 'Role deployed successfully. Use this ARN for cross-account access.'"]
    run_on_error = false
  }
}