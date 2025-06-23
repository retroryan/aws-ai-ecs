#!/bin/bash

# Agriculture Weather Agent Service Testing Script
# Tests the deployed services through the Application Load Balancer

set -e

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Export environment variables
export_common_env

# Main testing function
test_mcp_services() {
    log_info "🔍 Finding AWS Load Balancer for Spring AI MCP Agent..."
    
    # Get the load balancer DNS name using common function
    local lb_dns=$(get_stack_output "$BASE_STACK_NAME" "ALBDNSName")
    
    if [ -z "$lb_dns" ]; then
        log_error "Could not find Load Balancer DNS. Make sure the $BASE_STACK_NAME stack is deployed."
        exit 1
    fi
    
    log_info "✅ Found Load Balancer: ${lb_dns}"
    echo ""
    
    # Test health endpoints first
    print_section "🏥 Health Endpoint Checks"
    
    # Test client health endpoint
    log_info "Testing client health endpoint..."
    client_health_response=$(curl -s "http://${lb_dns}/health" 2>/dev/null || echo "Failed to connect")
    if [[ "$client_health_response" != "Failed to connect" ]]; then
        log_info "✅ Client health endpoint response:"
        echo "$client_health_response"
    else
        log_warn "⚠️  Client health endpoint failed"
    fi
    echo ""
    
    # Test the service
    print_section "🚀 Testing the Weather Agent service"
    
    # Test 1: Basic weather query
    log_info "Test 1: Getting current weather in Chicago..."
    echo "POST http://${lb_dns}/query"
    echo 'Body: {"query": "What is the weather like in Chicago?"}'
    echo ""
    
    local weather_response=$(curl -s -X POST "http://${lb_dns}/query" \
        -H "Content-Type: application/json" \
        -d '{"query": "What is the weather like in Chicago?"}' \
        -w "\n\nHTTP Status: %{http_code}\n")
    echo "$weather_response"
    echo ""
    
    # Test 2: Agricultural query
    log_info "Test 2: Checking agricultural conditions in Iowa..."
    echo "POST http://${lb_dns}/query"
    echo 'Body: {"query": "Are conditions good for planting corn in Iowa?"}'
    echo ""
    
    log_info "Response:"
    local response=$(curl -s -X POST --location "http://${lb_dns}/query" \
        -H "Content-Type: application/json" \
        -d '{"query": "Are conditions good for planting corn in Iowa?"}' \
        -w "\n\nHTTP Status: %{http_code}\n")
    
    # Check if curl was successful
    if [ $? -ne 0 ]; then
        log_error "Failed to connect to the service"
        exit 1
    fi
    
    # Extract HTTP status code
    local http_status=$(echo "$response" | tail -n 1 | cut -d' ' -f3)
    
    # Print the response
    echo "$response"
    
    # Check if the request was successful
    if [[ "$http_status" == "200" ]]; then
        log_info "\n✅ Test successful!"
    else
        log_error "\nTest failed with HTTP status: ${http_status}"
    fi
    
    print_section "📊 ECS Infrastructure Status"
    
    # Check ECS cluster status
    log_info "ECS Cluster Status:"
    # Get cluster status directly from ECS
    cluster_status=$(aws ecs describe-clusters --clusters "$CLUSTER_NAME" --query 'clusters[0].status' --output text 2>/dev/null || echo "Not found")
    log_info "  Cluster Status: $cluster_status"
    
    # List running tasks
    log_info "Running ECS Tasks:"
    local tasks=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --query 'taskArns' --output json 2>/dev/null || echo "[]")
    local task_count=$(echo "$tasks" | jq 'length' 2>/dev/null || echo "0")
    log_info "  Number of running tasks: $task_count"
    
    if [ "$task_count" -gt "0" ]; then
        # Get task details
        log_info "Task Details:"
        aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks $(echo "$tasks" | jq -r '.[]') \
            --query 'tasks[*].[taskDefinitionArn, lastStatus, desiredStatus, containers[*].[name, lastStatus]]' \
            --output table 2>/dev/null || log_info "  Could not retrieve task details"
    fi
    
    # Check service status using common functions
    log_info "ECS Services Status:"
    
    echo "  Main Service:"
    local main_status=$(get_ecs_service_status "$CLUSTER_NAME" "agriculture-agent-main")
    log_info "    $main_status"
    
    echo "  Forecast Service:"
    local forecast_status=$(get_ecs_service_status "$CLUSTER_NAME" "agriculture-agent-forecast")
    log_info "    $forecast_status"
    
    echo "  Historical Service:"
    local historical_status=$(get_ecs_service_status "$CLUSTER_NAME" "agriculture-agent-historical")
    log_info "    $historical_status"
    
    echo "  Agricultural Service:"
    local agricultural_status=$(get_ecs_service_status "$CLUSTER_NAME" "agriculture-agent-agricultural")
    log_info "    $agricultural_status"
    
    print_section "🎯 ALB Target Health"
    
    # Get target group ARN using common function
    local target_group_arn=$(get_stack_output "$BASE_STACK_NAME" "ALBTargetGroupArn")
    
    if [ ! -z "$target_group_arn" ]; then
        log_info "Target Group Health:"
        aws elbv2 describe-target-health --target-group-arn "$target_group_arn" \
            --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State, TargetHealth.Reason]' \
            --output table 2>/dev/null || log_info "  Could not retrieve health status"
    else
        log_warn "  Could not find Target Group ARN"
    fi
    
    if [[ "$http_status" != "200" ]]; then
        exit 1
    fi
}

# Check prerequisites
if ! check_aws_cli; then
    exit 1
fi

if ! check_aws_credentials; then
    exit 1
fi

# Optional but recommended
check_jq

# Run the test
test_mcp_services