#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

echo "Starting Agriculture Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Export AWS credentials if available
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
    export $(aws configure export-credentials --format env-no-export 2>/dev/null)
    echo "✓ AWS credentials exported"
fi

# Set AWS_SESSION_TOKEN to empty if not set (to avoid docker-compose warning)
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}

# Start services
docker-compose up -d

echo ""
echo "Services started!"
echo "Run ./scripts/test_docker.sh to test the services"