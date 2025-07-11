#!/bin/bash

# AWS Setup Script for Bedrock Configuration
# This script checks AWS CLI setup and generates a bedrock.env file with available models

set -e

echo "==================================="
echo "AWS Bedrock Setup Script"
echo "==================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ ERROR: AWS CLI is not installed."
    echo "Please install AWS CLI first: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

echo "✅ AWS CLI is installed"
echo "AWS CLI version: $(aws --version)"
echo ""

# Get current AWS profile and account info
echo "Getting AWS account information..."
CURRENT_PROFILE="${AWS_PROFILE:-default}"
ACCOUNT_INFO=$(aws sts get-caller-identity 2>/dev/null || echo '{"Account": "unknown", "Arn": "unknown"}')
ACCOUNT_ID=$(echo $ACCOUNT_INFO | jq -r '.Account')
USER_ARN=$(echo $ACCOUNT_INFO | jq -r '.Arn')

echo "✅ Using AWS credentials"
echo "Current profile: $CURRENT_PROFILE"
if [ "$ACCOUNT_ID" != "unknown" ]; then
    echo "Account ID: $ACCOUNT_ID"
    echo "User/Role ARN: $USER_ARN"
fi
echo ""

# Get the current region
CURRENT_REGION=$(aws configure get region || echo "us-east-1")
echo "Current region: $CURRENT_REGION"
echo ""

# Check if Bedrock is available in the current region
echo "Checking Bedrock availability in $CURRENT_REGION..."
if ! aws bedrock list-foundation-models --region $CURRENT_REGION &> /dev/null; then
    echo "⚠️  WARNING: Unable to list Bedrock models. This could mean:"
    echo "   - Bedrock is not available in your region ($CURRENT_REGION)"
    echo "   - You don't have permissions to access Bedrock"
    echo "   - Your account doesn't have Bedrock enabled"
    echo ""
    echo "Continuing with default configuration..."
    
    # Create default bedrock.env
    cat > bedrock.env << EOF
# Bedrock Configuration - Generated by aws-setup.sh
# WARNING: Unable to detect available models. Using defaults.
# Please verify these settings match your AWS Bedrock setup.

BEDROCK_MODEL_ID=anthropic.claude-v2
BEDROCK_REGION=$CURRENT_REGION
BEDROCK_MAX_TOKENS=500
BEDROCK_TEMPERATURE=0.7

# AWS Profile (optional - remove if using IAM roles in ECS)
# AWS_PROFILE=$CURRENT_PROFILE
EOF
    
    echo "Created bedrock.env with default settings"
    echo ""
    echo "📝 To use this configuration:"
    echo "   cp bedrock.env server/.env"
    echo ""
    echo "⚠️  Please verify that you have access to Bedrock and the model specified."
    exit 0
fi

# List available models
echo "✅ Bedrock is available!"
echo "Fetching available models..."
echo ""

# Get all available models
MODELS=$(aws bedrock list-foundation-models --region $CURRENT_REGION --output json)

# Extract Claude models (since our code is designed for Claude)
CLAUDE_MODELS=$(echo $MODELS | jq -r '.modelSummaries[] | select(.modelId | contains("claude")) | .modelId' | sort -u)

if [ -z "$CLAUDE_MODELS" ]; then
    echo "⚠️  No Claude models found. Checking all available models..."
    ALL_MODELS=$(echo $MODELS | jq -r '.modelSummaries[].modelId' | sort -u)
    echo "Available models:"
    echo "$ALL_MODELS" | sed 's/^/  - /'
    SELECTED_MODEL="anthropic.claude-v2"
    echo ""
    echo "Using default model: $SELECTED_MODEL"
else
    echo "Available Claude models:"
    echo "$CLAUDE_MODELS" | sed 's/^/  - /'
    
    # Select the most recent Claude model
    if echo "$CLAUDE_MODELS" | grep -q "anthropic.claude-3"; then
        # Prefer Claude 3 if available
        SELECTED_MODEL=$(echo "$CLAUDE_MODELS" | grep "anthropic.claude-3" | tail -1)
    else
        # Otherwise use the most recent Claude 2 model
        SELECTED_MODEL=$(echo "$CLAUDE_MODELS" | tail -1)
    fi
    echo ""
    echo "Selected model: $SELECTED_MODEL"
fi

# Create bedrock.env file
echo ""
echo "Creating bedrock.env file..."

cat > bedrock.env << EOF
# Bedrock Configuration - Generated by aws-setup.sh
# Generated on: $(date)
# AWS Account: $ACCOUNT_ID
# AWS Region: $CURRENT_REGION
# AWS Profile: $CURRENT_PROFILE

# Bedrock Model Configuration
BEDROCK_MODEL_ID=$SELECTED_MODEL
BEDROCK_REGION=$CURRENT_REGION
BEDROCK_MAX_TOKENS=500
BEDROCK_TEMPERATURE=0.7

# Optional: AWS Profile (remove this when deploying to ECS with IAM roles)
# AWS_PROFILE=$CURRENT_PROFILE

# Optional: Customize these values as needed
# BEDROCK_MAX_TOKENS - Maximum tokens in response (100-4096 depending on model)
# BEDROCK_TEMPERATURE - Response randomness (0.0-1.0, lower is more deterministic)
EOF

echo "✅ Successfully created bedrock.env"
echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "📝 To use this configuration in your local development:"
echo "   cp bedrock.env server/.env"
echo ""
echo "🚀 The server will use these environment variables to connect to AWS Bedrock."
echo ""
echo "💡 Tips:"
echo "   - For ECS deployment, remove AWS_PROFILE and use IAM task roles instead"
echo "   - Adjust BEDROCK_MAX_TOKENS based on your needs (affects cost)"
echo "   - Lower BEDROCK_TEMPERATURE for more consistent responses"
echo ""

# Make the script executable
chmod +x aws-setup.sh