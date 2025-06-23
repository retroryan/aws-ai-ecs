# Agent ECS Template - AWS Bedrock Integration Demo

## Overview

This is a **simple demonstration** project showing how to integrate AWS Bedrock using boto3 in a basic client-server architecture deployed to AWS ECS. It showcases the pattern: **Client → Server → AWS Bedrock Model**.

The application demonstrates a knowledge specialist system where users can ask domain experts questions, powered by AWS Bedrock's AI models.

**Purpose**: Educational demo showing basic AWS AI service integration - NOT production-ready code.

## Quick Start - Local Development

### Prerequisites
- Docker installed and running
- AWS CLI configured with appropriate credentials
- AWS account with Bedrock access enabled

### Running Locally

**Important:** AWS credentials are required for AI features to work properly.

```bash
# 1. Configure AWS Bedrock (one-time setup)
./scripts/setup.sh

# 2. Start services with AWS credentials
./scripts/start.sh

# 3. Test all endpoints
./scripts/test.sh

# 4. Stop services when done
./scripts/stop.sh
```

### Local Development Scripts

All local development scripts are in the `scripts/` directory:
- `setup.sh` - Configure AWS Bedrock for local development
- `start.sh` - Start services with AWS credentials
- `stop.sh` - Stop all services
- `test.sh` - Run comprehensive tests
- `logs.sh` - Show Docker Compose logs
- `clean.sh` - Clean up containers and cache files
- `rebuild.sh` - Rebuild containers from scratch

### Testing the API
```bash
# Get all knowledge specialists
curl http://localhost:8080/employees

# Ask a specialist a question
curl -X POST http://localhost:8080/ask/1 \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'
```

## Quick Start - AWS Development

