#!/bin/bash
set -e

ACCOUNT_ID=${ACCOUNT_ID:-"$(aws sts get-caller-identity --query Account --output text)"}
REGION=${AWS_DEFAULT_REGION:-"us-east-1"}
OUTPUT_FILE="runbook_${ACCOUNT_ID}_${REGION}.md"

echo "# 📄 AWS Runbook" > "$OUTPUT_FILE"
echo "**Account:** $ACCOUNT_ID" >> "$OUTPUT_FILE"
echo "**Region:** $REGION" >> "$OUTPUT_FILE"
echo "**Generated:** $(date)" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

add_section() {
  local title="$1"
  local header="$2"
  local data="$3"

  echo "## $title" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  echo "$header" >> "$OUTPUT_FILE"
  echo "$data" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
}

# AWS Organizations
org=$(aws organizations describe-organization --query "Organization.{Id:Id, MasterEmail:MasterAccountEmail, MasterId:MasterAccountId}" --output json || echo "{}")
org_table=$(echo "$org" | jq -r '["| Id | MasterEmail | MasterId |", "|----|-------------|----------|", "| \(.Id) | \(.MasterEmail) | \(.MasterId) |"] | .[]')
add_section "🏢 AWS Organizations" "$org_table" ""

# VPC
vpcs=$(aws ec2 describe-vpcs --region "$REGION" --query "Vpcs[].{VpcId:VpcId,Cidr:CidrBlock}" --output json)
vpcs_table=$(echo "$vpcs" | jq -r '[ "| VpcId | Cidr |", "|-------|------|"] + (map("| \(.VpcId) | \(.Cidr) |")) | .[]')
add_section "🌐 VPC Summary" "$vpcs_table" ""

# EC2
ec2=$(aws ec2 describe-instances --region "$REGION" --query "Reservations[].Instances[].{ID:InstanceId,Type:InstanceType,State:State.Name,AZ:Placement.AvailabilityZone}" --output json)
ec2_table=$(echo "$ec2" | jq -r '[ "| ID | Type | State | AZ |", "|----|------|-------|----|"] + (map("| \(.ID) | \(.Type) | \(.State) | \(.AZ) |")) | .[]')
add_section "💻 EC2 Instances" "$ec2_table" ""

# S3
s3=$(aws s3api list-buckets --query "Buckets[].Name" --output json)
s3_table=$(echo "$s3" | jq -r '[ "| BucketName |", "|------------|"] + (map("| \(.) |")) | .[]')
add_section "🪣 S3 Buckets" "$s3_table" ""

# Lambda
lambda=$(aws lambda list-functions --region "$REGION" --query "Functions[].{Name:FunctionName,Runtime:Runtime}" --output json)
lambda_table=$(echo "$lambda" | jq -r '[ "| Name | Runtime |", "|------|---------|"] + (map("| \(.Name) | \(.Runtime) |")) | .[]')
add_section "🌀 Lambda Functions" "$lambda_table" ""

# RDS
rds=$(aws rds describe-db-instances --region "$REGION" --query "DBInstances[].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Engine:Engine}" --output json)
rds_table=$(echo "$rds" | jq -r '[ "| ID | Status | Engine |", "|----|--------|--------|"] + (map("| \(.ID) | \(.Status) | \(.Engine) |")) | .[]')
add_section "🗄️ RDS Instances" "$rds_table" ""

# API Gateway
apigw=$(aws apigateway get-rest-apis --region "$REGION" --query "items[].{Name:name,ID:id}" --output json)
apigw_table=$(echo "$apigw" | jq -r '[ "| Name | ID |", "|------|----|"] + (map("| \(.Name) | \(.ID) |")) | .[]')
add_section "🌐 API Gateway" "$apigw_table" ""

# CloudFront
cf=$(aws cloudfront list-distributions --query "DistributionList.Items[].{ID:Id,Domain:DomainName}" --output json)
cf_table=$(echo "$cf" | jq -r '[ "| ID | Domain |", "|----|--------|"] + (map("| \(.ID) | \(.Domain) |")) | .[]')
add_section "🚀 CloudFront Distributions" "$cf_table" ""

# SNS
sns=$(aws sns list-topics --region "$REGION" --query "Topics[].TopicArn" --output json)
sns_table=$(echo "$sns" | jq -r '[ "| TopicArn |", "|----------|"] + (map("| \(.) |")) | .[]')
add_section "📣 SNS Topics" "$sns_table" ""

# AWS Backup
backup=$(aws backup list-backup-vaults --region "$REGION" --query "BackupVaultList[].{Name:BackupVaultName,ARN:BackupVaultArn}" --output json)
backup_table=$(echo "$backup" | jq -r '[ "| Name | ARN |", "|------|-----|"] + (map("| \(.Name) | \(.ARN) |")) | .[]')
add_section "💾 AWS Backup Vaults" "$backup_table" ""

# EventBridge
eb=$(aws events list-rules --region "$REGION" --query "Rules[].{Name:Name,State:State}" --output json)
eb_table=$(echo "$eb" | jq -r '[ "| Name | State |", "|------|-------|"] + (map("| \(.Name) | \(.State) |")) | .[]')
add_section "⏰ EventBridge Rules" "$eb_table" ""

# Load Balancer
lb=$(aws elbv2 describe-load-balancers --region "$REGION" --query "LoadBalancers[].{Name:LoadBalancerName,Type:Type,State:State.Code}" --output json)
lb_table=$(echo "$lb" | jq -r '[ "| Name | Type | State |", "|------|------|-------|"] + (map("| \(.Name) | \(.Type) | \(.State) |")) | .[]')
add_section "⚖️ Load Balancers" "$lb_table" ""

# ECS
ecs=$(aws ecs list-clusters --region "$REGION" --query "clusterArns[]" --output json)
ecs_table=$(echo "$ecs" | jq -r '[ "| ClusterArn |", "|------------|"] + (map("| \(.) |")) | .[]')
add_section "🐳 ECS Clusters" "$ecs_table" ""

# IAM Identity Center (SSO)
sso=$(aws sso-admin list-users --region "$REGION" --query "Users[].{Username:Username,Status:Status}" --output json || echo "[]")
sso_table=$(echo "$sso" | jq -r '[ "| Username | Status |", "|----------|--------|"] + (map("| \(.Username) | \(.Status) |")) | .[]')
add_section "👥 IAM Identity Center (SSO) Users" "$sso_table" ""

echo "✅ Runbook generated: $OUTPUT_FILE"
