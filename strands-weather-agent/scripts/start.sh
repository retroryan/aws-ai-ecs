#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

echo "Starting Strands Weather Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Export AWS credentials if available
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
    export $(aws configure export-credentials --format env-no-export 2>/dev/null)
    echo "✓ AWS credentials exported"
    # Show which AWS account we're using (without exposing sensitive info)
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
    echo "✓ Using AWS Account: $ACCOUNT_ID"
fi

# Set AWS_SESSION_TOKEN to empty if not set (to avoid docker-compose warning)
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}

# Check if BEDROCK_MODEL_ID is set
if [ -z "${BEDROCK_MODEL_ID}" ]; then
    echo "⚠️  Warning: BEDROCK_MODEL_ID is not set"
    echo "   Set it in your .env file or export it:"
    echo "   export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0"
fi

# Start services
docker compose up -d

echo ""
echo "Services started!"
echo "Run ./scripts/test_docker.sh to test the services"