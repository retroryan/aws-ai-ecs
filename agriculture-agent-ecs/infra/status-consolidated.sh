#!/bin/bash

# Agriculture Agent Infrastructure Status Script (Consolidated Architecture)
# This script provides detailed status information about the deployed infrastructure

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"

echo "=================================================="
echo "Agriculture Agent Infrastructure Status"
echo "=================================================="
echo ""

# Get stack names
BASE_STACK_NAME="${BASE_STACK_NAME:-agriculture-agent-base}"
SERVICES_STACK_NAME="${SERVICES_STACK_NAME:-agriculture-agent-services}"
REGION="${AWS_REGION:-us-east-1}"

# Check if stacks exist
echo "📋 Stack Status"
echo "---------------"

# Function to check stack status
check_stack() {
    local stack_name=$1
    local stack_type=$2
    
    echo -n "$stack_type Stack ($stack_name): "
    
    STATUS=$(aws cloudformation describe-stacks \
        --stack-name "$stack_name" \
        --region "$REGION" \
        --query 'Stacks[0].StackStatus' \
        --output text 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        case $STATUS in
            CREATE_COMPLETE|UPDATE_COMPLETE)
                echo -e "${GREEN}✅ $STATUS${NC}"
                return 0
                ;;
            *PROGRESS*)
                echo -e "${YELLOW}⏳ $STATUS${NC}"
                return 1
                ;;
            *FAILED*|*ROLLBACK*)
                echo -e "${RED}❌ $STATUS${NC}"
                return 2
                ;;
            *)
                echo -e "${BLUE}ℹ️  $STATUS${NC}"
                return 0
                ;;
        esac
    else
        echo -e "${RED}❌ Not deployed${NC}"
        return 3
    fi
}

BASE_STATUS=$(check_stack "$BASE_STACK_NAME" "Base")
BASE_RC=$?

SERVICES_STATUS=$(check_stack "$SERVICES_STACK_NAME" "Services")
SERVICES_RC=$?

