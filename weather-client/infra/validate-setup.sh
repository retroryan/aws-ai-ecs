#!/bin/bash

# Simple validation and CDK bootstrap script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up CDK...${NC}"

# Get AWS account and region
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=${AWS_DEFAULT_REGION:-$(aws configure get region || echo "us-east-1")}

echo "AWS Account: $ACCOUNT"
echo "AWS Region: $REGION"

# Check for modern CDK bootstrap with the default qualifier
QUALIFIER="hnb659fds"
BOOTSTRAP_VERSION_PARAM="/cdk-bootstrap/${QUALIFIER}/version"

# Check if modern CDK bootstrap exists
if aws ssm get-parameter --name "$BOOTSTRAP_VERSION_PARAM" --region "$REGION" &> /dev/null; then
    VERSION=$(aws ssm get-parameter --name "$BOOTSTRAP_VERSION_PARAM" --region "$REGION" --query 'Parameter.Value' --output text)
    echo -e "${GREEN}✅ CDK already bootstrapped (version: $VERSION)${NC}"
else
    # Check if legacy bootstrap exists
    if aws cloudformation describe-stacks --stack-name CDKToolkit --region "$REGION" &> /dev/null; then
        echo -e "${YELLOW}⚠️  Legacy CDK bootstrap found. Need to upgrade to modern bootstrap.${NC}"
        echo -e "${YELLOW}Running modern CDK bootstrap...${NC}"
    else
        echo -e "${YELLOW}Bootstrapping CDK...${NC}"
    fi
    
    # Run modern bootstrap
    cdk bootstrap aws://$ACCOUNT/$REGION --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess
fi

# Verify the required S3 bucket exists
BUCKET_NAME="cdk-${QUALIFIER}-assets-${ACCOUNT}-${REGION}"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo -e "${GREEN}✅ CDK assets bucket exists: $BUCKET_NAME${NC}"
else
    echo -e "${RED}❌ CDK assets bucket not found: $BUCKET_NAME${NC}"
    echo -e "${YELLOW}Please run: cdk bootstrap aws://$ACCOUNT/$REGION${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Setup complete${NC}"