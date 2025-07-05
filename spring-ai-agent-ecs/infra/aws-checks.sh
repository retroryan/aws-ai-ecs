#!/bin/bash

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"

echo "=================================================="
echo "AWS Configuration Check for Spring AI Agent"
echo "=================================================="
echo ""

# Change to parent directory (from infra/ to project root)
cd "$(dirname "$0")/.."

# 1. Display current AWS profile and region
echo "📋 Current AWS Configuration:"
echo "-----------------------------"

# Get current profile
CURRENT_PROFILE=$(aws configure list-profiles | grep -E "^\*" | sed 's/\* //' || echo "${AWS_PROFILE:-default}")
echo "Profile: ${CURRENT_PROFILE}"

# Get current region
CURRENT_REGION=$(get_aws_region)
echo "Region: ${CURRENT_REGION}"

# Check if credentials are configured
if check_aws_credentials; then
    echo -e "Credentials: ${GREEN}✅ Configured${NC}"
else
    echo -e "Credentials: ${RED}❌ Not configured${NC}"
fi

echo ""

# 2. Check required region
echo "🌍 Region Validation:"
echo "--------------------"

# Read required region from application.properties
REQUIRED_REGION=$(grep "spring.ai.bedrock.aws.region" client/src/main/resources/application.properties 2>/dev/null | cut -d'=' -f2 | tr -d ' ')

if [ -z "$REQUIRED_REGION" ]; then
    REQUIRED_REGION="us-east-1"  # Default from the config
fi

echo "Required region: ${REQUIRED_REGION}"

if [ "$CURRENT_REGION" = "$REQUIRED_REGION" ]; then
    echo -e "Region match: ${GREEN}✅ Correct${NC}"
else
    echo -e "Region match: ${RED}❌ Mismatch${NC}"
    echo -e "${YELLOW}💡 Set region to ${REQUIRED_REGION} using: export AWS_REGION=${REQUIRED_REGION}${NC}"
fi

echo ""

# 3. Check Bedrock model access
echo "🤖 Bedrock Model Access Check:"
echo "------------------------------"

# Required models from application.properties
NOVA_MODEL="amazon.nova-pro-v1:0"

# Check Bedrock access and specific model
if check_bedrock_access "$REQUIRED_REGION" "$NOVA_MODEL"; then
    echo -e "Amazon Nova Pro (${NOVA_MODEL}): ${GREEN}✅ Available${NC}"
else
    echo -e "Amazon Nova Pro (${NOVA_MODEL}): ${RED}❌ Not available${NC}"
    exit 1
fi

echo ""

# 4. List all available models
echo "📝 Available Bedrock Models in ${REQUIRED_REGION}:"
echo "----------------------------------------"

MODEL_COUNT=$(aws bedrock list-foundation-models --region "$REQUIRED_REGION" --output json | jq '.modelSummaries | length')
echo "Total models available: ${MODEL_COUNT}"

# Show Amazon models
echo ""
echo "Amazon models:"
aws bedrock list-foundation-models --region "$REQUIRED_REGION" --output json | \
    jq -r '.modelSummaries[] | select(.providerName == "Amazon") | "  - \(.modelId)"'

echo ""

# 5. Check ECR repositories for AWS deployment
echo "🐳 ECR Repository Check (for AWS deployment):"
echo "--------------------------------------------"

# Check if ECR repositories exist
ECR_REPOS_EXIST=true

echo -n "ECR repository '${ECR_CLIENT_REPO}': "
if check_ecr_repository "${ECR_CLIENT_REPO}" "$REQUIRED_REGION"; then
    echo -e "${GREEN}✅ Exists${NC}"
else
    echo -e "${YELLOW}⚠️  Not found${NC}"
    ECR_REPOS_EXIST=false
fi

echo -n "ECR repository '${ECR_SERVER_REPO}': "
if check_ecr_repository "${ECR_SERVER_REPO}" "$REQUIRED_REGION"; then
    echo -e "${GREEN}✅ Exists${NC}"
else
    echo -e "${YELLOW}⚠️  Not found${NC}"
    ECR_REPOS_EXIST=false
fi

if [ "$ECR_REPOS_EXIST" = false ]; then
    echo ""
    echo -e "${YELLOW}💡 To create ECR repositories for AWS deployment, run: ./infra/setup-ecr.sh${NC}"
fi

echo ""
echo "=================================================="
echo "✨ Check complete!"
echo ""

# Summary
ALL_GOOD=true
DEPLOYMENT_READY=true

if [ "$CURRENT_REGION" != "$REQUIRED_REGION" ]; then
    ALL_GOOD=false
fi

if ! aws bedrock list-foundation-models --region "$REQUIRED_REGION" --output json | jq -e ".modelSummaries[] | select(.modelId == \"${NOVA_MODEL}\")" >/dev/null 2>&1; then
    ALL_GOOD=false
fi

if [ "$ECR_REPOS_EXIST" = false ]; then
    DEPLOYMENT_READY=false
fi

if [ "$ALL_GOOD" = true ]; then
    echo -e "${GREEN}✅ All core checks passed! You're ready to run the application locally.${NC}"
    if [ "$DEPLOYMENT_READY" = false ]; then
        echo -e "${YELLOW}⚠️  For AWS deployment: Run ./infra/setup-ecr.sh to create ECR repositories${NC}"
    else
        echo -e "${GREEN}✅ ECR repositories exist - ready for AWS deployment${NC}"
    fi
else
    echo -e "${RED}❌ Some checks failed. Please fix the issues above before running the application.${NC}"
fi

echo "=================================================="