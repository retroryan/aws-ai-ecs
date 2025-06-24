#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

echo "Starting Strands Weather Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Load environment variables from .env if it exists
if [ -f .env ]; then
    # Use set -a to export all variables, handle quotes and spaces properly
    set -a
    source .env
    set +a
    echo "✓ Environment variables loaded from .env"
fi

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

# Check if BEDROCK_MODEL_ID is set, use default if not
if [ -z "${BEDROCK_MODEL_ID}" ]; then
    # Set a default model ID
    export BEDROCK_MODEL_ID="us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    echo "ℹ️  BEDROCK_MODEL_ID not set, using default: ${BEDROCK_MODEL_ID}"
    echo "   To use a different model, set it in your .env file"
fi

# Start services
docker compose up -d

echo ""
echo "Services started!"
echo "Run ./scripts/test_docker.sh to test the services"