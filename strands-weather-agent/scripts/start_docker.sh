#!/bin/bash

# Start script for Docker Compose with AWS credentials
set -e

# Parse command line arguments
DEBUG_MODE=""
TELEMETRY_MODE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --debug|-d)
            DEBUG_MODE="true"
            shift
            ;;
        --telemetry|-t)
            TELEMETRY_MODE="true"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --debug, -d      Enable debug logging"
            echo "  --telemetry, -t  Enable Langfuse telemetry"
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
if [ "$DEBUG_MODE" = "true" ] && [ "$TELEMETRY_MODE" = "true" ]; then
    STARTUP_MSG="$STARTUP_MSG with DEBUG logging and TELEMETRY enabled..."
elif [ "$DEBUG_MODE" = "true" ]; then
    STARTUP_MSG="$STARTUP_MSG with DEBUG logging enabled..."
elif [ "$TELEMETRY_MODE" = "true" ]; then
    STARTUP_MSG="$STARTUP_MSG with TELEMETRY enabled..."
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

# Export AWS credentials if available
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
    # Export credentials - this works with profiles, SSO, and temporary credentials
    eval $(aws configure export-credentials --format env 2>/dev/null)
    echo "✓ AWS credentials exported"
    # Show which AWS account we're using (without exposing sensitive info)
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
    echo "✓ Using AWS Account: $ACCOUNT_ID"
    
    # Debug: Check if credentials are actually exported
    if [ -z "$AWS_ACCESS_KEY_ID" ]; then
        echo "⚠️  Warning: AWS_ACCESS_KEY_ID not exported. Trying alternative method..."
        # Alternative method that works with profiles
        export AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile ${AWS_PROFILE:-default})
        export AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile ${AWS_PROFILE:-default})
        export AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile ${AWS_PROFILE:-default} 2>/dev/null || echo "")
        
        if [ -n "$AWS_ACCESS_KEY_ID" ]; then
            echo "✓ AWS credentials exported using profile method"
        else
            echo "❌ Failed to export AWS credentials"
            echo "   Please ensure your AWS CLI is properly configured"
            exit 1
        fi
    fi
else
    echo "⚠️  Warning: AWS CLI not configured or credentials not accessible"
    echo "   Docker containers will rely on credentials from .env file"
fi

# Set AWS_SESSION_TOKEN to empty if not set (to avoid docker-compose warning)
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}

# Export debug mode if enabled
if [ "$DEBUG_MODE" = "true" ]; then
    export WEATHER_AGENT_DEBUG=true
    echo "✓ Debug mode enabled (WEATHER_AGENT_DEBUG=true)"
fi

# Export telemetry mode if enabled
if [ "$TELEMETRY_MODE" = "true" ]; then
    export ENABLE_TELEMETRY=true
    echo "✓ Telemetry mode enabled (ENABLE_TELEMETRY=true)"
    
    # Check if Langfuse credentials are configured
    if [ -z "${LANGFUSE_PUBLIC_KEY}" ] || [ -z "${LANGFUSE_SECRET_KEY}" ]; then
        echo "⚠️  Warning: Langfuse credentials not found in .env file"
        echo "   Telemetry will be disabled unless credentials are set"
    fi
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