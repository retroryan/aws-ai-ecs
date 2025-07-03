#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

# Parse command line arguments
DEBUG_MODE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug|-d)
            DEBUG_MODE="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --debug, -d    Enable debug logging"
            echo "  --help, -h     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$DEBUG_MODE" = "true" ]; then
    echo "Starting Strands Weather Agent services with DEBUG logging enabled..."
else
    echo "Starting Strands Weather Agent services..."
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

# Export debug mode if enabled
if [ "$DEBUG_MODE" = "true" ]; then
    export WEATHER_AGENT_DEBUG=true
    echo "✓ Debug mode enabled (WEATHER_AGENT_DEBUG=true)"
fi

# Check if BEDROCK_MODEL_ID is set
if [ -z "${BEDROCK_MODEL_ID}" ]; then
  echo "🛑 Error: BEDROCK_MODEL_ID is not set."
  echo "   Please set BEDROCK_MODEL_ID in your .env file."
  exit 1
fi

# Start services, forcing a rebuild
docker compose up --build -d

echo ""
echo "Services started!"
echo "Run ./scripts/test_docker.sh to test the services"