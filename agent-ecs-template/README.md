# Python ECS Template

A simple Python Flask application demonstrating a client-server architecture designed to run on AWS ECS behind an Application Load Balancer. This template shows how to deploy a basic Python program to AWS ECR and ECS.

## Project Structure

- **client/**: Python Flask client that forwards requests to the server
- **server/**: Python Flask server that provides employee skills data  
- **infra/**: Infrastructure scripts and CloudFormation templates for AWS deployment

## Key Technologies

- Python 3.12.10
- Flask 3.1.0
- Docker with linux/amd64 targeting
- AWS ECS Fargate
- Gunicorn production server

## Prerequisites

- Docker (for local development and AWS deployment)
- AWS CLI configured with appropriate permissions
- [Rain CLI](https://github.com/aws-cloudformation/rain) (for AWS deployment)

## Run Locally

### Start the Applications

Run locally with Docker Compose:
```bash
docker-compose up --build
```

### Test the Application

Run health checks:
```bash
curl http://localhost:8080/health
curl http://localhost:8081/health
```

Test main functionality:
```bash
curl -X POST http://localhost:8080/inquire \
    -H "Content-Type: application/json" \
    -d '{"question": "Find employees with Python skills"}'
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
  - ECS: `http://python-server.python-agent-ecs-base:8081`

## Run on AWS

### Infrastructure Overview

The infrastructure is split into two CloudFormation stacks for faster, more flexible deployments:

1. **Base Stack** (`infra/base.cfn`): VPC, networking, security groups, IAM roles, load balancer (~10 min to deploy)
2. **Services Stack** (`infra/services.cfn`): ECS task definitions and services (~5 min to deploy/update)

This modular approach allows you to:
- Update services without touching base infrastructure (5 min vs 60+ min)
- Debug issues more easily with smaller, focused stacks
- Deploy and test components incrementally

**Note:** If deployment is taking an unusually long time, it's likely that the services deployment has failed. Check the deployment status using `./infra/deploy.sh status` and review the ECS service logs in the AWS Console for troubleshooting.

### Quick Deployment

The easiest way to deploy is using the orchestrated deployment script:

```bash
# 1. Setup ECR repositories
./infra/deploy.sh setup-ecr

# 2. Build and push Docker images
./infra/deploy.sh build-push

# 3. Deploy all infrastructure (base + services)
./infra/deploy.sh all

# 4. Check the deployment worked with 
./infra/test_services.sh 

# For subsequent deployments - just update services after code changes
./infra/deploy.sh update-services

# Check deployment status
./infra/deploy.sh status
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
   rain deploy infra/base.cfn python-agent-ecs-base
   
   # Deploy services
   rain deploy infra/services.cfn python-agent-ecs-services --params BaseStackName=python-agent-ecs-base
   ```

### Testing the Deployment

Once deployed, test with `curl` (replace YOUR_LB_HOST with your load balancer URL):
```bash
curl -X POST --location "http://YOUR_LB_HOST/inquire" \
    -H "Content-Type: application/json" \
    -d '{"question": "Find employees with Python skills"}'
```

## API Endpoints

### Client (Port 8080)
- `GET /` - Service information
- `GET /health` - Health check with server connectivity
- `POST /inquire` - Forward requests to server

### Server (Port 8081)
- `GET /` - Service information
- `GET /health` - Health check
- `POST /api/process` - Process employee skill queries
- `GET /api/employees` - Get all employees