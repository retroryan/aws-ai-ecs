# Agriculture Agent ECS Deployment Guide

This guide provides comprehensive instructions for deploying the Agriculture Agent system to AWS ECS.

## Architecture Overview

The system consists of four containerized services:
- **agriculture-agent-main**: FastAPI application that orchestrates the agent
- **agriculture-agent-forecast**: MCP server for weather forecast data
- **agriculture-agent-historical**: MCP server for historical weather data
- **agriculture-agent-agricultural**: MCP server for agricultural conditions

## Prerequisites

1. **AWS Account** with the following services enabled:
   - Amazon ECS (Elastic Container Service)
   - Amazon ECR (Elastic Container Registry)
   - AWS Bedrock with model access
   - VPC with internet access

2. **Local Tools**:
   - AWS CLI configured with credentials
   - Docker installed and running
   - Rain CLI (for CloudFormation deployment)
   - Git for version control

3. **AWS Bedrock Access**:
   - Enable desired models in AWS Bedrock console
   - Ensure your IAM user/role has Bedrock invoke permissions

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd agriculture-agent-ecs

# 2. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 3. Deploy everything
./infra/deploy.sh all
```

## Detailed Deployment Steps

### 1. AWS Configuration Check

Verify your AWS setup:

```bash
./infra/deploy.sh aws-checks
```

This will:
- Check AWS credentials
- Verify Bedrock access
- List available models
- Confirm region settings

### 2. Create ECR Repositories

Set up container registries:

```bash
./infra/deploy.sh setup-ecr
```

This creates four ECR repositories:
- `agriculture-agent-main`
- `agriculture-agent-forecast`
- `agriculture-agent-historical`
- `agriculture-agent-agricultural`

### 3. Build and Push Images

Build Docker images and push to ECR:

```bash
./infra/deploy.sh build-push
```

This will:
- Build all Docker images for AMD64 architecture
- Tag with git commit hash and timestamp
- Push to ECR with both version tag and `latest`

### 4. Deploy Infrastructure

Deploy the base infrastructure:

```bash
./infra/deploy.sh base
```

This creates:
- VPC with public/private subnets
- ECS cluster with Container Insights
- Application Load Balancer
- Security groups and IAM roles
- Service discovery namespace

### 5. Deploy Services

Deploy the application services:

```bash
./infra/deploy.sh services
```

This deploys:
- Three MCP server services
- Main agent service with ALB integration
- Auto-scaling configuration

## Configuration Options

### Environment Variables

```bash
# Deployment environment (dev, staging, prod)
export ENVIRONMENT=dev

# AWS region for deployment
export AWS_REGION=us-east-1

# Bedrock model configuration
export BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
export BEDROCK_REGION=us-east-1
export BEDROCK_TEMPERATURE=0

# Logging level
export LOG_LEVEL=INFO
```

### Available Bedrock Models

- `amazon.nova-lite-v1:0` - Fast and cost-effective
- `amazon.nova-pro-v1:0` - Higher performance
- `anthropic.claude-3-5-sonnet-20240620-v1:0` - Best quality
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast Claude model
- `meta.llama3-70b-instruct-v1:0` - Open source option
- `cohere.command-r-plus-v1:0` - Optimized for RAG

### Deployment Examples

```bash
# Production deployment with Claude
ENVIRONMENT=prod \
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0 \
./infra/deploy.sh all

# Staging with Nova Pro
ENVIRONMENT=staging \
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0 \
./infra/deploy.sh all

# Update only services (after code changes)
./infra/deploy.sh update-services
```

## Stack Management

### Check Status

```bash
./infra/deploy.sh status
```

This shows:
- Stack deployment status
- Application URL
- Running services
- Health check status

### Access the Application

After deployment, the application URL will be displayed:

```
Application URL: http://agriculture-agent-dev-123456789.us-east-1.elb.amazonaws.com
```

Test endpoints:
```bash
# Health check
curl http://<alb-url>/health

# Submit query
curl -X POST http://<alb-url>/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Chicago?"}'
```

### Update Services

After code changes:

```bash
# 1. Build and push new images
./infra/deploy.sh build-push

