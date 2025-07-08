#!/bin/bash

# Spring AI MCP Agent Common Functions Library
# This file contains shared functions used across all infrastructure scripts

# Mark this module as sourced
export COMMON_SOURCED=true

# Color definitions for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export NC='\033[0m' # No Color

# Common configuration defaults
export DEFAULT_REGION="${AWS_REGION:-us-east-1}"
export DEFAULT_BASE_STACK_NAME="${BASE_STACK_NAME:-spring-ai-mcp-base}"
export DEFAULT_SERVICES_STACK_NAME="${SERVICES_STACK_NAME:-spring-ai-mcp-services}"
export DEFAULT_CLUSTER_NAME="${CLUSTER_NAME:-${DEFAULT_BASE_STACK_NAME}-cluster}"

# ECR configuration
export ECR_REPO_PREFIX="mcp-agent-spring-ai"
export ECR_CLIENT_REPO="${ECR_REPO_PREFIX}-client"
export ECR_SERVER_REPO="${ECR_REPO_PREFIX}-server"

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Print section headers
print_section() {
    echo
    echo -e "${BLUE}=== $1 ===${NC}"
    echo
}

# AWS validation functions
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        log_warn "Please install AWS CLI: https://aws.amazon.com/cli/"
        return 1
    fi
    return 0
}

check_aws_credentials() {
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured"
        log_warn "Run 'aws configure' to set up credentials"
        return 1
    fi
    return 0
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        log_warn "Please install Docker: https://www.docker.com/get-started"
        return 1
    fi
    return 0
}

check_jq() {
    if ! command -v jq &> /dev/null; then
        log_warn "jq is not installed. Some outputs may be less readable."
        log_warn "Install jq for better JSON parsing: https://stedolan.github.io/jq/"
        return 1
    fi
    return 0
}

# Get current AWS account ID
get_aws_account_id() {
    aws sts get-caller-identity --query Account --output text 2>/dev/null
}

# Get current AWS region
get_aws_region() {
    local region=$(aws configure get region 2>/dev/null || echo "${AWS_REGION:-not set}")
    echo "$region"
}

# Get ECR registry URL
get_ecr_registry() {
    local account_id=$(get_aws_account_id)
    local region=$(get_aws_region)
    if [ -n "$account_id" ] && [ "$region" != "not set" ]; then
        echo "${account_id}.dkr.ecr.${region}.amazonaws.com"
    fi
}

# CloudFormation stack functions
get_stack_output() {
    local stack_name=$1
    local output_key=$2
    local region=${3:-$DEFAULT_REGION}
    
    aws cloudformation describe-stacks \
        --stack-name $stack_name \
        --region $region \
        --query "Stacks[0].Outputs[?OutputKey=='$output_key'].OutputValue" \
        --output text 2>/dev/null || echo ""
}

get_stack_parameter() {
    local stack_name=$1
    local param_key=$2
    local region=${3:-$DEFAULT_REGION}
    
    aws cloudformation describe-stacks \
        --stack-name $stack_name \
        --region $region \
        --query "Stacks[0].Parameters[?ParameterKey=='$param_key'].ParameterValue" \
        --output text 2>/dev/null || echo ""
}

get_stack_status() {
    local stack_name=$1
    local region=${2:-$DEFAULT_REGION}
    
    aws cloudformation describe-stacks \
        --stack-name $stack_name \
        --region $region \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null || echo ""
}

