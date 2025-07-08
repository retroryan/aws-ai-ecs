#!/bin/bash

# ECS Utilities Module
# Provides comprehensive ECS operations, health monitoring, and ECR management functions
# Used by multiple scripts in the infrastructure deployment pipeline

# Ensure common.sh is sourced (it should be sourced by the calling script)
if [ -z "$COMMON_SOURCED" ]; then
    echo "Error: common.sh must be sourced before ecs-utils.sh"
    exit 1
fi

# Mark this module as sourced
export ECS_UTILS_SOURCED=true

# =====================================================================
# ECR Repository Management
# =====================================================================

# Function to ensure both ECR repositories exist
# Replaces check_docker_images from deploy.sh
ensure_ecr_repositories_exist() {
    local server_repo="${1:-$ECR_SERVER_REPO}"
    local client_repo="${2:-$ECR_CLIENT_REPO}"
    local region="${3:-$REGION}"
    
    log_info "Ensuring ECR repositories exist..."
    create_ecr_repository "$server_repo" "$region"
    create_ecr_repository "$client_repo" "$region"
    log_info "ECR repositories are ready"
}

# =====================================================================
# ECS Service Operations
# =====================================================================

# Function to update service desired count
update_service_desired_count() {
    local service_name=$1
    local desired_count=$2
    local cluster_name="${3:-$CLUSTER_NAME}"
    local region="${4:-$REGION}"
    
    log_info "Updating $service_name desired count to $desired_count"
    
    local result=$(aws ecs update-service \
        --cluster $cluster_name \
        --service $service_name \
        --desired-count $desired_count \
        --region $region \
        --query 'service.desiredCount' \
        --output text 2>&1)
    
    if [ $? -eq 0 ] && [ "$result" = "$desired_count" ]; then
        log_info "✓ Successfully updated $service_name desired count to $desired_count"
        return 0
    else
        log_error "Failed to update desired count for $service_name: $result"
        return 1
    fi
}

# Function to get recent tasks
get_recent_tasks() {
    local service_name=$1
    local desired_status=${2:-RUNNING}
    local cluster_name="${3:-$CLUSTER_NAME}"
    local region="${4:-$REGION}"
    
    aws ecs list-tasks \
        --cluster $cluster_name \
        --service-name $service_name \
        --desired-status $desired_status \
        --max-items 10 \
        --region $region \
        --query 'taskArns[]' \
        --output text 2>/dev/null
}

# Function to check service status (enhanced version)
check_service_status() {
    local service_name=$1
    local cluster_name="${2:-$CLUSTER_NAME}"
    local region="${3:-$REGION}"
    
    aws ecs describe-services \
        --cluster $cluster_name \
        --services $service_name \
        --region $region \
        --query 'services[0]' \
        --output json 2>/dev/null || echo "{}"
}

# =====================================================================
# ECS Health Monitoring
# =====================================================================

