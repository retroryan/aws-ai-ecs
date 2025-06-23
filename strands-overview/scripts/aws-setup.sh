#!/bin/bash

# AWS Bedrock Setup Script
# This script checks AWS CLI configuration and generates a bedrock.env file
# with available Bedrock models for the user

set -e

echo "🔍 AWS Bedrock Setup Script"
echo "=========================="
echo ""

# Function to print error and exit
error_exit() {
    echo "❌ ERROR: $1" >&2
    exit 1
}

# Function to print info
info() {
    echo "ℹ️  $1"
}

# Function to print success
success() {
    echo "✅ $1"
}

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    error_exit "AWS CLI is not installed. Please install it first: https://aws.amazon.com/cli/"
fi

# Get AWS CLI version
AWS_VERSION=$(aws --version)
info "AWS CLI Version: $AWS_VERSION"
echo ""

# Check AWS configuration
info "Checking AWS configuration..."

# Get current profile
CURRENT_PROFILE="${AWS_PROFILE:-default}"
info "Current AWS Profile: $CURRENT_PROFILE"

# Check if credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    error_exit "AWS credentials not configured. Please run 'aws configure' or set AWS credentials."
fi

# Get account info
ACCOUNT_INFO=$(aws sts get-caller-identity)
ACCOUNT_ID=$(echo $ACCOUNT_INFO | jq -r '.Account')
USER_ARN=$(echo $ACCOUNT_INFO | jq -r '.Arn')
success "AWS credentials verified!"
info "Account ID: $ACCOUNT_ID"
info "User/Role: $USER_ARN"
echo ""

# Get current region
CURRENT_REGION="${AWS_DEFAULT_REGION:-$(aws configure get region || echo "us-east-1")}"
info "Current Region: $CURRENT_REGION"
echo ""

# Check if Bedrock is available in the current region
info "Checking Bedrock availability in $CURRENT_REGION..."
if ! aws bedrock list-foundation-models --region $CURRENT_REGION &> /dev/null; then
    echo "⚠️  WARNING: Unable to access Bedrock in region $CURRENT_REGION"
    echo "   This could mean:"
    echo "   1. Bedrock is not available in this region"
    echo "   2. Your IAM user/role doesn't have Bedrock permissions"
    echo "   3. Bedrock hasn't been enabled in your account"
    echo ""
    echo "   To fix: Go to AWS Console → Bedrock → Model access → Enable models"
    echo ""
    
    # Try to find a region where Bedrock works
    echo "🔍 Searching for regions where Bedrock is accessible..."
    BEDROCK_REGIONS=("us-east-1" "us-west-2" "eu-west-1" "ap-southeast-1" "ap-northeast-1")
    WORKING_REGION=""
    
    for region in "${BEDROCK_REGIONS[@]}"; do
        if aws bedrock list-foundation-models --region $region &> /dev/null 2>&1; then
            WORKING_REGION=$region
            success "Found Bedrock access in region: $region"
            CURRENT_REGION=$region
            break
        fi
    done
    
    if [ -z "$WORKING_REGION" ]; then
        error_exit "Unable to access Bedrock in any common region. Please check your AWS account setup."
    fi
fi

# Get available models
info "Fetching available Bedrock models in $CURRENT_REGION..."
echo ""

# Get raw model data
MODELS_JSON=$(aws bedrock list-foundation-models --region $CURRENT_REGION --output json 2>/dev/null || echo '{"modelSummaries":[]}')

# Get total count for reference
TOTAL_API_MODELS=$(echo "$MODELS_JSON" | jq -r '.modelSummaries | length')
info "Found $TOTAL_API_MODELS models in Bedrock API response"
echo ""

# Create bedrock.env file
cat > bedrock.env << EOF
# AWS Bedrock Configuration
# Generated on $(date)
# AWS Profile: $CURRENT_PROFILE
# AWS Account: $ACCOUNT_ID
# Region: $CURRENT_REGION

# This file contains recommended models for the weather agent demo.
# To use a different model, uncomment its line and comment the current one.

# AWS Region for Bedrock
BEDROCK_REGION=$CURRENT_REGION

# Model Temperature (0-1, lower = more deterministic)
BEDROCK_TEMPERATURE=0

# Recommended Models (uncomment one to use):
EOF

# Counter for available models
MODEL_COUNT=0

# Function to check if model supports tools
check_model_tools() {
    local model_id=$1
    # Models known to support tool use - be more inclusive
    # Most modern models support function/tool calling
    if [[ $model_id == *"anthropic.claude"* ]] || \
       [[ $model_id == *"meta.llama"* ]] || \
       [[ $model_id == *"cohere.command"* ]] || \
       [[ $model_id == *"mistral"* ]] || \
       [[ $model_id == *"amazon.titan"* ]] || \
       [[ $model_id == *"ai21"* ]]; then
        return 0
    fi
    # Show all models but warn about tool support
    return 0
}

