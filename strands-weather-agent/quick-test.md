# Quick Test Guide - AWS Strands + Langfuse Demo

Get the demo running in under 10 minutes! This guide shows the fastest path to deploy and test the AWS Strands Weather Agent with Langfuse telemetry.

## Prerequisites

- AWS CLI configured with credentials
- Python 3.11+
- Docker installed
- AWS account with Bedrock access enabled

## Step 1: Clone and Setup (1 minute)

```bash
# Clone the repository
git clone <repository-url>
cd strands-weather-agent

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Step 2: Configure Bedrock (1 minute)

Edit `.env` and add your Bedrock model:

```bash
# Edit .env file
# Use one of these supported models:
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0  # Inference profile (recommended)
# OR
# BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0   # Direct model
# BEDROCK_MODEL_ID=amazon.nova-lite-v1:0                       # Amazon Nova

BEDROCK_REGION=us-east-1
```

## Step 3: Configure Langfuse (Optional - 1 minute)

For telemetry, create `cloud.env`:

```bash
# Copy template
cp cloud.env.example cloud.env

# Edit cloud.env and add your Langfuse credentials:
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxx
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

**Note**: If you skip this step, the demo works perfectly without telemetry!

## Step 4: Deploy Everything (5-7 minutes)

```bash
# One command deployment!
python3 infra/deploy.py all

# This will:
# - Create ECR repositories
# - Authenticate Docker with ECR
# - Build and push Docker images
# - Deploy CloudFormation stacks
# - Store Langfuse credentials (if configured)
# - Start all services
```

**Note**: If you see "Docker authentication token has expired", the script will now automatically re-authenticate.

## Step 5: Test the Deployment (2 minutes)

### Quick Health Check
```bash
# Run all tests
python3 infra/test_services.py
```

You should see:
- ✅ Health check passed
- ✅ All 4 ECS services running
- ✅ MCP servers connected
- ✅ Queries working

### Run the Demo
```bash
# Run interactive demo with sample queries
python3 infra/demo_telemetry.py
```

This runs real weather queries and shows telemetry status.

### Full Validation
```bash
# Run comprehensive validation
./infra/validate_deployment.sh
```

## Step 6: Access the Service

After deployment completes, you'll see:
```
🌐 Application URL: http://alb-xxxxx.us-east-1.elb.amazonaws.com
📚 API Docs: http://alb-xxxxx.us-east-1.elb.amazonaws.com/docs
```

### Try Some Queries

Using curl:
```bash
# Set your ALB URL
export ALB_URL="http://your-alb-url-here"

# Simple weather query
curl -X POST $ALB_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}'

# Agricultural query
curl -X POST $ALB_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Should I plant tomatoes in Minneapolis this week?"}'
```

Or use the interactive API docs at `http://your-alb-url/docs`

## Verify Telemetry (If Configured)

If you added Langfuse credentials:

1. Run some queries (using curl or the demo script)
2. Open your Langfuse dashboard
3. Look for traces with:
   - Session IDs from your queries
   - Token usage and costs
   - Latency metrics
   - Tool call details

## Testing Telemetry Toggle

```bash
# Deploy WITH telemetry (default)
python3 infra/deploy.py services

# Deploy WITHOUT telemetry
python3 infra/deploy.py services --disable-telemetry

# Check status
python3 infra/deploy.py status
```

## Cleanup

When you're done testing:

```bash
# Delete services stack
aws cloudformation delete-stack --stack-name strands-weather-agent-services

# Delete base stack
aws cloudformation delete-stack --stack-name strands-weather-agent-base

# Or use AWS Console to delete the stacks
```

## Troubleshooting

### BedrockModelId AllowedValues error?
```bash
# The model ID must be in the allowed list. Common supported models:
# - us.anthropic.claude-3-5-sonnet-20241022-v2:0 (inference profile)
# - anthropic.claude-3-5-sonnet-20240620-v1:0 (direct)
# - amazon.nova-lite-v1:0
# - amazon.nova-pro-v1:0

# Update your .env file with a supported model, then retry
```

### Docker push failing with authentication error?
```bash
# The build script now auto-authenticates, but if needed:
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Then retry
python3 infra/deploy.py all
```

### Services not starting?
```bash
# Check ECS service logs
aws logs tail /ecs/strands-weather-agent-main --follow
```

### Telemetry not showing?
```bash
# Verify configuration
python3 infra/integration_test.py
```

### Need more help?
See `docs/telemetry-troubleshooting.md` for detailed troubleshooting.

## What You've Deployed

- **4 ECS Services**: Main agent + 3 MCP servers
- **AWS Strands Agent**: Orchestrates AI queries across services
- **Langfuse Integration**: Optional telemetry and observability
- **Auto-scaling**: Configured for the main service
- **Secure Credentials**: Using AWS Parameter Store

## Next Steps

1. Explore the API documentation
2. Check Langfuse dashboard for traces (if configured)
3. Try different weather and agricultural queries
4. Review the code to understand the integration

**Time to First Query: ~10 minutes** 🚀