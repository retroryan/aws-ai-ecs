#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

# Check for add-experts parameter
COMPOSE_PROFILES=""
if [ "$1" = "add-experts" ]; then
    COMPOSE_PROFILES="--profile experts"
    echo "Starting Strands Weather Agent services with Experts server..."
else
    echo "Starting Strands Weather Agent services (without Experts server)..."
    echo "Use './scripts/start_docker.sh add-experts' to include the Experts server"
fi

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

# Check if BEDROCK_MODEL_ID is set
if [ -z "${BEDROCK_MODEL_ID}" ]; then
  echo "🛑 Error: BEDROCK_MODEL_ID is not set."
  echo "   Please set BEDROCK_MODEL_ID in your .env file."
  exit 1
fi

# Start services, forcing a rebuild
docker compose $COMPOSE_PROFILES up --build -d

echo ""
echo "Services started!"
if [ "$1" = "add-experts" ]; then
    echo "Experts server included on port 7781"
fi
echo "Run ./scripts/test_docker.sh to test the services"