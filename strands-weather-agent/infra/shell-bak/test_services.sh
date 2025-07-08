#!/bin/bash

# Strands Weather Agent AWS ECS Service Test Script
# Tests the deployed services through the Application Load Balancer

set -e

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Export environment variables
export_common_env

# Function to check if a service is healthy
check_service() {
    local service=$1
    local url=$2
    local max_attempts=5
    local attempt=1
    
    echo -n "Checking $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗${NC}"
    return 1
}

# Function to test a query
test_query() {
    local query=$1
    echo "Query: \"$query\""
    
    response=$(curl -s -X POST "http://${lb_dns}/query" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" 2>/dev/null || echo '{"response": "Error: Failed to connect"}')
    
    # Extract response and session fields
    response_text=$(echo "$response" | jq -r '.response' 2>/dev/null || echo "Error parsing response")
    session_id=$(echo "$response" | jq -r '.session_id' 2>/dev/null || echo "")
    session_new=$(echo "$response" | jq -r '.session_new' 2>/dev/null || echo "")
    conversation_turn=$(echo "$response" | jq -r '.conversation_turn' 2>/dev/null || echo "")
    
    if [[ "$response_text" == "Error"* ]] || [[ "$response_text" == "An error occurred"* ]]; then
        echo -e "Response: ${RED}✗ $response_text${NC}"
    else
        # Truncate long responses for display
        if [ ${#response_text} -gt 150 ]; then
            display_text="${response_text:0:147}..."
        else
            display_text="$response_text"
        fi
        echo -e "Response: ${GREEN}✓${NC} $display_text"
        
        # Display session info if available
        if [[ -n "$session_id" ]] && [[ "$session_id" != "null" ]]; then
            echo -e "Session: ${GREEN}✓${NC} ID: ${session_id:0:8}... | New: $session_new | Turn: $conversation_turn"
        fi
    fi
    echo ""
}

# Main testing function
test_aws_services() {
    log_info "🔍 Finding AWS Load Balancer for Strands Weather Agent..."
    
    # Get the load balancer DNS name
    local lb_dns=$(get_stack_output "$BASE_STACK_NAME" "ALBDNSName")
    
    if [ -z "$lb_dns" ]; then
        log_error "Could not find Load Balancer DNS. Make sure the $BASE_STACK_NAME stack is deployed."
        exit 1
    fi
    
    log_info "✅ Found Load Balancer: ${lb_dns}"
    echo ""
    
    print_section "🐳 AWS ECS Service Test"
    
    # Check ECS services status first
    print_section "1. Checking ECS Services Status"
    
    log_info "ECS Cluster Status:"
    cluster_status=$(aws ecs describe-clusters --clusters "$CLUSTER_NAME" --query 'clusters[0].status' --output text 2>/dev/null || echo "Not found")
    log_info "  Cluster Status: $cluster_status"
    
    # Check service status
    log_info "ECS Services Status:"
    
    echo "  Main Service:"
    local main_status=$(get_ecs_service_status "$CLUSTER_NAME" "strands-weather-agent-main")
    log_info "    $main_status"
    
    echo "  Forecast Service:"
    local forecast_status=$(get_ecs_service_status "$CLUSTER_NAME" "strands-weather-agent-forecast")
    log_info "    $forecast_status"
    
    echo "  Historical Service:"
    local historical_status=$(get_ecs_service_status "$CLUSTER_NAME" "strands-weather-agent-historical")
    log_info "    $historical_status"
    
    echo "  Agricultural Service:"
    local agricultural_status=$(get_ecs_service_status "$CLUSTER_NAME" "strands-weather-agent-agricultural")
    log_info "    $agricultural_status"
    echo ""
    
    # Test health endpoints
    print_section "2. Testing Service Endpoints"
    
    services_ok=true
    
    # Test weather agent health endpoint
    if ! check_service "Weather Agent Health" "http://${lb_dns}/health"; then
        services_ok=false
    fi
    
    # Note: MCP servers are internal and not exposed via ALB
    log_info "Note: MCP servers are internal services accessed via Service Discovery"
    echo ""
    
    if [ "$services_ok" = false ]; then
        log_error "Weather Agent service is not responding!"
        log_warn "Check service logs with: aws logs tail /ecs/strands-weather-agent-main --follow"
        exit 1
    fi
    
    log_info "✅ All accessible services are healthy!"
    echo ""
    
    # Test actual queries
    print_section "3. Running Test Queries"
    
    # Test different types of queries
    test_query "What's the weather forecast for Chicago?"
    test_query "How much rain did Seattle get last week?"
    test_query "Are conditions good for planting corn in Iowa?"
    
    # Test session endpoints
    print_section "4. Testing Session Endpoints"
    
    echo -n "Testing session endpoint..."
    # Get a session ID from a query
    if command -v jq &> /dev/null; then
        # Make a query to get a session ID
        session_response=$(curl -s -X POST "http://${lb_dns}/query" \
            -H "Content-Type: application/json" \
            -d '{"query": "test session"}' 2>/dev/null)
        
        test_session_id=$(echo "$session_response" | jq -r '.session_id' 2>/dev/null || echo "")
        
        if [[ -n "$test_session_id" ]] && [[ "$test_session_id" != "null" ]]; then
            # Test GET session info
            session_info=$(curl -s "http://${lb_dns}/session/$test_session_id" 2>/dev/null)
            if echo "$session_info" | jq -e '.session_id' &> /dev/null; then
                echo -e " ${GREEN}✓${NC}"
                echo "Session info retrieved successfully"
            else
                echo -e " ${RED}✗${NC}"
            fi
        else
            echo -e " ${YELLOW}⚠${NC} Could not get session ID"
        fi
    else
        echo -e " ${YELLOW}⚠${NC} jq not installed, skipping session test"
    fi
    echo ""
    
    # Test MCP connectivity
    print_section "5. Testing MCP Server Connectivity"
    
    log_info "Checking /mcp/status endpoint..."
    mcp_status=$(curl -s "http://${lb_dns}/mcp/status" 2>/dev/null)
    
    if echo "$mcp_status" | jq -e '.servers' &> /dev/null; then
        connected=$(echo "$mcp_status" | jq -r '.connected_count' 2>/dev/null || echo "0")
        total=$(echo "$mcp_status" | jq -r '.total_count' 2>/dev/null || echo "0")
        
        if [ "$connected" -eq "$total" ] && [ "$total" -gt 0 ]; then
            echo -e "${GREEN}✓${NC} All $total MCP servers connected"
        else
            echo -e "${YELLOW}⚠${NC} Only $connected of $total MCP servers connected"
        fi
        
        # Show individual server status
        echo "$mcp_status" | jq -r '.servers | to_entries[] | "   - \(.key): \(.value)"' 2>/dev/null
    else
        echo -e "${RED}✗${NC} Could not get MCP status"
    fi
    echo ""
    
    # Check ALB target health
    print_section "6. ALB Target Health"
    
    local target_group_arn=$(get_stack_output "$BASE_STACK_NAME" "ALBTargetGroupArn")
    
    if [ ! -z "$target_group_arn" ]; then
        log_info "Target Group Health:"
        aws elbv2 describe-target-health --target-group-arn "$target_group_arn" \
            --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State, TargetHealth.Reason]' \
            --output table 2>/dev/null || log_info "  Could not retrieve health status"
    else
        log_warn "  Could not find Target Group ARN"
    fi
    echo ""
    
    # Show recent task events
    print_section "7. Recent Task Events"
    
    log_info "Checking for recently stopped tasks..."
    stopped_tasks=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" \
        --desired-status STOPPED \
        --max-items 5 \
        --query 'taskArns' \
        --output json 2>/dev/null || echo "[]")
    
    task_count=$(echo "$stopped_tasks" | jq 'length' 2>/dev/null || echo "0")
    
    if [ "$task_count" -gt 0 ]; then
        log_warn "Found $task_count recently stopped tasks"
        # Get details of stopped tasks
        aws ecs describe-tasks --cluster "$CLUSTER_NAME" \
            --tasks $(echo "$stopped_tasks" | jq -r '.[]') \
            --query 'tasks[*].[taskDefinitionArn, stoppedReason, stopCode]' \
            --output table 2>/dev/null || log_info "Could not retrieve task details"
    else
        log_info "No recently stopped tasks found"
    fi
    echo ""
    
    # Summary and next steps
    print_section "📊 Summary"
    
    echo "Service URLs:"
    echo "  - Weather Agent API: http://$lb_dns"
    echo "  - API Docs: http://$lb_dns/docs"
    echo "  - Health Check: http://$lb_dns/health"
    echo "  - MCP Status: http://$lb_dns/mcp/status"
    echo ""
    echo "Useful Commands:"
    echo "  - View logs: aws logs tail /ecs/strands-weather-agent-main --follow"
    echo "  - Service status: ./status.sh"
    echo "  - Update service: ./deploy.sh services"
    echo ""
    
    log_info "✅ AWS ECS service test completed!"
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
test_aws_services