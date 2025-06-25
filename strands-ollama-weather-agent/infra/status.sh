#!/bin/bash

# Strands Weather Agent Infrastructure Status Script

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
            WEATHER_AGENT_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "WeatherAgentServiceName" "$REGION")
            FORECAST_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "ForecastServerServiceName" "$REGION")
            HISTORICAL_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "HistoricalServerServiceName" "$REGION")
            AGRICULTURAL_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "AgriculturalServerServiceName" "$REGION")
            
            # If outputs don't exist, use default names
            if [ -z "$WEATHER_AGENT_SERVICE" ] || [ "$WEATHER_AGENT_SERVICE" = "null" ]; then
                WEATHER_AGENT_SERVICE="${SERVICES_STACK_NAME}-weather-agent"
            fi
            if [ -z "$FORECAST_SERVICE" ] || [ "$FORECAST_SERVICE" = "null" ]; then
                FORECAST_SERVICE="${SERVICES_STACK_NAME}-forecast-server"
            fi
            if [ -z "$HISTORICAL_SERVICE" ] || [ "$HISTORICAL_SERVICE" = "null" ]; then
                HISTORICAL_SERVICE="${SERVICES_STACK_NAME}-historical-server"
            fi
            if [ -z "$AGRICULTURAL_SERVICE" ] || [ "$AGRICULTURAL_SERVICE" = "null" ]; then
                AGRICULTURAL_SERVICE="${SERVICES_STACK_NAME}-agricultural-server"
            fi
            
            # Get log groups using common functions
            WEATHER_AGENT_LOG_GROUP=$(get_stack_output "$SERVICES_STACK_NAME" "WeatherAgentLogGroup" "$REGION")
            FORECAST_LOG_GROUP=$(get_stack_output "$SERVICES_STACK_NAME" "ForecastServerLogGroup" "$REGION")
            HISTORICAL_LOG_GROUP=$(get_stack_output "$SERVICES_STACK_NAME" "HistoricalServerLogGroup" "$REGION")
            AGRICULTURAL_LOG_GROUP=$(get_stack_output "$SERVICES_STACK_NAME" "AgriculturalServerLogGroup" "$REGION")
            
            # If log group outputs don't exist, use default names
            if [ -z "$WEATHER_AGENT_LOG_GROUP" ] || [ "$WEATHER_AGENT_LOG_GROUP" = "null" ]; then
                WEATHER_AGENT_LOG_GROUP="/ecs/strands-weather-agent"
            fi
            if [ -z "$FORECAST_LOG_GROUP" ] || [ "$FORECAST_LOG_GROUP" = "null" ]; then
                FORECAST_LOG_GROUP="/ecs/strands-forecast-server"
            fi
            if [ -z "$HISTORICAL_LOG_GROUP" ] || [ "$HISTORICAL_LOG_GROUP" = "null" ]; then
                HISTORICAL_LOG_GROUP="/ecs/strands-historical-server"
            fi
            if [ -z "$AGRICULTURAL_LOG_GROUP" ] || [ "$AGRICULTURAL_LOG_GROUP" = "null" ]; then
                AGRICULTURAL_LOG_GROUP="/ecs/strands-agricultural-server"
            fi
            
            # Display log groups
            print_section "CloudWatch Log Groups"
            echo "  Weather Agent: $WEATHER_AGENT_LOG_GROUP"
            echo "  Forecast Server: $FORECAST_LOG_GROUP"
            echo "  Historical Server: $HISTORICAL_LOG_GROUP"
            echo "  Agricultural Server: $AGRICULTURAL_LOG_GROUP"
            
            # Get cluster name from base stack
            if [ -n "$CLUSTER_NAME" ]; then
                print_section "ECS Services Status"
                
                # Check weather agent service
                check_ecs_service_status "$CLUSTER_NAME" "$WEATHER_AGENT_SERVICE" "Weather Agent"
                
                # Add separator
                echo ""
                
                # Check MCP server services
                check_ecs_service_status "$CLUSTER_NAME" "$FORECAST_SERVICE" "Forecast Server"
                echo ""
                check_ecs_service_status "$CLUSTER_NAME" "$HISTORICAL_SERVICE" "Historical Server"
                echo ""
                check_ecs_service_status "$CLUSTER_NAME" "$AGRICULTURAL_SERVICE" "Agricultural Server"
                
                # Always check for stopped tasks
                print_section "Recent Task Status"
                
                # Check weather agent stopped tasks
                STOPPED_AGENT_TASKS=$(aws ecs list-tasks \
                    --cluster "$CLUSTER_NAME" \
                    --service-name "$WEATHER_AGENT_SERVICE" \
                    --desired-status STOPPED \
                    --max-items 3 \
                    --query 'length(taskArns)' \
                    --output text 2>/dev/null || echo "0")
                
                # Check MCP server stopped tasks
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
                echo "    Weather Agent: $STOPPED_AGENT_TASKS"
                echo "    Forecast Server: $STOPPED_FORECAST_TASKS"
                echo "    Historical Server: $STOPPED_HISTORICAL_TASKS"
                echo "    Agricultural Server: $STOPPED_AGRICULTURAL_TASKS"
                
                if [ "$STOPPED_AGENT_TASKS" -gt 0 ] || [ "$STOPPED_FORECAST_TASKS" -gt 0 ] || [ "$STOPPED_HISTORICAL_TASKS" -gt 0 ] || [ "$STOPPED_AGRICULTURAL_TASKS" -gt 0 ]; then
                    echo -e "    ${YELLOW}Note: Services may be experiencing issues${NC}"
                fi
            fi
            
            # Check if services are healthy
            print_section "Service Health Check"
            if [ -n "$LB_DNS" ]; then
                echo "  Testing weather agent endpoint..."
                HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" "http://$LB_DNS/health" 2>/dev/null || echo "000")
                if [ "$HEALTH_CHECK" = "200" ]; then
                    echo -e "  Weather Agent: ${GREEN}HEALTHY${NC}"
                else
                    echo -e "  Weather Agent: ${RED}UNHEALTHY${NC} (HTTP $HEALTH_CHECK)"
                fi
                
                echo ""
                echo "  MCP Servers: Internal services (not exposed via Load Balancer)"
                echo "  Access via Service Connect:"
                echo "    - Forecast Server: forecast-server.${BASE_STACK_NAME}:8081"
                echo "    - Historical Server: historical-server.${BASE_STACK_NAME}:8082"
                echo "    - Agricultural Server: agricultural-server.${BASE_STACK_NAME}:8083"
            fi
            
            # Always check for recent errors in logs
            print_section "Recent Log Errors"
            echo "  Checking for errors in the last 5 minutes..."
            
            # Function to check logs for a service
            check_service_logs() {
                local log_group=$1
                local service_name=$2
                
                if [ -n "$log_group" ]; then
                    echo -n "  $service_name: "
                    ERROR_COUNT=$(aws logs filter-log-events \
                        --log-group-name "$log_group" \
                        --start-time $(date -v-5M +%s)000 \
                        --filter-pattern "ERROR" \
                        --query 'length(events)' \
                        --output text 2>/dev/null || echo "0")
                    if [ "$ERROR_COUNT" -gt 0 ]; then
                        echo -e "${RED}$ERROR_COUNT errors found${NC}"
                        
                        # Show a few recent errors
                        echo "    Recent errors:"
                        aws logs filter-log-events \
                            --log-group-name "$log_group" \
                            --start-time $(date -v-5M +%s)000 \
                            --filter-pattern "ERROR" \
                            --max-items 3 \
                            --query 'events[*].message' \
                            --output text 2>/dev/null | head -3 | sed 's/^/      - /'
                    else
                        echo -e "${GREEN}No errors${NC}"
                    fi
                fi
            }
            
            # Check all service logs
            check_service_logs "$WEATHER_AGENT_LOG_GROUP" "Weather Agent"
            check_service_logs "$FORECAST_LOG_GROUP" "Forecast Server"
            check_service_logs "$HISTORICAL_LOG_GROUP" "Historical Server"
            check_service_logs "$AGRICULTURAL_LOG_GROUP" "Agricultural Server"
        fi
    else
        echo "  Status: NOT DEPLOYED"
    fi
    
    # Suggest next steps
    print_section "Next Steps"
    if [ -n "$LB_DNS" ]; then
        echo "  Test the API:"
        echo "    curl -X POST \"http://$LB_DNS/query\" \\"
        echo "        -H \"Content-Type: application/json\" \\"
        echo "        -d '{\"question\": \"What is the weather in Chicago?\"}'"
        echo ""
        echo "  Test health endpoint:"
        echo "    curl \"http://$LB_DNS/health\""
        echo ""
        echo "  View logs:"
        echo "    aws logs tail $WEATHER_AGENT_LOG_GROUP --follow"
        echo "    aws logs tail $FORECAST_LOG_GROUP --follow"
        echo "    aws logs tail $HISTORICAL_LOG_GROUP --follow"
        echo "    aws logs tail $AGRICULTURAL_LOG_GROUP --follow"
    fi
}

# Main execution
check_status