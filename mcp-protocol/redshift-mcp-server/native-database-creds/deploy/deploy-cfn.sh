#!/bin/bash
# Package + upload the MCP server, then deploy the CloudFormation stack.
# Usage: ./deploy-cfn.sh   (run from the repo dir; reads ./deploy.env)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../redshift-mcp" && pwd)"
cd "$REPO_ROOT"
source "$SCRIPT_DIR/deploy.env"

echo "==> 1. Package and upload to s3://$S3_BUCKET/$S3_KEY"
tar -czf redshift-mcp.tar.gz server.py redshift.py requirements.txt
aws s3 cp redshift-mcp.tar.gz "s3://$S3_BUCKET/$S3_KEY" --region "$AWS_REGION"

echo "==> 2. Deploy CloudFormation stack: $STACK_NAME"
# Resolve the managed prefix list for CloudFront origin-facing IP ranges (region-specific).
CF_PL=$(aws ec2 describe-managed-prefix-lists --region "$AWS_REGION" \
  --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing \
  --query 'PrefixLists[0].PrefixListId' --output text)
echo "    CloudFront origin prefix list: $CF_PL"

aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$SCRIPT_DIR/infra.yaml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    VpcId="$VPC_ID" \
    PublicSubnetIds="$PUBLIC_SUBNET_IDS" \
    PrivateSubnetId="$EC2_SUBNET_ID" \
    InstanceType="$INSTANCE_TYPE" \
    S3Bucket="$S3_BUCKET" \
    S3Key="$S3_KEY" \
    Ec2SecurityGroupName="$EC2_SECURITY_GROUP_NAME" \
    AlbSecurityGroupName="$ALB_SECURITY_GROUP_NAME" \
    InstanceProfileName="$EC2_INSTANCE_PROFILE_NAME" \
    CloudFrontPrefixListId="$CF_PL" \
    RsHost="$RS_HOST" \
    RsPort="$RS_PORT" \
    RsDb="$RS_DB" \
    RedshiftSecurityGroupId="$REDSHIFT_SG_ID" \
    CwLogGroup="$CW_LOG_GROUP"

echo "==> Stack outputs:"
aws cloudformation describe-stacks --region "$AWS_REGION" --stack-name "$STACK_NAME" \
  --query 'Stacks[0].Outputs' --output table