# If base stack exists, get detailed information
if [ $BASE_RC -eq 0 ]; then
    echo ""
    echo "🏗️  Infrastructure Details"
    echo "------------------------"
    
    # Get outputs from base stack
    VPC_ID=$(get_stack_output "$BASE_STACK_NAME" "VPCId" "$REGION")
    CLUSTER_NAME=$(get_stack_output "$BASE_STACK_NAME" "ClusterName" "$REGION")
    ALB_URL=$(get_stack_output "$BASE_STACK_NAME" "ALBDNSName" "$REGION")
    
    echo "VPC ID: $VPC_ID"
    echo "ECS Cluster: $CLUSTER_NAME"
    echo "Load Balancer URL: http://$ALB_URL"
    
    # If services stack exists, get service details
    if [ $SERVICES_RC -eq 0 ]; then
        echo ""
        echo "🚀 Service Status"
        echo "-----------------"
        
        # Get service names
        MAIN_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "MainServiceName" "$REGION")
        WEATHER_SERVICE=$(get_stack_output "$SERVICES_STACK_NAME" "WeatherServiceName" "$REGION")
        
        # Default service names if outputs don't exist
        MAIN_SERVICE="${MAIN_SERVICE:-agriculture-main}"
        WEATHER_SERVICE="${WEATHER_SERVICE:-agriculture-weather}"
        
        # Get log groups
        MAIN_LOG_GROUP="/ecs/agriculture-main"
        WEATHER_LOG_GROUP="/ecs/agriculture-weather"
        
        echo "Log Groups:"
        echo "  Main Agent: $MAIN_LOG_GROUP"
        echo "  Weather Server: $WEATHER_LOG_GROUP"
        
        # Check ECS services
        echo ""
        echo "ECS Services:"
        
        # Function to check ECS service status
        check_ecs_service_status() {
            local cluster=$1
            local service=$2
            local display_name=$3
            
            echo -n "  $display_name: "
            
            SERVICE_STATUS=$(aws ecs describe-services \
                --cluster "$cluster" \
                --services "$service" \
                --region "$REGION" \
                --query 'services[0].status' \
                --output text 2>/dev/null)
            
            if [ "$SERVICE_STATUS" = "ACTIVE" ]; then
                # Get running/desired task count
                RUNNING=$(aws ecs describe-services \
                    --cluster "$cluster" \
                    --services "$service" \
                    --region "$REGION" \
                    --query 'services[0].runningCount' \
                    --output text 2>/dev/null)
                
                DESIRED=$(aws ecs describe-services \
                    --cluster "$cluster" \
                    --services "$service" \
                    --region "$REGION" \
                    --query 'services[0].desiredCount' \
                    --output text 2>/dev/null)
                
                if [ "$RUNNING" = "$DESIRED" ] && [ "$RUNNING" -gt 0 ]; then
                    echo -e "${GREEN}✅ Running ($RUNNING/$DESIRED tasks)${NC}"
                else
                    echo -e "${YELLOW}⚠️  Deploying ($RUNNING/$DESIRED tasks)${NC}"
                fi
            else
                echo -e "${RED}❌ $SERVICE_STATUS${NC}"
            fi
        }
        
        check_ecs_service_status "$CLUSTER_NAME" "$MAIN_SERVICE" "Main Agent"
        check_ecs_service_status "$CLUSTER_NAME" "$WEATHER_SERVICE" "Weather Server"
        
        # Check for stopped tasks
        echo ""
        echo "Stopped Tasks (last hour):"
        
        STOPPED_MAIN_TASKS=$(aws ecs list-tasks \
            --cluster "$CLUSTER_NAME" \
            --service-name "$MAIN_SERVICE" \
            --desired-status STOPPED \
            --region "$REGION" \
            --query 'length(taskArns)' \
            --output text 2>/dev/null || echo "0")
        
        STOPPED_WEATHER_TASKS=$(aws ecs list-tasks \
            --cluster "$CLUSTER_NAME" \
            --service-name "$WEATHER_SERVICE" \
            --desired-status STOPPED \
            --region "$REGION" \
            --query 'length(taskArns)' \
            --output text 2>/dev/null || echo "0")
        
        echo "    Main Agent: $STOPPED_MAIN_TASKS"
        echo "    Weather Server: $STOPPED_WEATHER_TASKS"
        
        TOTAL_STOPPED=$((STOPPED_MAIN_TASKS + STOPPED_WEATHER_TASKS))
        if [ $TOTAL_STOPPED -gt 0 ]; then
            echo -e "    ${YELLOW}⚠️  Check logs for task failures${NC}"
        fi
        
        # Service discovery info
        echo ""
        echo "🔗 Service Discovery"
        echo "-------------------"
        echo "  Namespace: agriculture.local"
        echo "  Internal endpoints:"
        echo "    - Weather Server: weather.agriculture.local:7071"
        
        # Health check
        echo ""
        echo "🏥 Health Check"
        echo "---------------"
        echo -n "Main Agent Health (via ALB): "
        
        if command -v curl &> /dev/null; then
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_URL/health" --connect-timeout 5)
            if [ "$HTTP_CODE" = "200" ]; then
                echo -e "${GREEN}✅ Healthy${NC}"
            else
                echo -e "${RED}❌ Unhealthy (HTTP $HTTP_CODE)${NC}"
            fi
        else
            echo -e "${YELLOW}⚠️  curl not available${NC}"
        fi
        
        # Example commands
        echo ""
        echo "📝 Example Commands"
        echo "------------------"
        echo ""
        echo "Test the API:"
        echo "  # Weather query example:"
        echo "  curl -X POST \"http://$ALB_URL/query\" \\"
        echo "    -H \"Content-Type: application/json\" \\"
        echo "    -d '{\"query\": \"What is the weather like in Chicago?\"}'"
        echo ""
        echo "  # Agricultural query example:"
        echo "  curl -X POST \"http://$ALB_URL/query\" \\"
        echo "    -H \"Content-Type: application/json\" \\"
        echo "    -d '{\"query\": \"Are conditions good for planting corn in Iowa?\"}'"
        echo ""
        echo "View logs:"
        echo "  Main Agent:"
        echo "    aws logs tail $MAIN_LOG_GROUP --follow"
        echo "  Weather Server:"
        echo "    aws logs tail $WEATHER_LOG_GROUP --follow"
        echo ""
        echo "View task details:"
        echo "  aws ecs list-tasks --cluster $CLUSTER_NAME --region $REGION"
        echo "  aws ecs describe-tasks --cluster $CLUSTER_NAME --tasks <task-arn> --region $REGION"
    fi
else
    echo ""
    echo -e "${YELLOW}⚠️  Base infrastructure not deployed. Run: ./infra/deploy.sh base${NC}"
fi

echo ""
echo "=================================================="