### Prerequisites
- AWS CLI configured with appropriate credentials
- [Rain CLI](https://github.com/aws-cloudformation/rain) (for CloudFormation deployment)
- AWS account with Bedrock access enabled

### Deploy to AWS ECS
```bash
# 1. Verify AWS prerequisites
./infra/aws-checks.sh

# 2. Setup ECR repositories and push images
./infra/deploy.sh setup-ecr
./infra/deploy.sh build-push

# 3. Deploy all infrastructure
./infra/deploy.sh all

# 4. Check deployment status
./infra/deploy.sh status
```

### Testing the Deployed Application

You have two options for testing:

#### Option 1: Use the automated test script
```bash
./infra/test_services.sh
```

#### Option 2: Manual testing
```bash
# Get the load balancer URL
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name agent-ecs-base \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
    --output text)

# Test the endpoints
curl http://$LB_URL/health
curl http://$LB_URL/employees
curl -X POST http://$LB_URL/ask/1 \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'
```

### Update After Code Changes
```bash
# Rebuild and push new images
./infra/deploy.sh build-push

# Update the running services
./infra/deploy.sh update-services
```

## Script Organization

This project has two distinct script directories:

### Local Development Scripts (`scripts/`)
For running and testing the application locally with Docker:
- `setup.sh` - Configure AWS Bedrock for local development
- `start.sh` - Start services with AWS credentials
- `stop.sh` - Stop all services  
- `test.sh` - Run comprehensive tests against local endpoints
- `logs.sh` - Show Docker Compose logs
- `clean.sh` - Clean up containers and cache files
- `rebuild.sh` - Rebuild containers from scratch

### AWS Infrastructure Scripts (`infra/`)
For deploying and managing the application on AWS ECS:

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

#### `infra/aws-setup.sh`
Configures AWS Bedrock settings:
- Checks AWS CLI configuration and credentials
- Lists available Bedrock models in your region
- Creates a bedrock.env configuration file
- Used by `scripts/setup.sh` for local development

### AWS Infrastructure Scripts

All AWS deployment scripts are in the `infra/` directory:

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

## Architecture Overview

### System Architecture
```
User → Client (Flask:8080) → Server (Flask:8081) → AWS Bedrock (Nova Lite)
         ↓                      ↓
    AWS ALB               AWS Service Connect
```

### Key Technologies
- Python 3.12.10 with Flask 3.1.0
- AWS Bedrock (Amazon Nova Lite model)
- Docker with linux/amd64 targeting
- AWS ECS Fargate
- boto3 for AWS service integration
- Gunicorn production server

### AWS Bedrock Integration

The server uses **boto3** to integrate with AWS Bedrock for AI-powered responses:

1. **How it works**:
   - Server receives questions from the client
   - Uses boto3's `bedrock-runtime` client to invoke the AI model
   - Sends prompts with specialist context to Amazon Nova Lite
   - Returns AI-generated responses to the client

2. **Required IAM Permissions**:
   - `bedrock:InvokeModel` for the specific models:
     - `amazon.nova-lite-v1:0` (default)
     - `amazon.nova-pro-v1:0`
     - `anthropic.claude-3-5-haiku-*`
     - `anthropic.claude-3-5-sonnet-*`
   - These permissions are automatically configured in the ECS task role

### Project Structure
```
agent-ecs-template/
├── client/                 # Flask client application
│   ├── app.py             # Main client app
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Client container definition
├── server/                 # Flask server application
│   ├── app.py             # Main server app with specialists
│   ├── bedrock_service.py # AWS Bedrock integration
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Server container definition
├── infra/                  # Infrastructure as code
│   ├── base.cfn           # Base infrastructure
│   ├── services.cfn       # ECS services
│   └── *.sh               # Deployment scripts
└── scripts/               # Development scripts
    ├── setup.sh           # Initial AWS setup
    ├── start.sh           # Start local services
    ├── test.sh            # Run tests
    └── stop.sh            # Stop services
```

### API Endpoints

#### Client (Port 8080)
- `GET /` - Service information
- `GET /health` - Health check with server connectivity
- `GET /employees` - Get all knowledge specialists
- `POST /ask/{employee_id}` - Ask a specific specialist a question

#### Server (Port 8081)
- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/employees` - Get all knowledge specialists
- `POST /api/employee/{employee_id}/ask` - Ask a specific specialist a question using AWS Bedrock

### Knowledge Specialists
The demo includes 8 knowledge specialists in different fields:
1. **Dr. Sarah Chen** - Aerospace & Aviation
2. **Prof. Marcus Rodriguez** - Planetary Science
3. **Dr. Emily Thompson** - Forest Ecology
4. **Dr. James Wilson** - Agricultural Science
5. **Dr. Maria Garcia** - Marine Biology
6. **Prof. David Kim** - Wildlife Conservation
7. **Dr. Lisa Anderson** - Soil Science
8. **Dr. Robert Johnson** - Oceanography

## Local Development

### Development Scripts

All local development scripts are in the `scripts/` directory:

- **`setup.sh`** - Configure AWS Bedrock for local development
  - Runs `infra/aws-setup.sh` to check AWS credentials
  - Creates `bedrock.env` configuration file
  - Copies configuration to `server/.env`

- **`start.sh`** - Start services with AWS credentials
  - Exports AWS credentials for boto3
  - Starts Docker Compose services
  - Services run on localhost ports 8080/8081

- **`stop.sh`** - Stop all Docker services

- **`test.sh`** - Run comprehensive tests
  - Tests health endpoints
  - Tests API functionality
  - Validates specialist responses

- **`logs.sh`** - Show Docker Compose logs

- **`clean.sh`** - Clean up containers and cache files

- **`rebuild.sh`** - Force rebuild of Docker containers

### Environment Configuration

Local development requires AWS credentials for Bedrock access:
```bash
# Generated by setup.sh
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_REGION=us-east-1
BEDROCK_MAX_TOKENS=500
BEDROCK_TEMPERATURE=0.7
```

## AWS Setup and Configuration

### Infrastructure Overview

The deployment uses two CloudFormation stacks:

1. **Base Stack** (`infra/base.cfn`): 
   - VPC with 2 private subnets
   - Application Load Balancer
   - ECS Cluster (agent-ecs-cluster)
   - IAM roles with Bedrock permissions
   - Security groups and networking
   - Service Connect namespace

2. **Services Stack** (`infra/services.cfn`): 
   - ECS Task Definitions with Bedrock environment variables
   - ECS Services running on Fargate
   - Service Connect for internal communication
   - CloudWatch logging

### Naming Convention
All resources follow the `agent-ecs-*` naming pattern:
- **ECR Repositories**: `agent-ecs-client`, `agent-ecs-server`
- **ECS Cluster**: `agent-ecs-cluster`
- **CloudFormation Stacks**: `agent-ecs-base`, `agent-ecs-services`
- **Log Groups**: `/ecs/agent-ecs-client`, `/ecs/agent-ecs-server`

### IAM Permissions
The server task role includes permissions for:
- `amazon.nova-lite-v1:0` (default model)
- `amazon.nova-pro-v1:0`
- `anthropic.claude-3-5-haiku-*`
- `anthropic.claude-3-5-sonnet-*`

### Environment Variables

#### Local Development
- `SERVER_URL`: `http://localhost:8081`

#### AWS ECS
- `SERVER_URL`: `http://agent-server.agent-ecs:8081`
- `BEDROCK_REGION`: AWS region for Bedrock (uses deployment region)
- `BEDROCK_MODEL_ID`: `amazon.nova-lite-v1:0`
- `BEDROCK_MAX_TOKENS`: 500
- `BEDROCK_TEMPERATURE`: 0.7

### Container Details
- **Base Image**: python:3.12.10-slim (~150MB)
- **Client**: Port 8080, forwards requests to server
- **Server**: Port 8081, provides employee skills API
- **Health Checks**: Both services provide `/health` endpoints
- **Production**: Gunicorn with 4 workers, 2 threads each

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

### Viewing Logs

Local:
```bash
./scripts/logs.sh
```

AWS:
```bash
# View recent errors
./infra/deploy.sh status

# Check CloudWatch logs in AWS Console
# Log groups: /ecs/agent-ecs-client, /ecs/agent-ecs-server
```

### Monitoring
- **CloudWatch Logs**: All container logs are in CloudWatch under `/ecs/agent-ecs-*`
- **ECS Console**: View task status, CPU/memory usage, and service events
- **Load Balancer**: Check target health in EC2 console under Target Groups

## Clean Up

### Local Resources
```bash
# Stop and remove containers
./scripts/stop.sh

# Clean all resources including volumes
./scripts/clean.sh
```

### AWS Resources
```bash
# Remove services first
./infra/deploy.sh cleanup-services

# Then remove base infrastructure
./infra/deploy.sh cleanup-all

# Delete ECR repositories (optional)
aws ecr delete-repository --repository-name agent-ecs-client --force
aws ecr delete-repository --repository-name agent-ecs-server --force
```

## Important Notes

- **No Authentication**: Endpoints are publicly accessible
- **Basic Error Handling**: Minimal validation and error messages
- **For Demo Only**: Not suitable for production without hardening
- **Cost Monitoring**: Check AWS Console to monitor Bedrock API usage

## Next Steps

If you want to make this production-ready, consider:
1. Adding authentication (API keys or JWT)
2. Implementing proper logging and monitoring
3. Adding input validation and rate limiting
4. Setting up CI/CD pipeline
5. Adding unit and integration tests
6. Implementing caching for common questions
7. Adding HTTPS with proper certificates

## Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [boto3 Bedrock Runtime](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

**Status**: Ready for demo and learning purposes. This is a simple example showing the basic integration pattern - add security measures before any real-world use.