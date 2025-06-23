#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

echo "Starting AWS Strands Weather Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Export AWS credentials if available
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
    export $(aws configure export-credentials --format env-no-export 2>/dev/null)
    echo "✓ AWS credentials exported"
    
    # Display current AWS identity
    AWS_IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null || echo "Unknown")
    echo "✓ Using AWS identity: $AWS_IDENTITY"
else
    echo "⚠ AWS CLI not available or not configured - services will run without AWS credentials"
fi

# Set AWS environment variables to empty if not set (to avoid docker-compose warnings)
export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}

# Start services
docker compose up -d

echo ""
echo "Services started!"
echo "Run ./scripts/test_docker.sh to test the services"