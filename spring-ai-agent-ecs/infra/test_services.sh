#!/bin/bash

# Spring AI MCP Agent Service Testing Script
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
    local lb_dns=$(get_stack_output "$BASE_STACK_NAME" "LoadBalancerDNS")
    
    if [ -z "$lb_dns" ]; then
        log_error "Could not find Load Balancer DNS. Make sure the $BASE_STACK_NAME stack is deployed."
        exit 1
    fi
    
    log_info "✅ Found Load Balancer: ${lb_dns}"
    echo ""
    
    # Test the service
    log_info "🚀 Testing the MCP Agent service..."
    log_warn "Request:"
    echo "POST http://${lb_dns}/inquire"
    echo 'Body: {"question": "Get employees that have skills related to Java, but not Java"}'
    echo ""
    
    log_warn "Response:"
    local response=$(curl -s -X POST --location "http://${lb_dns}/inquire" \
        -H "Content-Type: application/json" \
        -d '{"question": "Get employees that have skills related to Java, but not Java"}' \
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
    
    print_section "📊 Performing additional service checks..."
    
    # Check ECS cluster status
    log_warn "Checking ECS Cluster:"
    local cluster_status=$(get_stack_status "$BASE_STACK_NAME-cluster" || echo "")
    if [ -z "$cluster_status" ]; then
        # Try alternative approach
        cluster_status=$(aws ecs describe-clusters --clusters "$CLUSTER_NAME" --query 'clusters[0].status' --output text 2>/dev/null || echo "Not found")
    fi
    log_info "Cluster Status: $cluster_status"
    
    # List running tasks
    log_warn "Running ECS Tasks:"
    local tasks=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --query 'taskArns' --output json 2>/dev/null || echo "[]")
    local task_count=$(echo "$tasks" | jq 'length' 2>/dev/null || echo "0")
    log_info "Number of running tasks: $task_count"
    
    if [ "$task_count" -gt "0" ]; then
        # Get task details
        log_warn "Task Details:"
        aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks $(echo "$tasks" | jq -r '.[]') \
            --query 'tasks[*].[taskDefinitionArn, lastStatus, desiredStatus, containers[*].[name, lastStatus]]' \
            --output table 2>/dev/null || log_warn "Could not retrieve task details"
    fi
    
    # Check service status using common functions
    log_warn "ECS Services Status:"
    
    echo "Client Service:"
    local client_status=$(get_ecs_service_status "$CLUSTER_NAME" "mcp-client-service")
    log_info "  $client_status"
    
    echo "Server Service:"
    local server_status=$(get_ecs_service_status "$CLUSTER_NAME" "spring-weather-experts-service")
    log_info "  $server_status"
    
    # Check target health
    log_warn "ALB Target Health:"
    
    # Get target group ARNs using common function
    local client_tg=$(get_stack_output "$BASE_STACK_NAME" "ClientTargetGroupArn")
    local server_tg=$(get_stack_output "$BASE_STACK_NAME" "ServerTargetGroupArn")
    
    if [ ! -z "$client_tg" ]; then
        echo "Client Target Group Health:"
        aws elbv2 describe-target-health --target-group-arn "$client_tg" \
            --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State, TargetHealth.Reason]' \
            --output table 2>/dev/null || log_warn "  Could not retrieve health status"
    fi
    
    if [ ! -z "$server_tg" ]; then
        echo "Server Target Group Health:"
        aws elbv2 describe-target-health --target-group-arn "$server_tg" \
            --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State, TargetHealth.Reason]' \
            --output table 2>/dev/null || log_warn "  Could not retrieve health status"
    fi
    
    # Security group check
    log_warn "Security Group Rules:"
    local sg_id=$(get_stack_output "$BASE_STACK_NAME" "SecurityGroupId")
    
    if [ ! -z "$sg_id" ]; then
        echo "Ingress rules for $sg_id:"
        aws ec2 describe-security-groups --group-ids "$sg_id" \
            --query 'SecurityGroups[0].IpPermissions[*].[IpProtocol, FromPort, ToPort, IpRanges[0].CidrIp]' \
            --output table 2>/dev/null || log_warn "  Could not retrieve security group rules"
    fi
    
    # Check task health using ecs-utils
    log_warn "Checking Task Health:"
    if check_task_health "mcp-client-service" "Client" "$CLUSTER_NAME"; then
        log_info "✅ Client service tasks are healthy"
    else
        log_warn "⚠️  Client service tasks may have issues"
    fi
    
    if check_task_health "spring-weather-experts-service" "Server" "$CLUSTER_NAME"; then
        log_info "✅ Server service tasks are healthy"
    else
        log_warn "⚠️  Server service tasks may have issues"
    fi
    
    # Try health endpoint check
    if check_health_endpoint "$lb_dns"; then
        log_info "✅ Health endpoint is responding"
    else
        log_warn "⚠️  Health endpoint check failed or timed out"
    fi
    
    print_section "Troubleshooting Commands"
    echo "1. Check task logs: aws logs tail /ecs/mcp-client --follow"
    echo "2. Check service events: aws ecs describe-services --cluster $CLUSTER_NAME --services mcp-client-service --query 'services[0].events[:5]'"
    echo "3. Check task definition: aws ecs describe-task-definition --task-definition mcp-client-task --query 'taskDefinition.containerDefinitions[0].environment'"
    echo "4. Test direct container access: aws ecs execute-command --cluster $CLUSTER_NAME --task <task-id> --container mcp-client --interactive --command '/bin/sh'"
    echo "5. Check ECR images: aws ecr describe-images --repository-name $ECR_CLIENT_REPO --query 'imageDetails[:5].[imageTags, imagePushedAt]'"
    
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