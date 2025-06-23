#!/bin/bash

# Spring AI MCP Agent Infrastructure Status Script

set -e

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Export environment variables
export_common_env

# Ensure REGION is set
if [ -z "$REGION" ]; then
    REGION="$DEFAULT_REGION"
fi

# Function to check ECS service status
check_ecs_service_status() {
    local cluster_name=$1
    local service_name=$2
    local service_type=$3
    
    # Get service status using common function
    SERVICE_INFO=$(get_ecs_service_info "$cluster_name" "$service_name" "$REGION")
    
    if [ "$SERVICE_INFO" != "{}" ]; then
        DESIRED_COUNT=$(echo $SERVICE_INFO | jq -r '.desiredCount // 0')
        RUNNING_COUNT=$(echo $SERVICE_INFO | jq -r '.runningCount // 0')
        PENDING_COUNT=$(echo $SERVICE_INFO | jq -r '.pendingCount // 0')
        
        echo "  $service_type Service:"
        echo "    Desired: $DESIRED_COUNT"
        echo "    Running: $RUNNING_COUNT"
        echo "    Pending: $PENDING_COUNT"
        
    else
        echo "  $service_type Service: NOT FOUND"
    fi
}

# Main status check function
check_status() {
    log_info "Checking infrastructure status in region: $REGION"
    
    print_section "Base Infrastructure Stack"
    if check_stack_exists "$BASE_STACK_NAME" "$REGION"; then
        STATUS=$(get_stack_status "$BASE_STACK_NAME" "$REGION")
        echo "  Status: $STATUS"
        
        if [ "$STATUS" = "CREATE_COMPLETE" ] || [ "$STATUS" = "UPDATE_COMPLETE" ]; then
            # Get outputs using common functions
            LB_DNS=$(get_stack_output "$BASE_STACK_NAME" "LoadBalancerDNS" "$REGION")
            VPC_ID=$(get_stack_output "$BASE_STACK_NAME" "VPCId" "$REGION")
            CLUSTER_NAME=$(get_stack_output "$BASE_STACK_NAME" "ECSClusterName" "$REGION")
            
            echo "  Load Balancer: http://$LB_DNS"
            echo "  VPC ID: $VPC_ID"
            echo "  ECS Cluster: $CLUSTER_NAME"
        fi
    else
        echo "  Status: NOT DEPLOYED"
    fi
    
    print_section "Services Stack"
    if check_stack_exists "$SERVICES_STACK_NAME" "$REGION"; then
        STATUS=$(get_stack_status "$SERVICES_STACK_NAME" "$REGION")
        echo "  Status: $STATUS"
        
        if [ "$STATUS" = "CREATE_COMPLETE" ] || [ "$STATUS" = "UPDATE_COMPLETE" ]; then
            # Get service names using common functions
            CLIENT_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "ClientServiceName" "$REGION")
            SERVER_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "ServerServiceName" "$REGION")
            
            # If outputs don't exist, use default names
            if [ -z "$CLIENT_SERVICE" ] || [ "$CLIENT_SERVICE" = "null" ]; then
                CLIENT_SERVICE="${SERVICES_STACK_NAME}-client"
            fi
            if [ -z "$SERVER_SERVICE" ] || [ "$SERVER_SERVICE" = "null" ]; then
                SERVER_SERVICE="${SERVICES_STACK_NAME}-server"
            fi
            
            # Get log groups using common functions
            CLIENT_LOG_GROUP=$(get_stack_output "$SERVICES_STACK_NAME" "ClientLogGroup" "$REGION")
            SERVER_LOG_GROUP=$(get_stack_output "$SERVICES_STACK_NAME" "ServerLogGroup" "$REGION")
            
            # If log group outputs don't exist, use default names
            if [ -z "$CLIENT_LOG_GROUP" ] || [ "$CLIENT_LOG_GROUP" = "null" ]; then
                CLIENT_LOG_GROUP="/ecs/spring-ai-mcp-agent-client"
            fi
            if [ -z "$SERVER_LOG_GROUP" ] || [ "$SERVER_LOG_GROUP" = "null" ]; then
                SERVER_LOG_GROUP="/ecs/spring-ai-mcp-agent-server"
            fi
            
            # Display log groups
            print_section "CloudWatch Log Groups"
            echo "  Client: $CLIENT_LOG_GROUP"
            echo "  Server: $SERVER_LOG_GROUP"
            
            # Get cluster name from base stack
            if [ -n "$CLUSTER_NAME" ]; then
                print_section "ECS Services Status"
                
                # Check client service
                check_ecs_service_status "$CLUSTER_NAME" "$CLIENT_SERVICE" "Client"
                
                # Add separator
                echo ""
                
                # Check server service
                check_ecs_service_status "$CLUSTER_NAME" "$SERVER_SERVICE" "Server"
                
                # Always check for stopped tasks
                print_section "Recent Task Status"
                
                # Check client stopped tasks
                STOPPED_CLIENT_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$CLIENT_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                # Check server stopped tasks
                STOPPED_SERVER_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$SERVER_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                echo "  Recently stopped tasks:"
                echo "    Client: $STOPPED_CLIENT_TASKS"
                echo "    Server: $STOPPED_SERVER_TASKS"
                
                if [ "$STOPPED_CLIENT_TASKS" -gt 0 ] || [ "$STOPPED_SERVER_TASKS" -gt 0 ]; then
                    echo -e "    ${YELLOW}Note: Services may be experiencing issues${NC}"
                fi
            fi
            
            # Check if services are healthy
            print_section "Service Health Check"
            if [ -n "$LB_DNS" ]; then
                echo "  Testing client endpoint..."
                HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://$LB_DNS/actuator/health" 2>/dev/null || echo "000")
                if [ "$HEALTH_CHECK" = "200" ]; then
                    echo -e "  Client: ${GREEN}HEALTHY${NC}"
                else
                    echo -e "  Client: ${RED}UNHEALTHY${NC} (HTTP $HEALTH_CHECK)"
                fi
                
                echo "  Server: Internal service (not exposed via Load Balancer)"
                echo "         Access via Service Connect: mcp-server.${BASE_STACK_NAME}:8081"
            fi
            
            # Always check for recent errors in logs
            print_section "Recent Log Errors"
            echo "  Checking for errors in the last 5 minutes..."
            
            # Check client logs
            if [ -n "$CLIENT_LOG_GROUP" ]; then
                echo -n "  Client: "
                ERROR_COUNT=$(aws logs filter-log-events \
                    --log-group-name "$CLIENT_LOG_GROUP" \
                    --start-time $(date -v-5M +%s)000 \
                    --filter-pattern "ERROR" \
                    --query 'length(events)' \
                    --output text 2>/dev/null || echo "0")
                if [ "$ERROR_COUNT" -gt 0 ]; then
                    echo -e "${RED}$ERROR_COUNT errors found${NC}"
                    
                    # Show a few recent errors
                    echo "    Recent errors:"
                    aws logs filter-log-events \
                        --log-group-name "$CLIENT_LOG_GROUP" \
                        --start-time $(date -v-5M +%s)000 \
                        --filter-pattern "ERROR" \
                        --max-items 3 \
                        --query 'events[*].message' \
                        --output text 2>/dev/null | head -3 | sed 's/^/      - /'
                else
                    echo -e "${GREEN}No errors${NC}"
                fi
            fi
            
            # Check server logs
            if [ -n "$SERVER_LOG_GROUP" ]; then
                echo -n "  Server: "
                ERROR_COUNT=$(aws logs filter-log-events \
                    --log-group-name "$SERVER_LOG_GROUP" \
                    --start-time $(date -v-5M +%s)000 \
                    --filter-pattern "ERROR" \
                    --query 'length(events)' \
                    --output text 2>/dev/null || echo "0")
                if [ "$ERROR_COUNT" -gt 0 ]; then
                    echo -e "${RED}$ERROR_COUNT errors found${NC}"
                    
                    # Show a few recent errors
                    echo "    Recent errors:"
                    aws logs filter-log-events \
                        --log-group-name "$SERVER_LOG_GROUP" \
                        --start-time $(date -v-5M +%s)000 \
                        --filter-pattern "ERROR" \
                        --max-items 3 \
                        --query 'events[*].message' \
                        --output text 2>/dev/null | head -3 | sed 's/^/      - /'
                else
                    echo -e "${GREEN}No errors${NC}"
                fi
            fi
        fi
    else
        echo "  Status: NOT DEPLOYED"
    fi
    
    # Suggest next steps
    print_section "Next Steps"
    if [ -n "$LB_DNS" ]; then
        echo "  Test the API:"
        echo "    curl -X POST --location \"http://$LB_DNS/inquire\" \\"
        echo "        -H \"Content-Type: application/json\" \\"
        echo "        -d '{\"question\": \"Get employees that have skills related to Java\"}'"
        echo ""
        echo "  View logs:"
        echo "    aws logs tail $CLIENT_LOG_GROUP --follow"
        echo "    aws logs tail $SERVER_LOG_GROUP --follow"
    fi
}

# Main execution
check_status