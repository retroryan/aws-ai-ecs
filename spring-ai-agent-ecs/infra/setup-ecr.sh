#!/bin/bash

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"

# Script configuration
REPOS=("${ECR_SERVER_REPO}" "${ECR_CLIENT_REPO}")
DELETE_MODE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --delete)
            DELETE_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Setup ECR repositories and Docker authentication for Spring AI Agent ECS deployment"
            echo ""
            echo "This script will:"
            echo "  - Create ECR repositories if they don't exist"
            echo "  - Authenticate Docker with ECR"
            echo "  - Can be run multiple times safely"
            echo ""
            echo "Options:"
            echo "  --delete    Remove the ECR repositories"
            echo "  --help      Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "=================================================="
echo "ECR Setup for Spring AI Agent ECS"
echo "=================================================="
echo ""

# Check required tools
if ! check_aws_cli || ! check_aws_credentials || ! check_docker; then
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

if [ "$DELETE_MODE" = true ]; then
    echo -e "${RED}🗑️  DELETE MODE - Removing ECR repositories${NC}"
    echo ""
    
    # Confirm deletion
    echo -e "${YELLOW}⚠️  This will delete the following repositories:${NC}"
    for repo in "${REPOS[@]}"; do
        echo "   - ${repo}"
    done
    echo ""
    read -p "Are you sure you want to delete these repositories? (yes/no): " -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo "Deletion cancelled"
        exit 0
    fi
    
    # Delete repositories
    for repo in "${REPOS[@]}"; do
        echo -n "Deleting repository ${repo}... "
        
        if aws ecr delete-repository --repository-name "${repo}" --force --region "${CURRENT_REGION}" 2>/dev/null; then
            echo -e "${GREEN}✅ Deleted${NC}"
        else
            # Check if repository doesn't exist
            if ! check_ecr_repository "${repo}" "${CURRENT_REGION}"; then
                echo -e "${YELLOW}⚠️  Repository doesn't exist${NC}"
            else
                echo -e "${RED}❌ Failed to delete${NC}"
            fi
        fi
    done
    
    echo ""
    echo "=================================================="
    echo "✨ Deletion complete!"
    echo "=================================================="
    exit 0
fi

# Normal mode - Create repositories and authenticate

# Step 1: Check and create repositories
echo "📦 Step 1: Checking ECR repositories"
echo "-----------------------------------"

REPOS_CREATED=0
REPOS_EXISTING=0

for repo in "${REPOS[@]}"; do
    echo -n "Repository ${repo}: "
    
    # Check if repository already exists
    if check_ecr_repository "${repo}" "${CURRENT_REGION}"; then
        echo -e "${GREEN}✅ Already exists${NC}"
        ((REPOS_EXISTING++))
    else
        # Create the repository
        if create_ecr_repository "${repo}" "${CURRENT_REGION}"; then
            ((REPOS_CREATED++))
        else
            exit 1
        fi
    fi
done

echo ""
if [ $REPOS_CREATED -gt 0 ]; then
    echo -e "${GREEN}Created ${REPOS_CREATED} new repository(ies)${NC}"
fi
if [ $REPOS_EXISTING -gt 0 ]; then
    echo -e "${BLUE}Found ${REPOS_EXISTING} existing repository(ies)${NC}"
fi

# Step 2: Authenticate Docker with ECR
echo ""
echo "🔐 Step 2: Authenticating Docker with ECR"
echo "----------------------------------------"

ECR_REGISTRY=$(get_ecr_registry)
if ! authenticate_docker_ecr "${CURRENT_REGION}"; then
    exit 1
fi

# Step 3: Display repository information
echo ""
echo "📋 Repository Information"
echo "------------------------"

for repo in "${REPOS[@]}"; do
    REPO_URI="${ECR_REGISTRY}/${repo}"
    echo "${repo}: ${REPO_URI}"
done

# Step 4: Show next steps
echo ""
echo "✅ Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo ""
echo -e "${BLUE}1. Build and push Docker images:${NC}"
echo -e "${BLUE}   ./infra/build-push.sh${NC}"
echo ""
echo -e "${BLUE}2. Deploy infrastructure:${NC}"
echo -e "${BLUE}   ./infra/deploy.sh all${NC}"
echo ""
echo -e "${GREEN}💡 Tip: You can run this script again anytime to refresh your Docker ECR authentication${NC}"