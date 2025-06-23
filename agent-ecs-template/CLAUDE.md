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

# Run comprehensive tests
./scripts/test.sh

# Run integration tests (starts/stops services automatically)
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

### AWS Deployment
```bash
# Verify AWS prerequisites
./infra/aws-checks.sh

# Setup ECR and push images
./infra/deploy.sh setup-ecr
./infra/deploy.sh build-push

# Deploy all infrastructure
./infra/deploy.sh all

# Update services after code changes
./infra/deploy.sh build-push
./infra/deploy.sh update-services

# Check deployment status
./infra/deploy.sh status

# Test deployed services
./infra/test_services.sh

# Cleanup
./infra/deploy.sh cleanup-all
```

### Testing Endpoints
```bash
# Local testing
curl http://localhost:8080/employees
curl -X POST http://localhost:8080/ask/1 \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'

# AWS testing (get ALB URL first)
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name agent-ecs-base \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
    --output text)
curl http://$LB_URL/employees
```

## High-Level Architecture

### System Flow
```
User → Client (Flask:8080) → Server (Flask:8081) → AWS Bedrock (Nova Lite)
         ↓                      ↓
    AWS ALB               AWS Service Connect
```

### Key Components

1. **Client Service** (client/app.py)
   - Flask web server on port 8080
   - Forwards requests to server via SERVER_URL
   - Provides user-facing endpoints: /employees, /ask/{id}
   - Health check endpoint that validates server connectivity

2. **Server Service** (server/app.py + bedrock_service.py)
   - Flask API server on port 8081
   - Manages 8 knowledge specialists with different expertise
   - Integrates with AWS Bedrock using boto3
   - Constructs prompts with specialist context for AI responses

3. **AWS Infrastructure** (infra/)
   - **Base Stack**: VPC, subnets, ALB, ECS cluster, IAM roles
   - **Services Stack**: ECS task definitions and services
   - Service Connect enables internal service discovery
   - IAM roles grant Bedrock model invocation permissions

### Service Discovery
- Local: Services communicate via docker-compose network
- AWS: Service Connect provides DNS names (e.g., agent-server.agent-ecs:8081)

### AWS Bedrock Integration
- Uses boto3 bedrock-runtime client
- Supports multiple models (Nova Lite/Pro, Claude 3.5 variants)
- Configurable via environment variables:
  - BEDROCK_MODEL_ID (default: amazon.nova-lite-v1:0)
  - BEDROCK_REGION (uses deployment region)
  - BEDROCK_MAX_TOKENS (default: 500)
  - BEDROCK_TEMPERATURE (default: 0.7)

## Important Considerations

- AWS credentials required for Bedrock features
- ECR authentication expires - run setup-ecr.sh if push fails
- Health checks use application endpoints, not shell commands
- All resources follow agent-ecs-* naming convention
- No authentication on endpoints - demo only
- Gunicorn runs with 4 workers, 2 threads in production