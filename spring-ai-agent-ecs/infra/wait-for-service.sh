#!/bin/bash

# Simple script to wait for an ECS service to be stable

set -e

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Configuration
SERVICE_NAME="${1:-}"
CLUSTER_NAME="${2:-$DEFAULT_CLUSTER_NAME}"
REGION="${AWS_REGION:-$DEFAULT_REGION}"
MAX_WAIT="${3:-120}"
CHECK_INTERVAL=10

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: $0 <service-name> [cluster-name] [max-wait-seconds]"
    echo "Example: $0 spring-ai-mcp-services-server"
    exit 1
fi

# Use the comprehensive wait function from ecs-utils.sh
if wait_for_service_stable "$SERVICE_NAME" "Service" $MAX_WAIT "$CLUSTER_NAME" "$REGION"; then
    log_info "Service $SERVICE_NAME is stable and healthy!"
    exit 0
else
    log_error "Service $SERVICE_NAME did not stabilize within $MAX_WAIT seconds"
    exit 1
fi