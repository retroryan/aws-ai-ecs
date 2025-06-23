# Agent ECS Template - AWS Bedrock Integration Demo

## Overview

This is a **simple demonstration** project showing how to integrate AWS Bedrock using boto3 in a basic client-server architecture deployed to AWS ECS. It showcases the pattern: **Client → Server → AWS Bedrock Model**.

**Purpose**: Educational demo showing basic AWS AI service integration - NOT production-ready code.

**Architecture**:
```
User → Client (Flask:8080) → Server (Flask:8081) → AWS Bedrock (Nova Lite)
         ↓                      ↓
    AWS ALB               AWS Service Connect
```

## What This Demo Shows

1. **Client-Server Architecture**: Flask-based microservices communicating via HTTP
2. **AWS Bedrock Integration**: Server uses boto3 to call AI models
3. **Docker Deployment**: Containerized services ready for AWS ECS
4. **Basic API Design**: RESTful endpoints for listing specialists and asking questions
5. **AWS ECS Deployment**: CloudFormation templates with proper IAM permissions

## Quick Start

### Prerequisites
- Docker installed
- AWS CLI configured with credentials
- AWS account with Bedrock access (specifically Amazon Nova Lite model)

### Local Development
```bash
# 1. Configure AWS Bedrock (one-time setup)
./scripts/setup.sh

# 2. Start services with AWS credentials
./scripts/start.sh

# 3. Test everything works
./scripts/test.sh

# 4. Stop services when done
./scripts/stop.sh
```

### Testing the API Locally
```bash
# Get all knowledge specialists
curl http://localhost:8080/employees

# Ask a specialist a question
curl -X POST http://localhost:8080/ask/1 \
    -H "Content-Type: application/json" \
    -d '{"question": "What are the main components of modern aircraft navigation systems?"}'
```

## AWS Deployment

### Deploy to AWS ECS
```bash
# 1. Setup ECR repositories and push images
./infra/deploy.sh setup-ecr
./infra/deploy.sh build-push

# 2. Deploy all infrastructure
./infra/deploy.sh all

# 3. Test the deployment
./infra/test_services.sh

# 4. Check deployment status
./infra/deploy.sh status
```

### Access the Deployed Application
After deployment, the script will output the load balancer URL. You can test it:

```bash
# Get the load balancer URL
LB_URL=$(aws cloudformation describe-stacks \
    --stack-name agent-ecs-base \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
    --output text)

# Test the deployed service
curl http://$LB_URL/employees
```

## Infrastructure Details

### Naming Convention
All resources follow the `agent-ecs-*` naming pattern:
- **ECR Repositories**: `agent-ecs-client`, `agent-ecs-server`
- **ECS Cluster**: `agent-ecs-cluster`
- **CloudFormation Stacks**: `agent-ecs-base`, `agent-ecs-services`
- **Log Groups**: `/ecs/agent-ecs-client`, `/ecs/agent-ecs-server`

### CloudFormation Templates

#### base.cfn
- VPC with 2 private subnets
- Application Load Balancer
- ECS Cluster
- IAM roles with Bedrock permissions
- Security groups
- Service Connect namespace

#### services.cfn
- ECS Task Definitions
- ECS Services (Fargate)
- Bedrock environment variables
- CloudWatch log groups

### IAM Permissions
The server task role includes permissions for:
- `amazon.nova-lite-v1:0` (default model)
- `amazon.nova-pro-v1:0`
- `anthropic.claude-3-5-haiku-*`
- `anthropic.claude-3-5-sonnet-*`

### Environment Variables
The server is configured with:
- `BEDROCK_REGION`: AWS region for Bedrock
- `BEDROCK_MODEL_ID`: `amazon.nova-lite-v1:0`
- `BEDROCK_MAX_TOKENS`: 500
- `BEDROCK_TEMPERATURE`: 0.7

## Project Structure

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

## API Endpoints

### Client (Port 8080)
- `GET /` - Service information
- `GET /health` - Health check
- `GET /employees` - List all knowledge specialists
- `POST /ask/{employee_id}` - Ask a specialist a question

### Server (Port 8081)
- `GET /` - Service information
- `GET /health` - Health check
- `GET /api/employees` - List all knowledge specialists
- `POST /api/employee/{employee_id}/ask` - Process question with Bedrock

## Knowledge Specialists

The demo includes 8 knowledge specialists in different fields:
1. **Dr. Sarah Chen** - Aerospace & Aviation
2. **Prof. Marcus Rodriguez** - Planetary Science
3. **Dr. Emily Thompson** - Forest Ecology
4. **Dr. James Wilson** - Agricultural Science
5. **Dr. Maria Garcia** - Marine Biology
6. **Prof. David Kim** - Wildlife Conservation
7. **Dr. Lisa Anderson** - Soil Science
8. **Dr. Robert Johnson** - Oceanography

## Testing

### Local Testing
```bash
# Run comprehensive tests
./scripts/test.sh

# Quick health check
./scripts/test-quick.sh

# View logs
./scripts/logs.sh
```

### AWS Testing
```bash
# Test deployed services
./infra/test_services.sh

# Check infrastructure status
./infra/deploy.sh status
```

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Ensure AWS CLI is configured: `aws configure`
   - Run `./scripts/setup.sh` to configure Bedrock
   - Start with `./scripts/start.sh` (not plain docker-compose)

2. **Model Not Found**
   - Check you have access to Amazon Nova Lite in your AWS account
   - Verify the region supports Bedrock
   - Update `BEDROCK_MODEL_ID` in server/.env if using different model

3. **Container Build Fails**
   - Ensure Docker is running
   - Check you're building for linux/amd64 platform

4. **ECS Deployment Fails**
   - Check AWS credentials and permissions
   - Ensure ECR repositories exist (`./infra/deploy.sh setup-ecr`)
   - Review CloudWatch logs for detailed errors

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
# Remove services only
./infra/deploy.sh cleanup-services

# Remove everything
./infra/deploy.sh cleanup-all
```

## Important Notes

- **No Authentication**: Endpoints are publicly accessible
- **Basic Error Handling**: Minimal validation and error messages
- **For Demo Only**: Not suitable for production without hardening
- **Cost Monitoring**: Check AWS Console to monitor Bedrock API usage

## Estimated Costs

- **Amazon Nova Lite**: ~$0.00015 per 1K input tokens
- **Typical demo usage**: <$5/month for Bedrock
- **ECS Fargate**: ~$10-20/month for minimal resources
- **Load Balancer**: ~$20/month

Total: ~$30-45/month for a running demo

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

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [boto3 Bedrock Client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)
- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

**Status**: Ready for demo and learning purposes. This is a simple example showing the basic integration pattern - add security measures before any real-world use.