# Agent ECS Template

A simple Python Flask application demonstrating AWS Bedrock integration in a client-server architecture. This template shows how to deploy AI-powered services to AWS ECS with proper IAM permissions for Bedrock access.

## Project Structure

- **client/**: Python Flask client that forwards requests to the server
- **server/**: Python Flask server that provides employee skills data  
- **infra/**: Infrastructure scripts and CloudFormation templates for AWS deployment

## Key Technologies

- Python 3.12.10 with Flask 3.1.0
- AWS Bedrock (Amazon Nova Lite model)
- Docker with linux/amd64 targeting
- AWS ECS Fargate
- boto3 for AWS service integration

## Prerequisites

- Docker installed and running
- AWS CLI configured with appropriate credentials
- AWS account with Bedrock access enabled
- [Rain CLI](https://github.com/aws-cloudformation/rain) (for CloudFormation deployment)

## Run Locally

### Quick Start with AWS Bedrock

**Important:** AWS credentials are required for AI features to work properly.

```bash
# Configure AWS Bedrock access (one-time setup)
./scripts/setup.sh

# Start services with AWS credentials
./scripts/start.sh

# Test all endpoints
./scripts/test.sh
```

### Available Scripts

All scripts are located in the `scripts/` directory:

- `setup.sh` - Initial AWS Bedrock configuration
- `start.sh` - Start services with AWS credentials
- `stop.sh` - Stop all services
- `test.sh` - Run comprehensive endpoint tests
- `test-quick.sh` - Run quick health check
- `logs.sh` - Show Docker Compose logs
- `clean.sh` - Clean up containers and cache files
- `rebuild.sh` - Rebuild containers from scratch

### Manual Start

If you prefer to start manually:
```bash
# Export AWS credentials first (required for Bedrock)
export $(aws configure export-credentials --format env-no-export)

# Then start Docker Compose
docker-compose up -d
```

### Test the Application

Run health checks:
```bash
# Quick health check
./scripts/test-quick.sh

# Comprehensive endpoint testing
./scripts/test.sh

# Or test manually
curl http://localhost:8080/health
curl http://localhost:8081/health
```

Test main functionality:
```bash
# Get all knowledge specialists
curl http://localhost:8080/employees

# Ask a specialist a question
curl -X POST http://localhost:8080/ask/1 \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'
```

## Container Details

- **Base Image**: python:3.12.10-slim (~150MB)
- **Client**: Port 8080, forwards requests to server
- **Server**: Port 8081, provides employee skills API
- **Health Checks**: Both services provide `/health` endpoints
- **Production**: Gunicorn with 4 workers, 2 threads each

## Environment Variables

- `SERVER_URL`: The URL of the server (used by the client)
  - Local: `http://localhost:8081`
  - ECS: `http://agent-server.agent-ecs:8081`

### AWS Bedrock Configuration

The server integrates with AWS Bedrock for AI-powered responses:

```bash
# Configure AWS Bedrock access (one-time setup)
./scripts/setup.sh
```

Environment variables (automatically configured in ECS):
- `BEDROCK_MODEL_ID`: Amazon Nova Lite model (`amazon.nova-lite-v1:0`)
- `BEDROCK_REGION`: AWS region for Bedrock (uses deployment region)
- `BEDROCK_MAX_TOKENS`: Maximum response tokens (500)
- `BEDROCK_TEMPERATURE`: Response randomness 0-1 (0.7)

## Deploy to AWS ECS

### Infrastructure Overview

The deployment uses two CloudFormation stacks:

1. **Base Stack** (`infra/base.cfn`): 
   - VPC with 2 private subnets
   - Application Load Balancer
   - ECS Cluster (agent-ecs-cluster)
   - IAM roles with Bedrock permissions
   - Security groups and networking

2. **Services Stack** (`infra/services.cfn`): 
   - ECS Task Definitions with Bedrock environment variables
   - ECS Services running on Fargate
   - Service Connect for internal communication
   - CloudWatch logging

### Step-by-Step Deployment

1. **Verify AWS Prerequisites**:
   ```bash
   # Check AWS configuration and Bedrock access
   ./infra/aws-checks.sh
   ```

2. **Setup ECR Repositories**:
   ```bash
   # Create ECR repositories: agent-ecs-client and agent-ecs-server
   ./infra/deploy.sh setup-ecr
   ```

3. **Build and Push Docker Images**:
   ```bash
   # Build images for linux/amd64 and push to ECR
   ./infra/deploy.sh build-push
   ```

4. **Deploy Infrastructure**:
   ```bash
   # Deploy both base and services stacks
   ./infra/deploy.sh all
   
   # This creates:
   # - agent-ecs-base stack (VPC, ALB, IAM roles)
   # - agent-ecs-services stack (ECS tasks and services)
   ```

5. **Verify Deployment**:
   ```bash
   # Test the deployed services
   ./infra/test_services.sh
   
   # Check infrastructure status
   ./infra/deploy.sh status
   ```

### Update After Code Changes

When you modify the application code:
```bash
# Rebuild and push new images
./infra/deploy.sh build-push

# Update the running services
./infra/deploy.sh update-services
```

### Helper Scripts

This project includes several helper scripts in the `infra/` directory:

#### `infra/setup-ecr.sh`
Automates ECR repository creation and Docker authentication:
- Creates ECR repositories for both server and client images
- Authenticates Docker with ECR (logs in for docker push)
- Sets up proper repository lifecycle policies
- Provides the ECR_REPO environment variable for builds
- **Important:** Run this script if you get "Your authorization token has expired" errors during docker push

#### `infra/build-push.sh`
Builds and pushes Docker images to ECR:
- Builds Python Flask Docker images for both server and client
- Tags and pushes images to ECR
- Handles authentication and error checking
- Detects expired authentication tokens and suggests running `setup-ecr.sh`
- **Common failures:** Most push failures are due to expired ECR authentication tokens

#### `infra/test_services.sh`
Tests the deployed services end-to-end:
- Retrieves the load balancer URL from CloudFormation
- Sends a test request to the Python application endpoint
- Validates that the services are responding correctly
- Provides immediate feedback on deployment success

#### `infra/deploy.sh`
Main deployment script with the following commands:
- `setup-ecr` - Setup ECR repositories and Docker authentication
- `build-push` - Build and push Docker images to ECR
- `all` - Deploy all infrastructure (base + services)
- `base` - Deploy only base infrastructure
- `services` - Deploy only services (requires base)
- `update-services` - Update services after code changes
- `status` - Show current deployment status
- `cleanup-services` - Remove services stack only
- `cleanup-base` - Remove base infrastructure
- `cleanup-all` - Remove all infrastructure
- `help` - Show help message

### Manual Deployment (Alternative)

If you prefer to run scripts individually:

1. **Setup ECR repositories:**
   ```bash
   ./infra/setup-ecr.sh
   ```

2. **Build and push images:**
   ```bash
   ./infra/build-push.sh
   ```

3. **Deploy infrastructure with Rain:**
   ```bash
   # Deploy base infrastructure
   rain deploy infra/base.cfn agent-ecs-base
   
   # Deploy services
   rain deploy infra/services.cfn agent-ecs-services --params BaseStackName=agent-ecs-base
   ```

### Accessing the Deployed Application

After deployment, get the load balancer URL:
```bash
# Get the load balancer URL
aws cloudformation describe-stacks \
    --stack-name agent-ecs-base \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
    --output text
```

Test the deployed application:
```bash
# Replace <LB_URL> with your actual load balancer URL

# Get all knowledge specialists
curl http://<LB_URL>/employees

# Ask a specialist a question
curl -X POST "http://<LB_URL>/ask/1" \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'
```

### Clean Up

To remove all AWS resources:
```bash
# Remove services first
./infra/deploy.sh cleanup-services

# Then remove base infrastructure
./infra/deploy.sh cleanup-all

# Delete ECR repositories (optional)
aws ecr delete-repository --repository-name agent-ecs-client --force
aws ecr delete-repository --repository-name agent-ecs-server --force
```

## API Endpoints

### Client (Port 8080)
- `GET /` - Service information
- `GET /health` - Health check with server connectivity
- `GET /employees` - Get all knowledge specialists
- `POST /ask/{employee_id}` - Ask a specific specialist a question

### Server (Port 8081)
- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/employees` - Get all knowledge specialists
- `POST /api/employee/{employee_id}/ask` - Ask a specific specialist a question using AWS Bedrock

## Troubleshooting

### Common Deployment Issues

1. **ECR Push Failures**:
   - Error: "Your authorization token has expired"
   - Solution: Run `./infra/setup-ecr.sh` to refresh authentication

2. **CloudFormation Stack Stuck**:
   - Check deployment status: `./infra/deploy.sh status`
   - View CloudWatch logs in AWS Console
   - Common cause: ECS services failing health checks

3. **Bedrock Access Denied**:
   - Ensure your AWS account has Bedrock access enabled
   - Check the region supports Amazon Nova Lite model
   - Verify IAM permissions in base.cfn include your model

4. **Services Not Responding**:
   - Check ECS service logs: `/ecs/agent-ecs-client` and `/ecs/agent-ecs-server`
   - Verify security groups allow traffic on ports 8080/8081
   - Ensure tasks have public IP assignment enabled

### Monitoring

- **CloudWatch Logs**: All container logs are in CloudWatch under `/ecs/agent-ecs-*`
- **ECS Console**: View task status, CPU/memory usage, and service events
- **Load Balancer**: Check target health in EC2 console under Target Groups

## Cost Estimates

Running this demo on AWS:
- **ECS Fargate**: ~$10-20/month (2 tasks, 0.25 vCPU, 0.5GB memory each)
- **Application Load Balancer**: ~$20/month
- **Amazon Bedrock**: ~$0.00015 per 1K tokens (very low for demo usage)
- **Total**: ~$30-45/month

## Further Reading

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [boto3 Bedrock Runtime](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)
- See `boto3-v3.md` for detailed architecture and implementation notes