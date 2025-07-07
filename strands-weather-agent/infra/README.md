# AWS Deployment Guide for Strands Weather Agent

This guide provides detailed information for deploying the Strands Weather Agent to AWS ECS using CloudFormation infrastructure.

## Infrastructure Overview

The deployment creates AWS infrastructure using CloudFormation templates:

### Base Infrastructure (`base.cfn`)
- **Networking**: VPC with 2 public subnets across availability zones
- **Load Balancing**: Application Load Balancer with health checks
- **ECS Cluster**: Fargate-based cluster with Container Insights
- **Service Discovery**: Private DNS namespace (weather.local)
- **Security**: Security groups and IAM roles with least-privilege

### Services Infrastructure (`services.cfn`)
- **ECS Services**: 4 services (1 agent + 3 MCP servers)
- **Task Definitions**: Resource limits and environment configuration
- **Service Connect**: Internal service mesh for communication
- **CloudWatch Logs**: Log groups with 7-day retention
- **Auto-scaling**: Optional scaling policies based on CPU/memory

## AWS Infrastructure Details

### 1. Networking
- VPC with public/private subnets across 2 AZs
- Internet Gateway for outbound connectivity
- Security groups for ALB and services

### 2. ECS Cluster
- Fargate launch type (serverless containers)
- Container Insights enabled
- Auto-scaling policies

### 3. Services
- 4 ECS services (agent + 3 MCP servers)
- Service discovery for internal communication
- Health checks for reliability

### 4. Load Balancing
- Application Load Balancer for external access
- Target group with health checks
- Auto-assigned DNS name

### 5. Storage
- ECR repositories for Docker images
- CloudWatch Log Groups for each service

### 6. Security
- IAM roles with least-privilege access
- No hardcoded credentials
- VPC isolation for services

## Deployment Script (deploy.py)

The `deploy.py` script provides a comprehensive deployment solution with the following features:

### Prerequisites
- Python 3.8+
- boto3 library (`pip install boto3`)
- AWS CLI configured with appropriate credentials
- AWS Account with Bedrock access enabled

### Configuration Files

1. **`.env`** - Local configuration (required)
   ```bash
   BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
   BEDROCK_REGION=us-east-1
   BEDROCK_TEMPERATURE=0
   LOG_LEVEL=INFO
   ```

2. **`cloud.env`** - Production configuration (optional, for telemetry)
   ```bash
   # Copy from .env.example and add:
   LANGFUSE_PUBLIC_KEY=your_public_key
   LANGFUSE_SECRET_KEY=your_secret_key
   LANGFUSE_HOST=https://us.cloud.langfuse.com
   TELEMETRY_TAGS=production,aws-strands
   ```

### Deployment Commands

#### Full Deployment
```bash
# Deploy everything with default settings
python3 infra/deploy.py all

# Deploy without telemetry
python3 infra/deploy.py all --disable-telemetry

# Deploy to specific region
python3 infra/deploy.py all --region us-west-2
```

#### Step-by-Step Deployment
```bash
# 1. Check AWS configuration and Bedrock access
python3 infra/deploy.py aws-checks

# 2. Setup ECR repositories
python3 infra/deploy.py setup-ecr

# 3. Build and push Docker images
python3 infra/deploy.py build-push

# 4. Deploy base infrastructure (VPC, ALB, ECS Cluster)
python3 infra/deploy.py base

# 5. Deploy services (ECS tasks and services)
python3 infra/deploy.py services
```

#### Monitoring and Updates
```bash
# Check deployment status
python3 infra/deploy.py status

# Update services after code changes (rebuilds images)
python3 infra/deploy.py update-services

# View CloudWatch logs (after deployment)
aws logs tail /aws/ecs/strands-weather-agent --follow
```

#### Cleanup
```bash
# Remove services only (keeps infrastructure)
python3 infra/deploy.py cleanup-services

# Remove base infrastructure
python3 infra/deploy.py cleanup-base

# Remove everything (prompts for confirmation)
python3 infra/deploy.py cleanup-all
```

## Testing the Deployment

After deployment, test your services:

```bash
# Run comprehensive service tests
python3 infra/test_services.py

# The test script will:
# - Check health endpoints
# - Test weather queries
# - Verify MCP server connectivity
# - Test multi-turn conversations
# - Display performance metrics
```

## Langfuse Telemetry Integration

The deployment supports optional Langfuse telemetry for observability:

1. **Setup**: Create `cloud.env` with Langfuse credentials
2. **Deploy**: The script automatically detects and configures telemetry
3. **Storage**: Credentials are securely stored in AWS Parameter Store
4. **Runtime**: Services retrieve credentials at startup

### Telemetry Features
- Token usage tracking
- Latency monitoring
- Session management
- Cost analysis
- Performance metrics

## Infrastructure Scripts Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy.py` | Main deployment script | `python3 deploy.py [command] [options]` |
| `build-push.sh` | Build and push Docker images | Called by deploy.py |
| `test_services.py` | Test deployed services | `python3 test_services.py` |
| `base.cfn` | Base infrastructure template | CloudFormation template |
| `services.cfn` | Services template | CloudFormation template |

## Environment Variables

### Required
- `BEDROCK_MODEL_ID`: AWS Bedrock model to use
- `BEDROCK_REGION`: AWS region for Bedrock (default: us-east-1)

### Optional
- `BEDROCK_TEMPERATURE`: Model temperature (default: 0)
- `LOG_LEVEL`: Logging level (default: INFO)
- `AWS_REGION`: AWS region for deployment (default: us-east-1)

### Telemetry (Optional, in cloud.env)
- `LANGFUSE_PUBLIC_KEY`: Langfuse public API key
- `LANGFUSE_SECRET_KEY`: Langfuse secret API key
- `LANGFUSE_HOST`: Langfuse API endpoint
- `TELEMETRY_TAGS`: Comma-separated tags for filtering

## Troubleshooting

### Common Issues

1. **Bedrock Access Denied**
   - Run `python3 infra/deploy.py aws-checks` to verify access
   - Enable the model in AWS Bedrock console
   - Check IAM permissions

2. **ECR Push Failures**
   - Ensure Docker is running
   - Check AWS credentials
   - Verify ECR repository exists

3. **Stack Creation Failures**
   - Check CloudFormation events for specific errors
   - Verify AWS quotas (VPCs, EIPs, etc.)
   - Ensure region supports all services

4. **Service Health Check Failures**
   - Check CloudWatch logs: `aws logs tail /aws/ecs/strands-weather-agent-main --follow`
   - Verify security group rules
   - Check task resource allocation

### Debug Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster strands-weather-agent --services strands-weather-agent-main

# List running tasks
aws ecs list-tasks --cluster strands-weather-agent

# Describe task for failure reasons
aws ecs describe-tasks --cluster strands-weather-agent --tasks <task-arn>

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn <arn>
```

## Best Practices

1. **Security**
   - Use `cloud.env` for production secrets
   - Rotate Langfuse API keys regularly
   - Review IAM roles and permissions
   - Enable VPC Flow Logs for monitoring

2. **Cost Optimization**
   - Monitor ECS task sizes and adjust as needed
   - Use CloudWatch metrics to right-size resources
   - Consider Fargate Spot for non-critical workloads
   - Set up billing alerts

3. **Reliability**
   - Test deployments in staging first
   - Use blue-green deployments for updates
   - Monitor CloudWatch alarms
   - Implement proper health checks

4. **Performance**
   - Adjust task CPU/memory based on load
   - Use CloudWatch Container Insights
   - Monitor ALB metrics
   - Consider caching strategies

## Rain CLI (Optional)

The deployment script supports the [Rain CLI](https://github.com/aws-cloudformation/rain) for enhanced CloudFormation deployments:

```bash
# Install Rain CLI
brew install rain

# The deploy.py script will automatically use Rain if available
# Rain provides better error messages and deployment progress
```

## Support

For issues or questions:
1. Check CloudWatch logs for detailed error messages
2. Review the troubleshooting section above
3. Verify all prerequisites are met
4. Check AWS service limits and quotas