# Function to check task health
check_task_health() {
    local service_name=$1
    local service_type=$2
    local cluster_name="${3:-$CLUSTER_NAME}"
    local region="${4:-$REGION}"
    
    local task_arns=$(get_recent_tasks "$service_name" "RUNNING" "$cluster_name" "$region")
    
    if [ -z "$task_arns" ]; then
        log_warn "No running tasks found for $service_type"
        return 1
    fi
    
    # Get task details
    local tasks_json=$(aws ecs describe-tasks \
        --cluster $cluster_name \
        --tasks $task_arns \
        --region $region \
        --output json 2>/dev/null)
    
    local total_tasks=0
    local healthy_tasks=0
    
    # Parse tasks
    while read -r task; do
        total_tasks=$((total_tasks + 1))
        
        local task_arn=$(echo "$task" | jq -r '.taskArn' 2>/dev/null)
        local last_status=$(echo "$task" | jq -r '.lastStatus' 2>/dev/null)
        local health_status=$(echo "$task" | jq -r '.healthStatus // "UNKNOWN"' 2>/dev/null)
        
        log_info "Task ${task_arn##*/}: Status=$last_status, Health=$health_status"
        
        if [ "$last_status" = "RUNNING" ]; then
            # Check container statuses
            local all_containers_healthy=true
            
            while read -r container; do
                local container_name=$(echo "$container" | jq -r '.name' 2>/dev/null)
                local container_status=$(echo "$container" | jq -r '.lastStatus' 2>/dev/null)
                local exit_code=$(echo "$container" | jq -r '.exitCode // empty' 2>/dev/null)
                
                if [ "$container_status" != "RUNNING" ] || [ -n "$exit_code" -a "$exit_code" != "0" -a "$exit_code" != "null" ]; then
                    log_warn "Container $container_name is not healthy: status=$container_status, exit_code=$exit_code"
                    all_containers_healthy=false
                    break
                fi
            done < <(echo "$task" | jq -c '.containers[]' 2>/dev/null)
            
            if [ "$all_containers_healthy" = "true" ]; then
                healthy_tasks=$((healthy_tasks + 1))
            fi
        fi
    done < <(echo "$tasks_json" | jq -c '.tasks[]' 2>/dev/null)
    
    log_info "$service_type: $healthy_tasks/$total_tasks tasks are healthy"
    
    if [ $healthy_tasks -eq $total_tasks ] && [ $total_tasks -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Function to capture service logs
capture_service_logs() {
    local service_type=$1
    local log_group=$2
    local since_minutes=${3:-5}
    local region="${4:-$REGION}"
    
    log_info "=== Recent $service_type Logs ==="
    
    # Calculate start time
    local start_time=$(($(date +%s) - (since_minutes * 60)))
    local start_time_ms=$((start_time * 1000))
    
    # Get log streams
    local streams=$(aws logs describe-log-streams \
        --log-group-name $log_group \
        --order-by LastEventTime \
        --descending \
        --limit 5 \
        --region $region \
        --query 'logStreams[0].logStreamName' \
        --output text 2>/dev/null)
    
    if [ -z "$streams" ] || [ "$streams" = "None" ]; then
        log_warn "No log streams found for $service_type"
        return
    fi
    
    # Get recent events
    aws logs get-log-events \
        --log-group-name $log_group \
        --log-stream-name "$streams" \
        --start-time $start_time_ms \
        --limit 50 \
        --region $region \
        --query 'events[-20:].message' \
        --output text 2>/dev/null | while IFS= read -r line; do
        log_info "$line"
    done
}

# Function to wait for service to be stable
wait_for_service_stable() {
    local service_name=$1
    local service_type=$2
    local timeout=$3
    local cluster_name="${4:-$CLUSTER_NAME}"
    local region="${5:-$REGION}"
    local check_interval="${CHECK_INTERVAL:-10}"
    
    log_info "Waiting for $service_type service ($service_name) to become stable..."
    
    local start_time=$(date +%s)
    local last_event_count=0
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            log_error "$service_type service did not stabilize within $timeout seconds"
            return 1
        fi
        
        # Get service status
        local service_info=$(check_service_status "$service_name" "$cluster_name" "$region")
        
        if [ "$service_info" = "{}" ]; then
            log_error "Failed to get status for $service_type"
            return 1
        fi
        
        local running_count=$(echo "$service_info" | jq -r '.runningCount // 0')
        local desired_count=$(echo "$service_info" | jq -r '.desiredCount // 0')
        local pending_count=$(echo "$service_info" | jq -r '.pendingCount // 0')
        local deployments=$(echo "$service_info" | jq -r '.deployments | length // 0')
        
        log_info "[$service_type] Running: $running_count/$desired_count, Pending: $pending_count, Active deployments: $deployments"
        
        # Log new events
        local events=$(echo "$service_info" | jq -r '.events[:5] | .[] | .message' 2>/dev/null)
        local event_count=$(echo "$events" | wc -l)
        if [ $event_count -gt $last_event_count ]; then
            echo "$events" | tail -n $((event_count - last_event_count)) | while IFS= read -r event; do
                log_info "[$service_type Event] $event"
            done
            last_event_count=$event_count
        fi
        
        # Special case: if desired count is 0, skip stability check
        if [ "$desired_count" -eq 0 ]; then
            log_info "$service_type service has desired count of 0, skipping stability check"
            return 0
        fi
        
        # Check if service is stable
        if [ "$running_count" -eq "$desired_count" ] && [ "$running_count" -gt 0 ] && [ "$deployments" -eq 1 ] && [ "$pending_count" -eq 0 ]; then
            log_info "$service_type service appears stable, checking task health..."
            
            # Additional health check
            if check_task_health "$service_name" "$service_type" "$cluster_name" "$region"; then
                log_info "✓ $service_type service is healthy!"
                return 0
            else
                log_warn "$service_type tasks are not all healthy yet"
            fi
        fi
        
        # Check for failed tasks
        local stopped_tasks=$(get_recent_tasks "$service_name" "STOPPED" "$cluster_name" "$region")
        if [ -n "$stopped_tasks" ]; then
            local stopped_count=$(echo "$stopped_tasks" | wc -w)
            log_warn "Found $stopped_count stopped tasks for $service_type"
            
            # Get details of stopped tasks
            local stopped_info=$(aws ecs describe-tasks \
                --cluster $cluster_name \
                --tasks $stopped_tasks \
                --region $region \
                --output json 2>/dev/null)
            
            echo "$stopped_info" | jq -r '.tasks[:2] | .[] | {stoppedReason, containers: .containers[] | {name, exitCode}}' 2>/dev/null | while IFS= read -r line; do
                log_warn "Stopped task info: $line"
            done
        fi
        
        sleep $check_interval
    done
}

# Function to check health endpoint
check_health_endpoint() {
    local alb_dns=$1
    local health_check_timeout="${2:-30}"
    
    local url="http://$alb_dns/actuator/health"
    
    log_info "Checking health endpoint: $url"
    
    # Try to check health endpoint using curl
    if command -v curl >/dev/null 2>&1; then
        local response=$(curl -s -w "\n%{http_code}" --connect-timeout $health_check_timeout "$url" 2>/dev/null)
        local http_code=$(echo "$response" | tail -1)
        local body=$(echo "$response" | head -n -1)
        
        if [ "$http_code" = "200" ]; then
            log_info "✓ Health check passed: $body"
            return 0
        else
            log_warn "Health check returned status $http_code: $body"
        fi
    else
        log_warn "curl not available, skipping HTTP health check"
    fi
    
    return 1
}