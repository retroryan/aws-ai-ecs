# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AWS Bedrock integration demo showcasing a client-server architecture deployed on AWS ECS. The application demonstrates a knowledge specialist system where users can ask domain experts questions, powered by AWS Bedrock's AI models (Amazon Nova Lite by default).

## Common Development Commands

### Local Development
```bash
# One-time setup for AWS Bedrock
./scripts/setup.sh

# Start services locally with AWS credentials
./scripts/start.sh

# Run comprehensive tests (health checks and API endpoints)
./scripts/test.sh

# Run integration tests with pytest (auto starts/stops services)
./scripts/run-tests.sh

# View logs
./scripts/logs.sh

# Stop services
./scripts/stop.sh

# Clean up containers and cache
./scripts/clean.sh

# Force rebuild containers
./scripts/rebuild.sh
```

### Testing Commands
```bash
# Run integration tests only (requires services running)
pytest tests/ -v --tb=short --timeout=60

# Test specific endpoint locally
curl http://localhost:8080/employees
curl -X POST http://localhost:8080/ask/1 \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'
```

### AWS Deployment
```bash
# Verify AWS prerequisites
./infra/aws-checks.sh

# Setup ECR and push images
./infra/deploy.sh setup-ecr
./infra/deploy.sh build-push

# Deploy all infrastructure (base + services)
./infra/deploy.sh all

# Update services after code changes
./infra/deploy.sh build-push
./infra/deploy.sh update-services

# Check deployment status
./infra/deploy.sh status

# Test deployed services
./infra/test_services.sh

# Cleanup
./infra/deploy.sh cleanup-services  # Services only
./infra/deploy.sh cleanup-all        # Everything
```

### Troubleshooting Common Issues
```bash
# ECR authentication expired during docker push
./infra/setup-ecr.sh

# View CloudWatch logs for debugging
aws logs tail /ecs/agent-ecs-client --follow
aws logs tail /ecs/agent-ecs-server --follow

# Get ALB URL for testing
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name agent-ecs-base \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
    --output text)
```

## High-Level Architecture

### System Flow
```
User → Client (Flask:8080) → Server (Flask:8081) → AWS Bedrock (Nova Lite)
         ↓                      ↓
    AWS ALB               AWS Service Connect
```

### Key Components

1. **Client Service** (`client/app.py`)
   - Flask web server on port 8080
   - Forwards requests to server via SERVER_URL environment variable
   - Endpoints:
     - `GET /health` - Health check with server connectivity validation
     - `GET /employees` - List all knowledge specialists
     - `POST /ask/{employee_id}` - Ask a specialist a question
   - Health check returns 503 if server is unreachable

2. **Server Service** (`server/app.py` + `server/bedrock_service.py`)
   - Flask API server on port 8081
   - Manages 8 knowledge specialists across different domains
   - Integrates with AWS Bedrock using boto3's converse API
   - Uses system prompts to provide specialist context
   - Endpoints:
     - `GET /api/employees` - Internal API for employee data
     - `POST /api/employee/{id}/ask` - Process questions with Bedrock

3. **AWS Infrastructure** (`infra/`)
   - **Base Stack** (`base.cfn`): VPC, subnets, ALB, ECS cluster, IAM roles
   - **Services Stack** (`services.cfn`): ECS task definitions and services
   - Service Connect enables internal service discovery
   - IAM task role includes bedrock:InvokeModel permissions

### Testing Architecture

The project includes comprehensive testing at multiple levels:

1. **Unit/Integration Tests** (`tests/`)
   - `test_integration.py`: Full API endpoint testing
   - `test_error_handling.py`: Error scenarios and edge cases
   - Uses pytest with fixtures for service startup
   - Tests cover health checks, employee endpoints, and ask functionality

2. **Local Testing Scripts** (`scripts/`)
   - `test.sh`: Manual endpoint testing with curl
   - `run-tests.sh`: Automated pytest execution with service lifecycle

### AWS Bedrock Integration

- Uses boto3 bedrock-runtime client with converse API
- Environment variables for configuration:
  - `BEDROCK_MODEL_ID` (default: amazon.nova-lite-v1:0)
  - `BEDROCK_REGION` (uses deployment region)
  - `BEDROCK_MAX_TOKENS` (default: 500)
  - `BEDROCK_TEMPERATURE` (default: 0.7)
- Supported models configured in IAM:
  - amazon.nova-lite-v1:0
  - amazon.nova-pro-v1:0
  - anthropic.claude-3-5-haiku-*
  - anthropic.claude-3-5-sonnet-*

### Service Discovery

- **Local Development**: Docker Compose network with service names
- **AWS ECS**: Service Connect namespace with DNS names
  - Client connects to server at: `http://agent-server.agent-ecs:8081`
  - Configured via SERVER_URL environment variable

### Container Configuration

- **Base Image**: python:3.12.10-slim
- **Production Server**: Gunicorn with 4 workers, 2 threads each
- **Resource Allocation**:
  - Client: 256 CPU / 1024 MB memory
  - Server: 256 CPU / 512 MB memory
- **Health Checks**: Application-level endpoints (not shell commands)

## Important Patterns and Conventions

### Error Handling
- Client service returns 503 when server is unreachable
- Server returns appropriate HTTP status codes (400, 404, 500)
- Bedrock errors are caught and return user-friendly messages

### Naming Conventions
- All AWS resources use `agent-ecs-*` prefix
- ECR repositories: `agent-ecs-client`, `agent-ecs-server`
- Log groups: `/ecs/agent-ecs-client`, `/ecs/agent-ecs-server`
- CloudFormation stacks: `agent-ecs-base`, `agent-ecs-services`

### Authentication and Security
- No authentication implemented (demo purposes only)
- Security groups restrict inter-service communication
- IAM roles follow least privilege for Bedrock access

### Deployment Best Practices
- Two-stack approach for faster iteration (base rarely changes)
- ECR authentication expires - run setup-ecr.sh when needed
- Always run aws-checks.sh before first deployment
- Use deploy.sh status to monitor deployment progress

### Development Workflow
1. Make code changes
2. Test locally with `./scripts/test.sh` or `./scripts/run-tests.sh`
3. Build and push: `./infra/deploy.sh build-push`
4. Update services: `./infra/deploy.sh update-services`
5. Verify with: `./infra/test_services.sh`

## Key Files to Understand

- `client/app.py`: Client service implementation (client/app.py:1-81)
- `server/app.py`: Server service with employee data (server/app.py:1-120)
- `server/bedrock_service.py`: Bedrock integration logic (server/bedrock_service.py:1-80)
- `infra/deploy.sh`: Master deployment orchestration script
- `tests/test_integration.py`: Comprehensive endpoint tests (tests/test_integration.py:1-141)
- `docker-compose.yml`: Local development configuration