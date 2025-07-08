#!/bin/bash

# Stack Operations Module
# Provides CloudFormation stack operations not available in common.sh
# Used by deploy-services.sh and other scripts that need advanced stack operations

# Ensure common.sh is sourced (it should be sourced by the calling script)
if [ -z "$COMMON_SOURCED" ]; then
    echo "Error: common.sh must be sourced before stack_operations.sh"
    exit 1
fi

# Mark this module as sourced
export STACK_OPERATIONS_SOURCED=true

# =====================================================================
# Advanced CloudFormation Operations
# =====================================================================

# Function to wait for stack completion with detailed monitoring
# This extends the basic stack operations from common.sh
wait_for_stack_completion() {
    local stack_name=$1
    local timeout=${2:-600}
    local region="${3:-$REGION}"
    local start_time=$(date +%s)
    
    log_info "Waiting for stack '$stack_name' to complete (timeout: ${timeout}s)..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "Timeout waiting for stack $stack_name after ${timeout} seconds"
            return 1
        fi
        
        # Get current stack status
        local status=$(get_stack_status "$stack_name" "$region")
        
        if [ -z "$status" ]; then
            log_error "Failed to get status for stack $stack_name"
            return 1
        fi
        
        log_info "Stack '$stack_name' status: $status (elapsed: ${elapsed}s)"
        
        case $status in
            CREATE_COMPLETE|UPDATE_COMPLETE)
                log_info "✓ Stack operation completed successfully"
                return 0
                ;;
            CREATE_FAILED|ROLLBACK_COMPLETE|UPDATE_ROLLBACK_COMPLETE|DELETE_COMPLETE)
                log_error "Stack operation failed with status: $status"
                
                # Try to get stack events for more details
                log_info "Fetching recent stack events for debugging..."
                aws cloudformation describe-stack-events \
                    --stack-name "$stack_name" \
                    --region "$region" \
                    --max-items 10 \
                    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED` || ResourceStatus==`UPDATE_FAILED`].{Resource:ResourceType,Status:ResourceStatus,Reason:ResourceStatusReason}' \
                    --output table 2>/dev/null || log_warn "Could not fetch stack events"
                
                return 1
                ;;
            *IN_PROGRESS*)
                # Stack operation is still in progress
                sleep 10
                ;;
            *)
                log_warn "Unexpected stack status: $status"
                sleep 10
                ;;
        esac
    done
}

# Function to get stack events (recent failures)
get_stack_failure_events() {
    local stack_name=$1
    local region="${2:-$REGION}"
    local max_events="${3:-20}"
    
    log_info "Fetching recent failure events for stack: $stack_name"
    
    aws cloudformation describe-stack-events \
        --stack-name "$stack_name" \
        --region "$region" \
        --max-items "$max_events" \
        --query 'StackEvents[?contains(ResourceStatus, `FAILED`)].{Time:Timestamp,Resource:LogicalResourceId,Type:ResourceType,Status:ResourceStatus,Reason:ResourceStatusReason}' \
        --output table 2>/dev/null
}

# Function to validate stack template before deployment
validate_stack_template() {
    local template_file=$1
    local region="${2:-$REGION}"
    
    log_info "Validating CloudFormation template: $template_file"
    
    if [ ! -f "$template_file" ]; then
        log_error "Template file not found: $template_file"
        return 1
    fi
    
    local validation_result=$(aws cloudformation validate-template \
        --template-body file://"$template_file" \
        --region "$region" \
        --output json 2>&1)
    
    if [ $? -eq 0 ]; then
        log_info "✓ Template validation successful"
        
        # Extract and display template capabilities if any
        local capabilities=$(echo "$validation_result" | jq -r '.Capabilities[]?' 2>/dev/null)
        if [ -n "$capabilities" ]; then
            log_info "Template requires capabilities: $capabilities"
        fi
        
        return 0
    else
        log_error "Template validation failed:"
        echo "$validation_result"
        return 1
    fi
}

# Function to check if stack update is needed
stack_needs_update() {
    local stack_name=$1
    local template_file=$2
    local parameters="$3"
    local region="${4:-$REGION}"
    
    log_info "Checking if stack '$stack_name' needs update..."
    
    # Check if stack exists
    if ! check_stack_exists "$stack_name" "$region"; then
        log_info "Stack does not exist, will need to create"
        return 0
    fi
    
    # Get current stack status
    local status=$(get_stack_status "$stack_name" "$region")
    
    # If stack is in failed state, update is needed
    case $status in
        CREATE_FAILED|ROLLBACK_COMPLETE|UPDATE_ROLLBACK_COMPLETE)
            log_info "Stack is in failed state ($status), update needed"
            return 0
            ;;
        *IN_PROGRESS*)
            log_warn "Stack operation is in progress ($status), cannot update now"
            return 1
            ;;
        CREATE_COMPLETE|UPDATE_COMPLETE)
            log_info "Stack is in good state ($status)"
            # Could add template diff checking here in the future
            return 1
            ;;
        *)
            log_warn "Stack has unexpected status: $status"
            return 1
            ;;
    esac
}

# Function to deploy stack with rain (if available) or aws cli
deploy_stack_with_rain() {
    local template_file=$1
    local stack_name=$2
    local region=$3
    local parameters="$4"
    local additional_args="$5"
    
    log_info "Deploying stack '$stack_name' using Rain CLI..."
    
    # Check if rain is available
    if ! command -v rain &> /dev/null; then
        log_error "Rain CLI is not installed. Please install it first."
        return 1
    fi
    
    # Validate template first
    if ! validate_stack_template "$template_file" "$region"; then
        log_error "Template validation failed, aborting deployment"
        return 1
    fi
    
    # Build rain command
    local rain_cmd="rain deploy $template_file $stack_name --region $region"
    
    if [ -n "$parameters" ]; then
        rain_cmd="$rain_cmd --params $parameters"
    fi
    
    if [ -n "$additional_args" ]; then
        rain_cmd="$rain_cmd $additional_args"
    fi
    
    log_info "Executing: $rain_cmd"
    
    # Execute rain command
    if eval "$rain_cmd"; then
        log_info "✓ Rain deployment completed successfully"
        return 0
    else
        log_error "Rain deployment failed"
        
        # Try to get stack events for debugging
        get_stack_failure_events "$stack_name" "$region"
        return 1
    fi
}

# Function to get stack drift information
check_stack_drift() {
    local stack_name=$1
    local region="${2:-$REGION}"
    
    log_info "Checking drift for stack: $stack_name"
    
    # Start drift detection
    local drift_id=$(aws cloudformation detect-stack-drift \
        --stack-name "$stack_name" \
        --region "$region" \
        --query 'StackDriftDetectionId' \
        --output text 2>/dev/null)
    
    if [ -z "$drift_id" ]; then
        log_error "Failed to start drift detection"
        return 1
    fi
    
    log_info "Drift detection started (ID: $drift_id)"
    
    # Wait for drift detection to complete
    local max_wait=300  # 5 minutes
    local elapsed=0
    
    while [ $elapsed -lt $max_wait ]; do
        local drift_status=$(aws cloudformation describe-stack-drift-detection-status \
            --stack-drift-detection-id "$drift_id" \
            --region "$region" \
            --query 'DetectionStatus' \
            --output text 2>/dev/null)
        
        case $drift_status in
            DETECTION_COMPLETE)
                break
                ;;
            DETECTION_FAILED)
                log_error "Drift detection failed"
                return 1
                ;;
            DETECTION_IN_PROGRESS)
                sleep 10
                elapsed=$((elapsed + 10))
                ;;
            *)
                log_warn "Unknown drift detection status: $drift_status"
                sleep 10
                elapsed=$((elapsed + 10))
                ;;
        esac
    done
    
    # Get drift results
    aws cloudformation describe-stack-drift-detection-status \
        --stack-drift-detection-id "$drift_id" \
        --region "$region" \
        --query '{Status:DetectionStatus,StackDriftStatus:StackDriftStatus,DriftedStackResourceCount:DriftedStackResourceCount}' \
        --output table 2>/dev/null
}