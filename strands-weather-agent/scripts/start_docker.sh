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
            echo "  --debug, -d      Enable debug logging"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build startup message
STARTUP_MSG="Starting Strands Weather Agent services"
if [ "$DEBUG_MODE" = "true" ]; then
    STARTUP_MSG="$STARTUP_MSG with DEBUG logging enabled..."
else
    STARTUP_MSG="$STARTUP_MSG..."
fi
echo "$STARTUP_MSG"

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

# Export AWS credentials for Docker Compose
echo "Configuring AWS credentials..."

# Check if credentials are already in environment
if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "✓ Using existing AWS credentials from environment"
    export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}
else
    # Try to get credentials from AWS CLI config
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
        # For AWS CLI v2, use export-credentials if available
        if aws configure export-credentials --help &> /dev/null 2>&1; then
            eval $(aws configure export-credentials --format env)
            export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}
        else
            # For AWS CLI v1, extract from config files
            export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id)
            export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key)
            export AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")
        fi
        
        if [ -n "$AWS_ACCESS_KEY_ID" ]; then
            echo "✓ AWS credentials exported successfully"
            # Show which AWS account we're using
            ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
            echo "✓ Using AWS Account: $ACCOUNT_ID"
        else
            echo "❌ Failed to export AWS credentials"
            exit 1
        fi
    else
        echo "❌ AWS CLI not found or credentials not configured"
        echo ""
        echo "Please ensure you have valid AWS credentials configured:"
        echo "  - Run 'aws configure' to set up credentials"
        echo "  - Or run 'aws sso login' if using SSO"
        echo "  - Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env file"
        echo ""
        echo "Test your credentials with: aws sts get-caller-identity"
        exit 1
    fi
fi

# Export debug mode if enabled
if [ "$DEBUG_MODE" = "true" ]; then
    export WEATHER_AGENT_DEBUG=true
    echo "✓ Debug mode enabled (WEATHER_AGENT_DEBUG=true)"
fi

# Check if Langfuse is configured (for informational purposes)
if [ -n "${LANGFUSE_PUBLIC_KEY}" ] && [ -n "${LANGFUSE_SECRET_KEY}" ]; then
    echo "✓ Langfuse credentials found - telemetry will auto-detect availability"
fi

# Check if BEDROCK_MODEL_ID is set
if [ -z "${BEDROCK_MODEL_ID}" ]; then
  echo "🛑 Error: BEDROCK_MODEL_ID is not set."
  echo "   Please set BEDROCK_MODEL_ID in your .env file."
  exit 1
fi

# Start services
# Check if Langfuse network exists for auto-detection
if docker network ls | grep -q "langfuse_default" && [ -n "${LANGFUSE_PUBLIC_KEY}" ] && [ -n "${LANGFUSE_SECRET_KEY}" ]; then
    # Langfuse is available and configured - use integrated configuration
    echo "✓ Langfuse network detected - using integrated configuration"
    docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up --build -d
else
    # Use standard compose configuration
    docker compose up --build -d
fi

echo ""
echo "Services started!"
echo "✓ Weather Agent API: http://localhost:7777"

# Show Langfuse info if it was auto-detected
if docker network ls | grep -q "langfuse_default" && [ -n "${LANGFUSE_PUBLIC_KEY}" ] && [ -n "${LANGFUSE_SECRET_KEY}" ]; then
    echo "✓ Connected to local Langfuse instance"
    echo ""
    echo "View metrics and traces at: http://localhost:3000"
fi

if [ "$DEBUG_MODE" = "true" ]; then
    echo ""
    echo "Debug logs will be saved to:"
    echo "  logs/weather_agent_debug_*.log"
    echo ""
    echo "To view logs in real-time:"
    echo "  docker compose logs -f weather-agent"
fi

echo ""
echo "Run ./scripts/test_docker.sh to test the services"