# Define model categories and their preferred models (in order of preference)
# Using simple variables instead of associative array for compatibility
MODELS_BEST_PERFORMANCE="anthropic.claude-3-5-sonnet-20241022-v2:0|anthropic.claude-3-5-sonnet-20240620-v1:0"
MODELS_FAST_CHEAP="anthropic.claude-3-haiku-20240307-v1:0"
MODELS_OPEN_SOURCE="meta.llama3-1-70b-instruct-v1:0|meta.llama3-70b-instruct-v1:0|meta.llama3-8b-instruct-v1:0"
MODELS_RAG_OPTIMIZED="cohere.command-r-plus-v1:0|cohere.command-r-v1:0"

# Parse available models and filter for recommended ones
FOUND_MODELS=()
while IFS= read -r model_id; do
    if [ -n "$model_id" ]; then
        FOUND_MODELS+=("$model_id")
    fi
done < <(echo "$MODELS_JSON" | jq -r '.modelSummaries[] | .modelId' | sort -u)

# Track which categories we've found
SELECTED_MODELS=()
MODEL_COUNT=0

# Function to check if model is in our found list
model_exists() {
    local model=$1
    for found in "${FOUND_MODELS[@]}"; do
        if [[ "$found" == "$model" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to add model to env file
add_model_to_env() {
    local model_id=$1
    local description=$2
    local is_default=$3
    
    if [ "$is_default" = "true" ]; then
        echo "BEDROCK_MODEL_ID=$model_id" >> bedrock.env
        echo "" >> bedrock.env
        echo "✓ $model_id"
        echo "  └─ $description (set as default)"
    else
        echo "# BEDROCK_MODEL_ID=$model_id" >> bedrock.env
        echo "✓ $model_id"
        echo "  └─ $description"
    fi
    echo ""
}

# Check each category and add the first available model
echo "📋 Recommended Models Available in Your Account:"
echo "-----------------------------------------------"
echo ""

# Best Performance (Claude 3.5 Sonnet)
IFS='|' read -ra MODELS <<< "$MODELS_BEST_PERFORMANCE"
for model in "${MODELS[@]}"; do
    if model_exists "$model"; then
        add_model_to_env "$model" "Best overall performance" "$([[ $MODEL_COUNT -eq 0 ]] && echo true || echo false)"
        SELECTED_MODELS+=("$model")
        ((MODEL_COUNT++))
        break
    fi
done

# Fast & Cheap (Claude 3 Haiku)
if model_exists "$MODELS_FAST_CHEAP"; then
    add_model_to_env "$MODELS_FAST_CHEAP" "Fast and cost-effective" "$([[ $MODEL_COUNT -eq 0 ]] && echo true || echo false)"
    SELECTED_MODELS+=("$MODELS_FAST_CHEAP")
    ((MODEL_COUNT++))
fi

# Open Source (Llama 3)
IFS='|' read -ra MODELS <<< "$MODELS_OPEN_SOURCE"
for model in "${MODELS[@]}"; do
    if model_exists "$model"; then
        # Determine size
        size_desc="70B"
        [[ "$model" == *"8b"* ]] && size_desc="8B - lightweight"
        [[ "$model" == *"405b"* ]] && size_desc="405B - largest"
        add_model_to_env "$model" "Open source, $size_desc" "$([[ $MODEL_COUNT -eq 0 ]] && echo true || echo false)"
        SELECTED_MODELS+=("$model")
        ((MODEL_COUNT++))
        break
    fi
done

# RAG Optimized (Cohere)
IFS='|' read -ra MODELS <<< "$MODELS_RAG_OPTIMIZED"
for model in "${MODELS[@]}"; do
    if model_exists "$model"; then
        desc="Optimized for RAG and tool use"
        [[ "$model" == *"command-r-v"* ]] && desc="Efficient RAG model"
        add_model_to_env "$model" "$desc" "$([[ $MODEL_COUNT -eq 0 ]] && echo true || echo false)"
        SELECTED_MODELS+=("$model")
        ((MODEL_COUNT++))
        break
    fi
done

# If user wants to see all models, they can use DEBUG mode
if [ "${SHOW_ALL_MODELS:-false}" = "true" ]; then
    echo "" >> bedrock.env
    echo "# Other available models:" >> bedrock.env
    for model in "${FOUND_MODELS[@]}"; do
        # Skip if already added
        if [[ ! " ${SELECTED_MODELS[@]} " =~ " ${model} " ]]; then
            echo "# BEDROCK_MODEL_ID=$model" >> bedrock.env
        fi
    done
fi

# Add AWS credentials section if not using IAM role
if [[ ! "$USER_ARN" =~ "assumed-role" ]]; then
    echo "" >> bedrock.env
    echo "# AWS Credentials (if not using IAM role)" >> bedrock.env
    echo "# AWS_ACCESS_KEY_ID=your_access_key" >> bedrock.env
    echo "# AWS_SECRET_ACCESS_KEY=your_secret_key" >> bedrock.env
fi

# Add logging configuration
echo "" >> bedrock.env
echo "# Optional: Logging level (default: INFO)" >> bedrock.env
echo "LOG_LEVEL=INFO" >> bedrock.env

if [ $MODEL_COUNT -eq 0 ]; then
    echo "⚠️  WARNING: No recommended models found in your account!"
    echo ""
    echo "   The weather agent works best with these models:"
    echo "   • Claude 3.5 Sonnet - Best overall performance"
    echo "   • Claude 3 Haiku - Fast and cost-effective"
    echo "   • Llama 3 70B/8B - Open source option"
    echo "   • Cohere Command R+ - Optimized for tool use"
    echo ""
    echo "   Please enable model access in the AWS Bedrock console:"
    echo "   https://console.aws.amazon.com/bedrock/home?region=$CURRENT_REGION#/modelaccess"
    echo ""
    echo "   Total models in account: ${#FOUND_MODELS[@]}"
    echo "   (Run with SHOW_ALL_MODELS=true to see all available models)"
else
    echo ""
    success "Found $MODEL_COUNT recommended models for the demo!"
    echo ""
    echo "💡 Tip: To see all ${#FOUND_MODELS[@]} available models, run:"
    echo "   SHOW_ALL_MODELS=true ./aws-setup.sh"
fi

echo ""
echo "📄 Generated bedrock.env file"
echo ""
echo "To use this configuration:"
echo "  cp bedrock.env .env"
echo ""
echo "To switch models, edit .env and uncomment a different BEDROCK_MODEL_ID line."
echo ""

# Check for common issues
echo "🔍 Checking for common issues..."

# Check IAM permissions with detailed diagnostics
echo ""
info "Checking IAM permissions..."

# Test specific Bedrock permissions
PERMISSIONS_OK=true
MISSING_PERMISSIONS=()

# Test ListFoundationModels
if ! aws bedrock list-foundation-models --region $CURRENT_REGION --max-results 1 &> /dev/null; then
    PERMISSIONS_OK=false
    MISSING_PERMISSIONS+=("bedrock:ListFoundationModels")
fi

# Test GetFoundationModel (pick a common model)
if ! aws bedrock get-foundation-model --model-identifier anthropic.claude-3-haiku-20240307-v1:0 --region $CURRENT_REGION &> /dev/null 2>&1; then
    # This might fail if model doesn't exist, so check error type
    ERROR_MSG=$(aws bedrock get-foundation-model --model-identifier anthropic.claude-3-haiku-20240307-v1:0 --region $CURRENT_REGION 2>&1 || true)
    if [[ $ERROR_MSG == *"AccessDeniedException"* ]]; then
        PERMISSIONS_OK=false
        MISSING_PERMISSIONS+=("bedrock:GetFoundationModel")
    fi
fi

# Test InvokeModel permission (dry run)
TEST_PAYLOAD='{"prompt": "\n\nHuman: Hi\n\nAssistant:", "max_tokens": 1}'
if ! aws bedrock invoke-model \
    --model-id anthropic.claude-instant-v1 \
    --body "$(echo -n "$TEST_PAYLOAD" | base64)" \
    --region $CURRENT_REGION \
    --no-paginate \
    --output text &> /dev/null 2>&1; then
    ERROR_MSG=$(aws bedrock invoke-model \
        --model-id anthropic.claude-instant-v1 \
        --body "$(echo -n "$TEST_PAYLOAD" | base64)" \
        --region $CURRENT_REGION 2>&1 || true)
    if [[ $ERROR_MSG == *"AccessDeniedException"* ]]; then
        PERMISSIONS_OK=false
        MISSING_PERMISSIONS+=("bedrock:InvokeModel")
    fi
fi

if [ "$PERMISSIONS_OK" = true ]; then
    success "IAM permissions verified!"
else
    echo "⚠️  WARNING: Missing IAM permissions for Bedrock"
    echo ""
    echo "   Missing permissions:"
    for perm in "${MISSING_PERMISSIONS[@]}"; do
        echo "   - $perm"
    done
    echo ""
    echo "   Add this policy to your IAM user/role:"
    echo "   {"
    echo '     "Version": "2012-10-17",'
    echo '     "Statement": ['
    echo "       {"
    echo '         "Effect": "Allow",'
    echo '         "Action": ['
    echo '           "bedrock:ListFoundationModels",'
    echo '           "bedrock:GetFoundationModel",'
    echo '           "bedrock:InvokeModel",'
    echo '           "bedrock:InvokeModelWithResponseStream"'
    echo "         ],"
    echo '         "Resource": "*"'
    echo "       }"
    echo "     ]"
    echo "   }"
fi

# Remind about model access
echo ""
echo "📌 Important: Make sure you have enabled model access in the AWS Console:"
echo "   https://console.aws.amazon.com/bedrock/home?region=$CURRENT_REGION#/modelaccess"
echo ""
echo "✨ Setup complete!"