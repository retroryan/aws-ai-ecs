#!/bin/bash

# Spring AI MCP Agent Services Deployment Script
# This script handles ordered deployment of server and client services with comprehensive logging

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source all required modules
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/enhanced_logging.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"
source "${SCRIPT_DIR}/stack_operations.sh"

# Export environment variables
export_common_env

# Configuration
BASE_STACK_NAME="${BASE_STACK_NAME:-$DEFAULT_BASE_STACK_NAME}"
SERVICES_STACK_NAME="${SERVICES_STACK_NAME:-$DEFAULT_SERVICES_STACK_NAME}"
REGION="${AWS_REGION:-$DEFAULT_REGION}"
CLUSTER_NAME="${BASE_STACK_NAME}-cluster"

# Deployment timeouts
SERVER_WAIT_TIME=300  # 5 minutes
CLIENT_WAIT_TIME=300  # 5 minutes
CHECK_INTERVAL=10     # seconds between health checks
HEALTH_CHECK_TIMEOUT=30  # seconds for individual health checks

# Setup enhanced logging
setup_log_file "deployment" "${SCRIPT_DIR}/logs"

# Note: Logging functions now provided by enhanced_logging.sh
# Note: Color definitions now provided by common.sh

# Note: Stack functions now provided by common.sh and stack_operations.sh

# Note: ECS operation functions now provided by ecs-utils.sh

# Note: Health monitoring functions now provided by ecs-utils.sh

# Note: Log capture functions now provided by ecs-utils.sh

# Note: Service stability functions now provided by ecs-utils.sh

# Note: Health endpoint functions now provided by ecs-utils.sh

