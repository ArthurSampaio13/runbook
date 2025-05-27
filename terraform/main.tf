terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "trusted_account_id" {
  description = "Account ID that will assume the role for runbook generation"
  type        = string
}

variable "role_name" {
  description = "Name of the cross-account role"
  type        = string
  default     = "RunbookGeneratorRole"
}

variable "external_id" {
  description = "External ID for additional security"
  type        = string
  default     = null
}

resource "aws_iam_role" "runbook_generator_role" {
  name = var.role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.trusted_account_id}:root"
        }
        Condition = var.external_id != null ? {
          StringEquals = {
            "sts:ExternalId" = var.external_id
          }
        } : {}
      }
    ]
  })

  tags = {
    Purpose = "AWS Runbook Generation"
    ManagedBy = "Terraform"
  }
}

resource "aws_iam_policy" "runbook_generator_policy" {
  name        = "RunbookGeneratorPolicy"
  description = "Policy for AWS infrastructure runbook generation"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity",
          
          "organizations:DescribeOrganization",
          "organizations:ListAccounts",
          
          "ec2:DescribeInstances",
          "ec2:DescribeVpcs",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeImages",
          "ec2:DescribeKeyPairs",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
          
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetBucketVersioning",
          "s3:GetBucketEncryption",
          
          "lambda:ListFunctions",
          "lambda:GetFunction",
          "lambda:ListLayers",
          
          "rds:DescribeDBInstances",
          "rds:DescribeDBClusters",
          "rds:DescribeDBSubnetGroups",
          "rds:DescribeDBParameterGroups",
          
          "apigateway:GET",
          
          "cloudfront:ListDistributions",
          "cloudfront:GetDistribution",
          
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          "elasticloadbalancing:DescribeListeners",
          
          "ecs:ListClusters",
          "ecs:DescribeClusters",
          "ecs:ListServices",
          "ecs:DescribeServices",
          
          "sns:ListTopics",
          "sns:GetTopicAttributes",
          
          "events:ListRules",
          "events:DescribeRule",
          
          "backup:ListBackupVaults",
          "backup:DescribeBackupVault",
          
          "iam:ListRoles",
          "iam:ListUsers",
          "iam:ListGroups",
          "iam:ListPolicies",
          
          "cloudwatch:ListMetrics",
          "logs:DescribeLogGroups",
          
          "route53:ListHostedZones",
          "route53:GetHostedZone",
          
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeLaunchConfigurations",
          
          "ssm:DescribeParameters",
          "ssm:GetParameters",
          
          "secretsmanager:ListSecrets",
          
          "cloudformation:ListStacks",
          "cloudformation:DescribeStacks"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "runbook_generator_policy_attachment" {
  role       = aws_iam_role.runbook_generator_role.name
  policy_arn = aws_iam_policy.runbook_generator_policy.arn
}

output "role_arn" {
  description = "ARN of the runbook generator role"
  value       = aws_iam_role.runbook_generator_role.arn
}

output "role_name" {
  description = "Name of the runbook generator role"
  value       = aws_iam_role.runbook_generator_role.name
}