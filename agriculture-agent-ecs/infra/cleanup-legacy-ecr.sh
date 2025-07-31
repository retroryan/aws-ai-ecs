#!/bin/bash

# Script to clean up legacy ECR repositories from the old multi-server architecture

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"

echo "=================================================="
echo "Legacy ECR Repository Cleanup"
echo "=================================================="
echo ""

# Check required tools
if ! check_aws_cli || ! check_aws_credentials; then
    exit 1
fi

# Get current AWS configuration
CURRENT_REGION=$(get_aws_region)
ACCOUNT_ID=$(get_aws_account_id)

if [ -z "$ACCOUNT_ID" ]; then
    log_error "Unable to get AWS account ID"
    exit 1
fi

if [ "$CURRENT_REGION" = "not set" ]; then
    log_error "AWS region is not set"
    log_warn "Set region with: export AWS_REGION=us-east-1"
    exit 1
fi

echo "📋 AWS Configuration:"
echo "--------------------"
echo "Account ID: ${ACCOUNT_ID}"
echo "Region: ${CURRENT_REGION}"
echo ""

# Define legacy repositories
LEGACY_REPOS=(
    "${ECR_FORECAST_REPO}"
    "${ECR_HISTORICAL_REPO}"
    "${ECR_AGRICULTURAL_REPO}"
)

echo "🔍 Checking for legacy repositories:"
echo "-----------------------------------"

REPOS_TO_DELETE=()

for repo in "${LEGACY_REPOS[@]}"; do
    echo -n "Repository ${repo}: "
    
    if check_ecr_repository "${repo}" "${CURRENT_REGION}"; then
        echo -e "${YELLOW}⚠️  Found${NC}"
        REPOS_TO_DELETE+=("${repo}")
    else
        echo -e "${GREEN}✅ Already removed${NC}"
    fi
done

if [ ${#REPOS_TO_DELETE[@]} -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ No legacy repositories found. Cleanup complete!${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}⚠️  WARNING: This will permanently delete the following repositories:${NC}"
echo ""
for repo in "${REPOS_TO_DELETE[@]}"; do
    echo "   - ${repo}"
    
    # Show image count
    IMAGE_COUNT=$(aws ecr list-images \
        --repository-name "${repo}" \
        --region "${CURRENT_REGION}" \
        --query 'length(imageIds)' \
        --output text 2>/dev/null || echo "0")
    
    echo "     (Contains ${IMAGE_COUNT} images)"
done

echo ""
echo "These repositories are from the old multi-server architecture and are no longer needed."
echo "The consolidated architecture only uses:"
echo "   - ${ECR_MAIN_REPO}"
echo "   - ${ECR_WEATHER_REPO}"
echo ""
read -p "Are you sure you want to delete these legacy repositories? (yes/no): " -r
echo ""

if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Deletion cancelled"
    exit 0
fi

# Delete repositories
echo "🗑️  Deleting legacy repositories..."
echo "----------------------------------"

DELETE_FAILED=false

for repo in "${REPOS_TO_DELETE[@]}"; do
    echo -n "Deleting ${repo}... "
    
    if aws ecr delete-repository \
        --repository-name "${repo}" \
        --force \
        --region "${CURRENT_REGION}" \
        --output text >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Deleted${NC}"
    else
        echo -e "${RED}❌ Failed${NC}"
        DELETE_FAILED=true
    fi
done

echo ""
echo "=================================================="

if [ "$DELETE_FAILED" = true ]; then
    log_error "Failed to delete some repositories"
    exit 1
else
    log_info "✅ Legacy repository cleanup complete!"
    echo ""
    echo "The project now uses the consolidated architecture with:"
    echo "   - ${ECR_MAIN_REPO} (main application)"
    echo "   - ${ECR_WEATHER_REPO} (unified MCP server)"
fi