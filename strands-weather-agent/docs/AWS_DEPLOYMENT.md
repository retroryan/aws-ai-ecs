# AWS ECS Deployment Guide

## Prerequisites

Before deploying to AWS ECS, ensure you have:
- ✅ AWS CLI configured with appropriate credentials
- ✅ AWS account with Bedrock access enabled (see main README)
- ✅ Docker installed for building images
- ✅ Python 3.12+ for running deployment scripts

## Deployment Options

### Option 1: Deploy with Langfuse Observability (Recommended)

#### 1. Deploy Langfuse to AWS

For production observability, first deploy Langfuse to your AWS cloud:
- See https://github.com/retroryan/langfuse-samples/tree/main/langfuse-aws for an easy deployment guide
- After deployment, login to Langfuse and create a new project
- Generate API keys from the project settings

#### 2. Configure Environment

```bash
# Copy and configure cloud environment
cp cloud.env.example cloud.env

# Edit cloud.env to add:
# - Your Langfuse API keys (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST)
# - Copy your BEDROCK_MODEL_ID from .env
# - Any other custom settings
```

### Option 2: Deploy without Langfuse

Simply skip the Langfuse configuration step. The system will automatically detect the absence of Langfuse credentials and run without telemetry.

## Deployment Process

### 1. Setup and Validation

```bash
# Setup AWS and validate environment
python infra/commands/setup.py
```

This command will:
- Check AWS CLI configuration
- Verify AWS credentials
- Test Bedrock access
- Validate environment configuration

### 2. Deploy Complete Infrastructure

```bash
# Deploy everything in one command
python infra/deploy.py all
```

This deploys:
- ECR repositories for Docker images
- VPC with public/private subnets
- ECS cluster with Fargate
- Application Load Balancer (ALB)
- All services with auto-scaling
- CloudWatch logging
- Langfuse telemetry (if configured)

### 3. Check Deployment Status

```bash
# View deployment status
python infra/status.py

# Test the deployed services
python infra/tests/test_services.py
```

## What Gets Deployed

### Infrastructure Components
- **VPC**: Isolated network with public/private subnets
- **ECS Cluster**: Fargate-based container orchestration
- **ALB**: Load balancer for external access
- **ECR**: Container registries for Docker images
- **CloudWatch**: Centralized logging

### Services
1. **Weather Agent Service**:
   - Main API service on port 7777
   - Health checks and auto-scaling
   - Session management

2. **MCP Servers** (3 separate services):
   - Forecast Server (port 7778)
   - Historical Server (port 7779)
   - Agricultural Server (port 7780)
   - Internal service discovery

### Auto-Scaling Configuration
- CPU-based scaling (70% threshold)
- Memory-based scaling (80% threshold)
- Min: 1 task, Max: 4 tasks per service

## Deployment Commands Reference

### Individual Deployment Steps

If you prefer to deploy components separately:

```bash
# 1. Create ECR repositories
python infra/deploy.py ecr

# 2. Build and push Docker images
python infra/deploy.py build

# 3. Deploy base infrastructure (VPC, ECS cluster, ALB)
python infra/deploy.py base

# 4. Deploy all services
python infra/deploy.py services
```

### Update Existing Deployment

```bash
# Update only the services (after code changes)
python infra/deploy.py build
python infra/deploy.py services

# Update specific service
python infra/deploy.py build --service weather-agent
python infra/deploy.py services --service weather-agent
```

## Monitoring and Debugging

### CloudWatch Logs

All services log to CloudWatch. View logs:

```bash
# Using AWS CLI
aws logs tail /ecs/strands-weather-agent/weather-agent --follow

# View specific MCP server logs
aws logs tail /ecs/strands-weather-agent/forecast-server --follow
aws logs tail /ecs/strands-weather-agent/historical-server --follow
aws logs tail /ecs/strands-weather-agent/agricultural-server --follow
```

### Service Health

```bash
# Check ECS service status
aws ecs describe-services \
  --cluster strands-weather-agent-cluster \
  --services weather-agent-service

# Check ALB health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

## Cost Optimization

### Fargate Pricing
- Each service runs as a Fargate task
- Default: 0.25 vCPU, 0.5 GB memory per task
- Approximate cost: ~$9/month per service

### Cost Reduction Tips
1. **Use Spot Fargate**: Up to 70% cost savings
2. **Adjust task sizes**: Reduce CPU/memory if underutilized
3. **Enable auto-scaling**: Scale down during low usage
4. **Schedule scaling**: Scale to zero during off-hours

## Cleanup

Remove all AWS resources when done:

```bash
# Remove in reverse order
./infra/deploy.sh cleanup-services  # Remove ECS services
./infra/deploy.sh cleanup-base      # Remove VPC, ALB, cluster
./infra/deploy.sh cleanup-ecr       # Remove ECR repositories (optional)
```

## Troubleshooting Deployment

### Common Issues

1. **ECR Login Failed**:
   ```bash
   # Manually login to ECR
   aws ecr get-login-password --region us-west-2 | \
     docker login --username AWS --password-stdin \
     <account-id>.dkr.ecr.us-west-2.amazonaws.com
   ```

2. **Service Won't Start**:
   - Check CloudWatch logs for errors
   - Verify security groups allow traffic
   - Ensure task IAM role has necessary permissions

3. **ALB Health Checks Failing**:
   - Verify health check path is `/health`
   - Check security group rules
   - Review service logs for startup errors

### Debug Commands

```bash
# List all resources
python infra/status.py --detailed

# Force service update
aws ecs update-service \
  --cluster strands-weather-agent-cluster \
  --service weather-agent-service \
  --force-new-deployment

# View task definition
aws ecs describe-task-definition \
  --task-definition strands-weather-agent-task
```

## Security Considerations

### Current Setup (Demo)
- Public ALB with HTTP
- Basic security groups
- No authentication

### Production Recommendations
See "Making This Production-Ready" section in the main README for comprehensive security hardening steps including:
- HTTPS/TLS with ACM certificates
- API authentication (API keys, OAuth, Cognito)
- VPC endpoints for AWS services
- Secrets Manager integration
- WAF rules for the ALB

## Infrastructure Details

For detailed information about the infrastructure components and CloudFormation templates, see [infra/README.md](../infra/README.md).