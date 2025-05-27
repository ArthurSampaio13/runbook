#!/bin/bash
set -e

ACCOUNT_ID=${ACCOUNT_ID:-"$(aws sts get-caller-identity --query Account --output text)"}
REGION=${AWS_DEFAULT_REGION:-"us-east-1"}
OUTPUT_FILE="runbook_${ACCOUNT_ID}_${REGION}.md"

echo "# AWS Infrastructure Runbook" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "**Account ID:** $ACCOUNT_ID" >> "$OUTPUT_FILE"
echo "**Region:** $REGION" >> "$OUTPUT_FILE"
echo "**Generated:** $(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

add_section() {
  local title="$1"
  local content="$2"
  
  echo "## $title" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
  echo "$content" >> "$OUTPUT_FILE"
  echo "" >> "$OUTPUT_FILE"
}

safe_aws_call() {
  local service="$1"
  local command="$2"
  
  if ! $command 2>/dev/null; then
    echo "| Service | Status |"
    echo "|---------|--------|"
    echo "| $service | Access Denied or Service Unavailable |"
  fi
}

echo "Collecting AWS infrastructure information for Account: $ACCOUNT_ID, Region: $REGION"

echo "Checking AWS Organizations..."
org_content=$(safe_aws_call "Organizations" "aws organizations describe-organization --query 'Organization.{Id:Id,MasterEmail:MasterAccountEmail,MasterId:MasterAccountId}' --output json | jq -r '[\"| Organization ID | Master Email | Master Account ID |\", \"|---------------|--------------|----------------|\", \"| \\(.Id) | \\(.MasterEmail) | \\(.MasterId) |\"] | .[]'")
add_section "AWS Organization" "$org_content"

echo "Collecting VPC information..."
vpcs_content=$(aws ec2 describe-vpcs --region "$REGION" --query "Vpcs[].{VpcId:VpcId,CidrBlock:CidrBlock,State:State,IsDefault:IsDefault}" --output json | jq -r '[
  "| VPC ID | CIDR Block | State | Default |",
  "|--------|------------|-------|---------|"
] + (map("| \(.VpcId) | \(.CidrBlock) | \(.State) | \(.IsDefault) |")) | .[]')
add_section "VPC Summary" "$vpcs_content"

echo "Collecting subnet information..."
subnets_content=$(aws ec2 describe-subnets --region "$REGION" --query "Subnets[].{SubnetId:SubnetId,VpcId:VpcId,CidrBlock:CidrBlock,AvailabilityZone:AvailabilityZone,MapPublicIpOnLaunch:MapPublicIpOnLaunch}" --output json | jq -r '[
  "| Subnet ID | VPC ID | CIDR Block | Availability Zone | Public IP on Launch |",
  "|-----------|--------|------------|-------------------|---------------------|"
] + (map("| \(.SubnetId) | \(.VpcId) | \(.CidrBlock) | \(.AvailabilityZone) | \(.MapPublicIpOnLaunch) |")) | .[]')
add_section "Subnets" "$subnets_content"

echo "Collecting EC2 instances..."
ec2_content=$(aws ec2 describe-instances --region "$REGION" --query "Reservations[].Instances[].{InstanceId:InstanceId,InstanceType:InstanceType,State:State.Name,AvailabilityZone:Placement.AvailabilityZone,LaunchTime:LaunchTime,Tags:Tags[?Key=='Name'].Value|[0]}" --output json | jq -r '[
  "| Instance ID | Name | Type | State | AZ | Launch Time |",
  "|-------------|------|------|-------|----|-----------  |"
] + (map("| \(.InstanceId) | \((.Tags | if . == null then "N/A" else . end)) | \(.InstanceType) | \(.State) | \(.AvailabilityZone) | \(.LaunchTime) |")) | .[]')
add_section "EC2 Instances" "$ec2_content"

echo "Collecting Lambda functions..."
lambda_content=$(aws lambda list-functions --region "$REGION" --query "Functions[].{FunctionName:FunctionName,Runtime:Runtime,Handler:Handler,CodeSize:CodeSize,LastModified:LastModified}" --output json | jq -r '[
  "| Function Name | Runtime | Handler | Code Size (bytes) | Last Modified |",
  "|---------------|---------|---------|-------------------|---------------|"
] + (map("| \(.FunctionName) | \(.Runtime) | \(.Handler) | \(.CodeSize) | \(.LastModified) |")) | .[]')
add_section "Lambda Functions" "$lambda_content"

