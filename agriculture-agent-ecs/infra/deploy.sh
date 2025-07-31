#!/bin/bash

# Agriculture Agent Infrastructure Deployment Script

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source common functions
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Export environment variables
export_common_env

# Configuration
BASE_STACK_NAME="agriculture-agent-base"
SERVICES_STACK_NAME="agriculture-agent-services"
REGION="${AWS_REGION:-us-east-1}"

# Bedrock configuration
BEDROCK_MODEL_ID="${BEDROCK_MODEL_ID:-amazon.nova-lite-v1:0}"
BEDROCK_REGION="${BEDROCK_REGION:-us-east-1}"
BEDROCK_TEMPERATURE="${BEDROCK_TEMPERATURE:-0}"
LOG_LEVEL="${LOG_LEVEL:-INFO}"

check_rain() {
    if ! command -v rain &> /dev/null; then
        log_error "Rain CLI is not installed. Please install it first."
        exit 1
    fi
}

deploy_base() {
    log_info "Deploying base infrastructure stack in region: $REGION"
    log_info "Stack name: $BASE_STACK_NAME"
    
    rain deploy "${SCRIPT_DIR}/base.cfn" $BASE_STACK_NAME --region $REGION --yes
    
    log_info "Base infrastructure deployed successfully!"
}

deploy_services() {
    log_info "Deploying services stack"
    log_info "Stack name: $SERVICES_STACK_NAME"
    log_info "Using Bedrock Model: $BEDROCK_MODEL_ID"
    
    rain deploy "${SCRIPT_DIR}/services-consolidated.cfn" $SERVICES_STACK_NAME \
        --region $REGION \
        --yes \
        --params BaseStackName=$BASE_STACK_NAME,BedrockModelId=$BEDROCK_MODEL_ID,BedrockRegion=$BEDROCK_REGION,BedrockTemperature=$BEDROCK_TEMPERATURE,LogLevel=$LOG_LEVEL
    
    log_info "Services deployed successfully!"
}

update_services() {
    log_info "Updating services stack"
    deploy_services
}

cleanup_services() {
    log_info "Removing services stack..."
    if check_stack_exists "$SERVICES_STACK_NAME" "$REGION"; then
        rain rm $SERVICES_STACK_NAME --region $REGION
        log_info "Services stack removed"
    else
        log_warn "Services stack not found"
    fi
}

cleanup_base() {
    log_info "Removing base infrastructure stack..."
    if check_stack_exists "$BASE_STACK_NAME" "$REGION"; then
        rain rm $BASE_STACK_NAME --region $REGION
        log_info "Base stack removed"
    else
        log_warn "Base stack not found"
    fi
}

cleanup_all() {
    log_warn "This will remove all infrastructure!"
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        cleanup_services
        cleanup_base
        log_info "All infrastructure removed"
    else
        log_info "Cleanup cancelled"
    fi
}

get_status() {
    log_info "Getting deployment status..."
    
    # Check base stack
    if check_stack_exists "$BASE_STACK_NAME" "$REGION"; then
        log_info "Base stack: DEPLOYED"
        
        # Get ALB DNS
        ALB_DNS=$(aws cloudformation describe-stacks \
            --stack-name $BASE_STACK_NAME \
            --query 'Stacks[0].Outputs[?OutputKey==`ALBDNSName`].OutputValue' \
            --output text \
            --region $REGION 2>/dev/null)
        
        if [ -n "$ALB_DNS" ]; then
            log_info "Application URL: http://$ALB_DNS"
        fi
    else
        log_warn "Base stack: NOT DEPLOYED"
    fi
    
    # Check services stack
    if check_stack_exists "$SERVICES_STACK_NAME" "$REGION"; then
        log_info "Services stack: DEPLOYED"
        
        # List services
        log_info "ECS Services:"
        aws ecs list-services \
            --cluster "agriculture-agent-cluster" \
            --region $REGION \
            --query 'serviceArns[*]' \
            --output text | xargs -n1 basename
    else
        log_warn "Services stack: NOT DEPLOYED"
    fi
}

build_and_push() {
    log_info "Building and pushing Docker images to ECR..."
    "${SCRIPT_DIR}/build-push.sh"
}

setup_ecr() {
    log_info "Setting up ECR repositories..."
    "${SCRIPT_DIR}/setup-ecr.sh"
}

aws_checks() {
    log_info "Running AWS configuration checks..."
    "${SCRIPT_DIR}/aws-checks.sh"
}

show_help() {
    echo "Agriculture Agent Infrastructure Deployment Script"
    echo ""
    echo "Usage: ./deploy.sh [command]"
    echo ""
    echo "Commands:"
    echo "  aws-checks       Check AWS configuration and Bedrock access"
    echo "  setup-ecr        Setup ECR repositories and Docker authentication"
    echo "  build-push       Build and push Docker images to ECR"
    echo "  all              Deploy all infrastructure (base + services)"
    echo "  base             Deploy only base infrastructure"
    echo "  services         Deploy only services (requires base)"
    echo "  update-services  Update services (redeploy task definitions)"
    echo "  status           Show current deployment status"
    echo "  cleanup-services Remove services stack only"
    echo "  cleanup-base     Remove base infrastructure stack"
    echo "  cleanup-all      Remove all infrastructure"
    echo "  help             Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  AWS_REGION          AWS region (default: us-east-1)"
    echo "  BEDROCK_MODEL_ID    Bedrock model to use (default: amazon.nova-lite-v1:0)"
    echo "  BEDROCK_REGION      Bedrock region (default: us-east-1)"
    echo "  BEDROCK_TEMPERATURE Model temperature (default: 0)"
    echo "  LOG_LEVEL           Logging level (default: INFO)"
    echo ""
    echo "Examples:"
    echo "  ./deploy.sh aws-checks                    # Check AWS setup"
    echo "  ./deploy.sh setup-ecr                     # Setup ECR repositories"
    echo "  ./deploy.sh build-push                    # Build and push images"
    echo "  ./deploy.sh all                          # Full deployment"
    echo "  ./deploy.sh status                       # Check deployment status"
    echo ""
}

# Main script logic
check_rain

case "$1" in
    aws-checks)
        aws_checks
        ;;
    setup-ecr)
        setup_ecr
        ;;
    build-push)
        build_and_push
        ;;
    all)
        setup_ecr
        build_and_push
        deploy_base
        deploy_services
        get_status
        ;;
    base)
        deploy_base
        ;;
    services)
        deploy_services
        ;;
    update-services)
        update_services
        ;;
    status)
        get_status
        ;;
    cleanup-services)
        cleanup_services
        ;;
    cleanup-base)
        cleanup_base
        ;;
    cleanup-all)
        cleanup_all
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac

# Ensure clean exit
exit 0