check_stack_exists() {
    local stack_name=$1
    local region=${2:-$DEFAULT_REGION}
    
    if aws cloudformation describe-stacks --stack-name $stack_name --region $region &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ECR repository functions
check_ecr_repository() {
    local repo_name=$1
    local region=${2:-$DEFAULT_REGION}
    
    aws ecr describe-repositories \
        --repository-names "$repo_name" \
        --region $region &>/dev/null
}

create_ecr_repository() {
    local repo_name=$1
    local region=${2:-$DEFAULT_REGION}
    
    if check_ecr_repository "$repo_name" "$region"; then
        log_info "ECR repository '$repo_name' already exists"
        return 0
    else
        log_info "Creating ECR repository '$repo_name'..."
        if aws ecr create-repository --repository-name "$repo_name" --region $region &>/dev/null; then
            log_info "✓ Created ECR repository '$repo_name'"
            return 0
        else
            log_error "Failed to create ECR repository '$repo_name'"
            return 1
        fi
    fi
}

authenticate_docker_ecr() {
    local region=${1:-$DEFAULT_REGION}
    local registry=$(get_ecr_registry)
    
    if [ -z "$registry" ]; then
        log_error "Could not determine ECR registry URL"
        return 1
    fi
    
    log_info "Authenticating Docker with ECR..."
    if aws ecr get-login-password --region "$region" 2>/dev/null | \
       docker login --username AWS --password-stdin "$registry" >/dev/null 2>&1; then
        log_info "✓ Docker authenticated with ECR"
        return 0
    else
        log_error "Failed to authenticate Docker with ECR"
        return 1
    fi
}

# ECS service functions
get_ecs_service_info() {
    local cluster_name=$1
    local service_name=$2
    local region=${3:-$DEFAULT_REGION}
    
    aws ecs describe-services \
        --cluster $cluster_name \
        --services $service_name \
        --region $region \
        --query 'services[0]' \
        --output json 2>/dev/null || echo "{}"
}

get_ecs_service_status() {
    local cluster_name=$1
    local service_name=$2
    local region=${3:-$DEFAULT_REGION}
    
    local service_info=$(get_ecs_service_info "$cluster_name" "$service_name" "$region")
    
    if [ "$service_info" != "{}" ]; then
        local desired=$(echo "$service_info" | jq -r '.desiredCount // 0')
        local running=$(echo "$service_info" | jq -r '.runningCount // 0')
        local pending=$(echo "$service_info" | jq -r '.pendingCount // 0')
        echo "Desired: $desired, Running: $running, Pending: $pending"
    else
        echo "Service not found"
    fi
}

# Maven wrapper detection
get_maven_command() {
    if [ -f "./mvnw" ]; then
        echo "./mvnw"
    elif command -v mvn &> /dev/null; then
        echo "mvn"
    else
        log_error "Maven is not available. Please install Maven or ensure mvnw is present"
        return 1
    fi
}

# Bedrock validation
check_bedrock_access() {
    local region=${1:-$DEFAULT_REGION}
    local model_id=${2:-"amazon.nova-pro-v1:0"}
    
    if ! aws bedrock list-foundation-models --region "$region" --output json >/dev/null 2>&1; then
        log_error "Unable to access Bedrock in region $region"
        log_warn "Make sure you have:"
        log_warn "  - Valid AWS credentials configured"
        log_warn "  - Bedrock access enabled in your AWS account"
        log_warn "  - Correct permissions to access Bedrock"
        return 1
    fi
    
    # Check specific model
    if aws bedrock list-foundation-models --region "$region" --output json | \
       jq -e ".modelSummaries[] | select(.modelId == \"${model_id}\")" >/dev/null 2>&1; then
        log_info "✓ Bedrock model $model_id is available"
        return 0
    else
        log_error "Bedrock model $model_id is not available"
        log_warn "Request access at: https://us-east-1.console.aws.amazon.com/bedrock/home?region=${region}#/modelaccess"
        return 1
    fi
}

# Spinner function for long-running operations
spin() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    
    tput civis # Hide cursor
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) % ${#spin} ))
        printf "\r${message} ${spin:$i:1} "
        sleep .1
    done
    tput cnorm # Show cursor
    
    # Check if the process succeeded
    wait $pid
    return $?
}

# Helper to ensure we're in the project root directory
ensure_project_root() {
    # Check if we're in the infra directory and move up if needed
    if [[ "$PWD" == */infra ]]; then
        cd ..
    fi
    
    # Verify we're in the right place by checking for key files
    if [ ! -f "pom.xml" ] || [ ! -d "client" ] || [ ! -d "server" ]; then
        log_error "Not in the Spring AI Agent ECS project root directory"
        return 1
    fi
    
    return 0
}

# Common validation for deployment scripts
validate_deployment_prerequisites() {
    log_info "Validating deployment prerequisites..."
    
    # Check AWS CLI
    if ! check_aws_cli; then
        return 1
    fi
    
    # Check AWS credentials
    if ! check_aws_credentials; then
        return 1
    fi
    
    # Check Docker
    if ! check_docker; then
        return 1
    fi
    
    # Check jq (optional but recommended)
    check_jq
    
    log_info "✓ All prerequisites validated"
    return 0
}

# Export common environment variables
export_common_env() {
    export AWS_REGION="${AWS_REGION:-$DEFAULT_REGION}"
    export BASE_STACK_NAME="${BASE_STACK_NAME:-$DEFAULT_BASE_STACK_NAME}"
    export SERVICES_STACK_NAME="${SERVICES_STACK_NAME:-$DEFAULT_SERVICES_STACK_NAME}"
    export CLUSTER_NAME="${CLUSTER_NAME:-$DEFAULT_CLUSTER_NAME}"
}