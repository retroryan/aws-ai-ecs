#!/bin/bash

# Spring AI MCP Agent Infrastructure Deployment Script

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source common functions
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Export environment variables
export_common_env

# Use configuration from common.sh
BASE_STACK_NAME="$DEFAULT_BASE_STACK_NAME"
SERVICES_STACK_NAME="$DEFAULT_SERVICES_STACK_NAME"
REGION="$DEFAULT_REGION"

check_rain() {
    if ! command -v rain &> /dev/null; then
        log_error "Rain CLI is not installed. Please install it first."
        exit 1
    fi
}


deploy_base() {
    log_info "Deploying base infrastructure stack in region: $REGION"
    rain deploy infra/base.cfn $BASE_STACK_NAME --region $REGION
    log_info "Base infrastructure deployed successfully!"
}

deploy_services() {
    log_info "Deploying services with ordered startup (server first, then client)"
    
    # Export environment variables for the deployment script
    export BASE_STACK_NAME="$BASE_STACK_NAME"
    export SERVICES_STACK_NAME="$SERVICES_STACK_NAME"
    export AWS_REGION="$REGION"
    
    # Use the bash deployment script
    "${SCRIPT_DIR}/deploy-services.sh"
}

update_services() {
    log_info "Updating services with ordered startup (server first, then client)"
    
    # Export environment variables for the deployment script
    export BASE_STACK_NAME="$BASE_STACK_NAME"
    export SERVICES_STACK_NAME="$SERVICES_STACK_NAME"
    export AWS_REGION="$REGION"
    
    # Use the bash deployment script
    "${SCRIPT_DIR}/deploy-services.sh"
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
    # Use external status script
    export BASE_STACK_NAME="$BASE_STACK_NAME"
    export SERVICES_STACK_NAME="$SERVICES_STACK_NAME"
    export AWS_REGION="$REGION"
    "${SCRIPT_DIR}/status.sh"
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
    echo "Spring AI MCP Agent Infrastructure Deployment Script"
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
    echo "Examples:"
    echo "  ./deploy.sh aws-checks       # Check AWS setup before deployment"
    echo "  ./deploy.sh setup-ecr        # Setup ECR repositories"
    echo "  ./deploy.sh build-push       # Build and push new images"
    echo "  ./deploy.sh all              # First time deployment"
    echo "  ./deploy.sh update-services  # Update after code changes"
    echo "  ./deploy.sh cleanup-all      # Complete teardown"
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
        ensure_ecr_repositories_exist
        deploy_base
        deploy_services
        get_status
        ;;
    base)
        ensure_ecr_repositories_exist
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