echo "Collecting RDS instances..."
rds_content=$(aws rds describe-db-instances --region "$REGION" --query "DBInstances[].{DBInstanceIdentifier:DBInstanceIdentifier,DBInstanceStatus:DBInstanceStatus,Engine:Engine,EngineVersion:EngineVersion,DBInstanceClass:DBInstanceClass,AllocatedStorage:AllocatedStorage}" --output json | jq -r '[
  "| DB Instance ID | Status | Engine | Version | Class | Storage (GB) |",
  "|----------------|--------|--------|---------|-------|--------------|"
] + (map("| \(.DBInstanceIdentifier) | \(.DBInstanceStatus) | \(.Engine) | \(.EngineVersion) | \(.DBInstanceClass) | \(.AllocatedStorage) |")) | .[]')
add_section "RDS Instances" "$rds_content"

echo "Collecting API Gateway..."
apigw_content=$(safe_aws_call "API Gateway" "aws apigateway get-rest-apis --region '$REGION' --query 'items[].{name:name,id:id,createdDate:createdDate}' --output json | jq -r '[
  \"| API Name | API ID | Created Date |\",
  \"|----------|--------|--------------|\"
] + (map(\"| \\(.name) | \\(.id) | \\(.createdDate) |\")) | .[]'")
add_section "API Gateway" "$apigw_content"

echo "Collecting CloudFront distributions..."
cf_content=$(aws cloudfront list-distributions --query "DistributionList.Items[].{Id:Id,DomainName:DomainName,Status:Status,PriceClass:PriceClass}" --output json | jq -r '[
  "| Distribution ID | Domain Name | Status | Price Class |",
  "|-----------------|-------------|--------|-------------|"
] + (map("| \(.Id) | \(.DomainName) | \(.Status) | \(.PriceClass) |")) | .[]')
add_section "CloudFront Distributions" "$cf_content"

echo "Collecting Load Balancers..."
lb_content=$(aws elbv2 describe-load-balancers --region "$REGION" --query "LoadBalancers[].{LoadBalancerName:LoadBalancerName,Type:Type,State:State.Code,Scheme:Scheme,VpcId:VpcId}" --output json | jq -r '[
  "| Load Balancer Name | Type | State | Scheme | VPC ID |",
  "|--------------------|------|-------|--------|--------|"
] + (map("| \(.LoadBalancerName) | \(.Type) | \(.State) | \(.Scheme) | \(.VpcId) |")) | .[]')
add_section "Load Balancers" "$lb_content"

echo "Collecting ECS clusters..."
ecs_content=$(aws ecs list-clusters --region "$REGION" --query "clusterArns[]" --output json | jq -r '[
  "| Cluster ARN |",
  "|-------------|"
] + (map("| \(.) |")) | .[]')
add_section "ECS Clusters" "$ecs_content"

echo "Collecting SNS topics..."
sns_content=$(aws sns list-topics --region "$REGION" --query "Topics[].TopicArn" --output json | jq -r '[
  "| Topic ARN |",
  "|-----------|"
] + (map("| \(.) |")) | .[]')
add_section "SNS Topics" "$sns_content"

echo "Collecting EventBridge rules..."
eb_content=$(aws events list-rules --region "$REGION" --query "Rules[].{Name:Name,State:State,Description:Description}" --output json | jq -r '[
  "| Rule Name | State | Description |",
  "|-----------|-------|-------------|"
] + (map("| \(.Name) | \(.State) | \((.Description | if . == null then "N/A" else . end)) |")) | .[]')
add_section "EventBridge Rules" "$eb_content"

echo "Collecting AWS Backup vaults..."
backup_content=$(aws backup list-backup-vaults --region "$REGION" --query "BackupVaultList[].{BackupVaultName:BackupVaultName,NumberOfRecoveryPoints:NumberOfRecoveryPoints,BackupVaultArn:BackupVaultArn}" --output json | jq -r '[
  "| Vault Name | Recovery Points | Vault ARN |",
  "|------------|-----------------|-----------|"
] + (map("| \(.BackupVaultName) | \(.NumberOfRecoveryPoints) | \(.BackupVaultArn) |")) | .[]')
add_section "AWS Backup Vaults" "$backup_content"

echo "Collecting IAM users..."
iam_content=$(aws iam list-users --query "Users[].{UserName:UserName,UserId:UserId,Arn:Arn,CreateDate:CreateDate}" --output json | jq -r '[
  "| User Name | User ID | ARN | Created Date |",
  "|-----------|---------|-----|--------------|"
] + (map("| \(.UserName) | \(.UserId) | \(.Arn) | \(.CreateDate) |")) | .[]')
add_section "IAM Users" "$iam_content"

echo "AWS infrastructure data collection completed for Account: $ACCOUNT_ID, Region: $REGION"
echo "Output file: $OUTPUT_FILE"