# 2. Update services with new images
./infra/deploy.sh update-services
```

### Clean Up

Remove all resources:

```bash
# Remove everything (with confirmation)
./infra/deploy.sh cleanup-all

# Remove only services (keep base infrastructure)
./infra/deploy.sh cleanup-services
```

## Architecture Details

### Network Architecture

```
Internet → ALB (Public Subnets)
            ↓
    Main Agent Service (Private Subnets)
            ↓
    Service Discovery (agriculture.local)
       ↙    ↓    ↘
Forecast  Historical  Agricultural
(7071)    (7072)      (7073)
```

### Service Communication

- Main agent discovers MCP servers via private DNS
- Internal communication uses service discovery
- External access only through ALB on port 80

### Resource Allocation

| Service | CPU | Memory | Count |
|---------|-----|--------|--------|
| Main Agent | 512 | 1024 MB | 1-3 (auto-scaling) |
| Forecast | 256 | 512 MB | 1 |
| Historical | 256 | 512 MB | 1 |
| Agricultural | 256 | 512 MB | 1 |

## Monitoring and Logs

### View Logs

```bash
# View logs for a specific service
aws logs tail /ecs/agriculture-agent-main --follow

# View all MCP server logs
aws logs tail /ecs/agriculture-agent-forecast --follow
aws logs tail /ecs/agriculture-agent-historical --follow
aws logs tail /ecs/agriculture-agent-agricultural --follow
```

### CloudWatch Insights

Container Insights is enabled by default. Access via:
1. AWS Console → CloudWatch → Container Insights
2. Select your cluster: `agriculture-agent-{environment}`
3. View service metrics, logs, and performance data

## Troubleshooting

### Common Issues

1. **Model Access Denied**
   ```
   Solution: Enable the model in Bedrock console
   Check: ./infra/deploy.sh aws-checks
   ```

2. **Service Won't Start**
   ```
   Check logs: aws logs tail /ecs/agriculture-agent-main --follow
   Verify IAM permissions in CloudFormation outputs
   ```

3. **Cannot Connect to MCP Servers**
   ```
   Verify service discovery is working
   Check security group rules allow ports 7071-7073
   Ensure all services are running: ./infra/deploy.sh status
   ```

4. **Build Failures**
   ```
   Check Docker is running
   Verify ECR login: ./infra/deploy.sh setup-ecr
   Review build logs: build-*.log
   ```

### Debug Commands

```bash
# List running tasks
aws ecs list-tasks --cluster agriculture-agent-dev

# Describe a service
aws ecs describe-services \
  --cluster agriculture-agent-dev \
  --services agriculture-agent-main

# Check task definition
aws ecs describe-task-definition \
  --task-definition agriculture-agent-main
```

## Security Considerations

1. **Network Security**:
   - Services run in private subnets
   - Internet access via NAT Gateway
   - Security groups restrict access

2. **IAM Permissions**:
   - Minimal Bedrock permissions (InvokeModel only)
   - Separate execution and task roles
   - No hardcoded credentials

3. **Container Security**:
   - Non-root user execution
   - Read-only root filesystem capable
   - No privileged access

## Cost Optimization

1. **Fargate Spot** (optional):
   - Modify services.cfn to use FARGATE_SPOT
   - Can reduce costs by up to 70%

2. **Auto-scaling**:
   - Main service scales 1-3 instances
   - Based on CPU utilization (70%)
   - Scale-in cooldown: 5 minutes

3. **Model Selection**:
   - Nova Lite: Lowest cost
   - Claude Haiku: Good balance
   - Claude Sonnet: Best quality (higher cost)

## Next Steps

After deployment:

1. **Configure Monitoring**:
   - Set up CloudWatch alarms
   - Create custom dashboards
   - Enable X-Ray tracing (optional)

2. **Security Hardening**:
   - Add WAF rules to ALB
   - Enable VPC Flow Logs
   - Implement API authentication

3. **Performance Tuning**:
   - Adjust task CPU/memory
   - Optimize auto-scaling thresholds
   - Cache frequently used responses