# Main deployment function
deploy_services() {
    log_deployment_section "Starting Spring AI MCP Services Deployment"
    log_info "Log file: $LOG_FILE"
    log_info "Base Stack: $BASE_STACK_NAME"
    log_info "Services Stack: $SERVICES_STACK_NAME"
    log_info "Region: $REGION"
    
    # Step 1: Check if base stack exists
    log_step "Step 1: Verifying base infrastructure..."
    local cluster_name=$(get_stack_output "$BASE_STACK_NAME" "ECSClusterName" "$REGION")
    if [ -z "$cluster_name" ]; then
        log_error "Base stack $BASE_STACK_NAME not found or not ready"
        exit 1
    fi
    log_info "✓ Base infrastructure verified"
    
    # Step 2: Load image tags
    log_step "Step 2: Loading image tags..."
    TAGS_FILE="${SCRIPT_DIR}/.image-tags"
    
    if [ -f "$TAGS_FILE" ]; then
        log_info "Loading tags from $TAGS_FILE"
        source "$TAGS_FILE"
    else
        log_error "Image tags file not found: $TAGS_FILE"
        log_error "Run './deploy.sh build-push' first to build and tag images"
        exit 1
    fi
    
    log_info "Client image tag: ${CLIENT_IMAGE_TAG}"
    log_info "Server image tag: ${SERVER_IMAGE_TAG}"
    
    # Step 3: Check if services stack already exists
    log_step "Step 3: Checking if services stack exists..."
    local stack_status=$(get_stack_status "$SERVICES_STACK_NAME" "$REGION")
    local skip_cf_deploy=false
    
    if [ -n "$stack_status" ]; then
        log_info "Services stack exists with status: $stack_status"
        
        # If stack is in progress, wait for it to complete
        if [[ "$stack_status" == *"IN_PROGRESS"* ]]; then
            log_info "Stack operation in progress, waiting for completion..."
            if ! wait_for_stack_completion "$SERVICES_STACK_NAME" 600 "$REGION"; then
                log_error "Stack operation failed or timed out"
                exit 1
            fi
            stack_status=$(get_stack_status "$SERVICES_STACK_NAME" "$REGION")
        fi
        
        # Check if we need to skip deployment
        if [ "$stack_status" = "CREATE_COMPLETE" ] || [ "$stack_status" = "UPDATE_COMPLETE" ]; then
            log_info "Stack already deployed successfully, skipping CloudFormation deployment"
            skip_cf_deploy=true
        fi
    else
        log_info "Services stack does not exist, will create it"
    fi
    
    # Step 4: Deploy CloudFormation stack (if needed)
    if [ "$skip_cf_deploy" = "false" ]; then
        log_step "Step 4: Deploying services CloudFormation stack..."
        
        # Build parameters - IMPORTANT: Set ClientStartupDelay=0 for ordered deployment
        PARAMS="BaseStackName=$BASE_STACK_NAME,ClientStartupDelay=0,ClientImageTag=$CLIENT_IMAGE_TAG,ServerImageTag=$SERVER_IMAGE_TAG"
        
        # Deploy with rain
        local services_template="${SCRIPT_DIR}/services.cfn"
        local cmd="rain deploy $services_template $SERVICES_STACK_NAME --region $REGION --params $PARAMS --yes"
        log_info "Running: $cmd"
        
        if ! $cmd >> "$LOG_FILE" 2>&1; then
            log_error "Failed to deploy CloudFormation stack"
            exit 1
        fi
        
        log_info "✓ CloudFormation stack deployed"
    else
        log_step "Step 4: Skipping CloudFormation deployment (stack already exists)"
    fi
    
    # Step 5: Get service names
    log_step "Step 5: Getting service information..."
    SERVER_SERVICE_NAME=$(get_stack_output "$SERVICES_STACK_NAME" "ServerServiceName" "$REGION")
    CLIENT_SERVICE_NAME=$(get_stack_output "$SERVICES_STACK_NAME" "ClientServiceName" "$REGION")
    
    if [ -z "$SERVER_SERVICE_NAME" ] || [ -z "$CLIENT_SERVICE_NAME" ]; then
        log_error "Failed to get service names from stack outputs"
        exit 1
    fi
    
    log_info "Server service: $SERVER_SERVICE_NAME"
    log_info "Client service: $CLIENT_SERVICE_NAME"
    
    # Step 6: Wait for server to be healthy
    log_step "Step 6: Waiting for server to be healthy (timeout: ${SERVER_WAIT_TIME}s)..."
    if ! wait_for_service_stable "$SERVER_SERVICE_NAME" "Server" $SERVER_WAIT_TIME "$CLUSTER_NAME" "$REGION"; then
        log_error "Server deployment failed!"
        capture_service_logs "Server" "/ecs/spring-ai-mcp-agent-server" 5 "$REGION"
        exit 1
    fi
    
    # Capture server logs
    capture_service_logs "Server" "/ecs/spring-ai-mcp-agent-server" 2 "$REGION"
    
    # Step 7: Start the client service by updating desired count
    log_step "Step 7: Starting client service..."
    if ! update_service_desired_count "$CLIENT_SERVICE_NAME" 1 "$CLUSTER_NAME" "$REGION"; then
        log_error "Failed to start client service"
        exit 1
    fi
    
    # Step 8: Wait for client to be healthy
    log_step "Step 8: Waiting for client to be healthy (timeout: ${CLIENT_WAIT_TIME}s)..."
    if ! wait_for_service_stable "$CLIENT_SERVICE_NAME" "Client" $CLIENT_WAIT_TIME "$CLUSTER_NAME" "$REGION"; then
        log_error "Client deployment failed!"
        capture_service_logs "Client" "/ecs/spring-ai-mcp-agent-client" 5 "$REGION"
        
        # Check client configuration
        log_info "Checking client configuration..."
        local client_tag=$(get_stack_parameter "$SERVICES_STACK_NAME" "ClientImageTag" "$REGION")
        log_info "Client is using image tag: $client_tag"
        
        exit 1
    fi
    
    # Capture client logs
    capture_service_logs "Client" "/ecs/spring-ai-mcp-agent-client" 2 "$REGION"
    
    # Step 9: Verify deployment
    log_step "Step 9: Verifying deployment..."
    ALB_DNS=$(get_stack_output "$BASE_STACK_NAME" "LoadBalancerDNS" "$REGION")
    if [ -n "$ALB_DNS" ]; then
        log_info "Load Balancer URL: http://$ALB_DNS"
        
        # Check health endpoint
        if check_health_endpoint "$ALB_DNS" 30; then
            log_info "✓ Service is responding to health checks!"
        else
            log_warn "⚠ Health check did not pass, but services are running"
        fi
        
        # Print test command
        log_deployment_section "✓ Deployment completed successfully!"
        log_info "You can test the service with:"
        echo "curl -X POST http://$ALB_DNS/inquire \\"
        echo '  -H "Content-Type: application/json" \'
        echo '  -d '"'"'{"question": "Get employees that have skills related to Java"}'"'"
    fi
    
    # Finalize logging
    finalize_log "completed"
}

# Script execution
case "${1:-deploy}" in
    deploy)
        deploy_services
        ;;
    *)
        echo "Usage: $0 [deploy]"
        exit 1
        ;;
esac