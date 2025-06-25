#!/bin/bash

# Agriculture Agent Infrastructure Status Script

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
        
        echo "  $service_type:"
        echo "    Desired: $DESIRED_COUNT"
        echo "    Running: $RUNNING_COUNT"
        echo "    Pending: $PENDING_COUNT"
        
    else
        echo "  $service_type: NOT FOUND"
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
            LB_DNS=$(get_stack_output "$BASE_STACK_NAME" "ALBDNSName" "$REGION")
            VPC_ID=$(get_stack_output "$BASE_STACK_NAME" "VPCId" "$REGION")
            CLUSTER_NAME=$(get_stack_output "$BASE_STACK_NAME" "ClusterName" "$REGION")
            
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
            # Get service names from stack outputs
            MAIN_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "MainServiceName" "$REGION")
            FORECAST_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "ForecastServiceName" "$REGION")
            HISTORICAL_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "HistoricalServiceName" "$REGION")
            AGRICULTURAL_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "AgriculturalServiceName" "$REGION")
            
            # Log groups are hardcoded in services.cfn
            MAIN_LOG_GROUP="/ecs/agriculture-agent-main"
            FORECAST_LOG_GROUP="/ecs/agriculture-agent-forecast"
            HISTORICAL_LOG_GROUP="/ecs/agriculture-agent-historical"
            AGRICULTURAL_LOG_GROUP="/ecs/agriculture-agent-agricultural"
            
            # Display log groups
            print_section "CloudWatch Log Groups"
            echo "  Main Agent: $MAIN_LOG_GROUP"
            echo "  Forecast Server: $FORECAST_LOG_GROUP"
            echo "  Historical Server: $HISTORICAL_LOG_GROUP"
            echo "  Agricultural Server: $AGRICULTURAL_LOG_GROUP"
            
            # Get cluster name from base stack
            if [ -n "$CLUSTER_NAME" ]; then
                print_section "ECS Services Status"
                
                # Check all four services
                check_ecs_service_status "$CLUSTER_NAME" "$MAIN_SERVICE" "Main Agent Service"
                echo ""
                check_ecs_service_status "$CLUSTER_NAME" "$FORECAST_SERVICE" "Forecast Server"
                echo ""
                check_ecs_service_status "$CLUSTER_NAME" "$HISTORICAL_SERVICE" "Historical Server"
                echo ""
                check_ecs_service_status "$CLUSTER_NAME" "$AGRICULTURAL_SERVICE" "Agricultural Server"
                
                # Check for stopped tasks for all services
                print_section "Recent Task Status"
                
                # Check stopped tasks for each service
                STOPPED_MAIN_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$MAIN_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                STOPPED_FORECAST_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$FORECAST_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                STOPPED_HISTORICAL_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$HISTORICAL_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                STOPPED_AGRICULTURAL_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$AGRICULTURAL_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                echo "  Recently stopped tasks:"
                echo "    Main Agent: $STOPPED_MAIN_TASKS"
                echo "    Forecast Server: $STOPPED_FORECAST_TASKS"
                echo "    Historical Server: $STOPPED_HISTORICAL_TASKS"
                echo "    Agricultural Server: $STOPPED_AGRICULTURAL_TASKS"
                
                TOTAL_STOPPED=$((STOPPED_MAIN_TASKS + STOPPED_FORECAST_TASKS + STOPPED_HISTORICAL_TASKS + STOPPED_AGRICULTURAL_TASKS))
                if [ "$TOTAL_STOPPED" -gt 0 ]; then
                    echo -e "    ${YELLOW}Note: Some services may be experiencing issues${NC}"
                fi
            fi
            
            # Check main agent health (only service exposed via ALB)
            print_section "Service Health Check"
            if [ -n "$LB_DNS" ]; then
                echo "  Testing main agent endpoint..."
                HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://$LB_DNS/health" 2>/dev/null || echo "000")
                if [ "$HEALTH_CHECK" = "200" ]; then
                    echo -e "  Main Agent: ${GREEN}HEALTHY${NC}"
                else
                    echo -e "  Main Agent: ${RED}UNHEALTHY${NC} (HTTP $HEALTH_CHECK)"
                fi
                
                echo ""
                echo "  MCP Servers: Internal services (not exposed via Load Balancer)"
                echo "    - Forecast Server: forecast.agriculture.local:7071"
                echo "    - Historical Server: historical.agriculture.local:7072"
                echo "    - Agricultural Server: agricultural.agriculture.local:7073"
            fi
            
            # Check for recent errors in main agent logs only
            print_section "Recent Log Errors (Main Agent)"
            echo "  Checking for errors in the last 5 minutes..."
            
            # Check main agent logs only
            if [ -n "$MAIN_LOG_GROUP" ]; then
                echo -n "  Main Agent: "
                ERROR_COUNT=$(aws logs filter-log-events \
                    --log-group-name "$MAIN_LOG_GROUP" \
                    --start-time $(date -v-5M +%s)000 \
                    --filter-pattern "ERROR" \
                    --query 'length(events)' \
                    --output text 2>/dev/null || echo "0")
                if [ "$ERROR_COUNT" -gt 0 ]; then
                    echo -e "${RED}$ERROR_COUNT errors found${NC}"
                    
                    # Show a few recent errors
                    echo "    Recent errors:"
                    aws logs filter-log-events \
                        --log-group-name "$MAIN_LOG_GROUP" \
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
        echo ""
        echo "  # Weather query example:"
        echo "    curl -X POST \"http://$LB_DNS/query\" \\"
        echo "        -H \"Content-Type: application/json\" \\"
        echo "        -d '{\"query\": \"What is the weather like in Chicago?\"}'"
        echo ""
        echo "  # Agricultural query example:"
        echo "    curl -X POST \"http://$LB_DNS/query\" \\"
        echo "        -H \"Content-Type: application/json\" \\"
        echo "        -d '{\"query\": \"Are conditions good for planting corn in Iowa?\"}'"
        echo ""
        echo "  View logs:"
        echo "    # Main agent logs:"
        echo "    aws logs tail $MAIN_LOG_GROUP --follow"
        echo ""
        echo "    # MCP server logs (if needed for debugging):"
        echo "    aws logs tail $FORECAST_LOG_GROUP --follow"
        echo "    aws logs tail $HISTORICAL_LOG_GROUP --follow"
        echo "    aws logs tail $AGRICULTURAL_LOG_GROUP --follow"
    fi
}

# Main execution
check_status