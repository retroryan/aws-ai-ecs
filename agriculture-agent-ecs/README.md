# Agriculture Agent ECS - Weather & Agricultural Data Assistant

## Overview

This is a demonstration project showing how to build model-agnostic AI agent systems using LangGraph for orchestration, FastMCP for distributed tool servers, and AWS Bedrock for foundation models. It showcases a multi-service architecture pattern: **User → Agent → MCP Servers → Weather APIs**.

The application demonstrates a weather and agricultural data assistant that can answer questions about current conditions, forecasts, and crop recommendations, powered by AWS Bedrock's AI models through a clean, model-agnostic interface.


## Paradigm Shift: Agent-Driven Orchestration

This example demonstrates how to properly implement structured output in LangGraph Agents, revealing a **fundamental paradigm shift in AI development**: from manual orchestration to agent-driven orchestration.

### 🚀 The Paradigm Shift

**Traditional Development**: You write code to orchestrate between data extraction, API calls, and response formatting.

**AI Agent Revolution**: You declare the desired output structure, and the agent orchestrates everything internally.

Instead of manually parsing LLM output and calling APIs or tools yourself, you simply define the tools and the output format. The agent (powered by LangGraph and LangChain) automatically:
- Interprets the user query
- Selects and calls the appropriate tools
- Gathers and consolidates results
- Produces structured or natural language output as needed

### Core of the Program: Automated Agent Orchestration

The heart of this approach is:

```python
# Create React agent with discovered tools and checkpointer
self.agent = create_react_agent(
    self.llm.bind_tools(self.tools),
    self.tools,
    checkpointer=self.checkpointer
)
```

Everything else in the code is just setup: connecting to MCP servers, discovering tools, and configuring prompts. Once the agent is created, the entire workflow—from tool selection to response formatting—is fully automated by this core function. This enables rapid development, robust tool usage, and seamless structured output, all orchestrated by the agent itself.

## Quick Start

### Prerequisites

Before you begin, ensure you have:

✅ **AWS CLI** configured with credentials (`aws configure`)  
✅ **AWS Account** with Bedrock access enabled  
✅ **Python 3.11+** installed  
✅ **Docker** installed (for Docker option)  

### Local Development: Docker (FastAPI Web Server)

Run the full application stack with FastAPI web server:

```bash
# 1. Configure AWS Bedrock (one-time setup)
./scripts/aws-setup.sh

# 2. Start all services with Docker
./scripts/start_docker.sh

# 3. Test the application
./scripts/test_docker.sh
```

The FastAPI server is now running at http://localhost:7075 with:
- Health check endpoint: GET /health
- Query endpoint: POST /query
- API documentation: GET /docs

### Local Development: Direct Python Execution (Interactive Chatbot)

Run the weather agent chatbot directly for development and debugging:

```bash
# 1. Configure environment (from project root)
./scripts/aws-setup.sh
cp bedrock.env .env

# 2. Start MCP servers (from project root)
./scripts/start_servers.sh

# 3. Change to weather_agent directory
cd weather_agent

# 4. Set up Python environment (one-time setup)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 5. Run the weather agent chatbot
# Interactive mode (default)
python chatbot.py

# Demo mode with example queries
python chatbot.py --demo

# Multi-turn conversation demo
python chatbot.py --multi-turn-demo

# 6. Stop servers when done (from project root)
cd ..
./scripts/stop_servers.sh
```

**Available Options:**
- No parameters: Interactive chat mode - type your queries and get responses
- `--demo`: Runs pre-defined demo queries showcasing various capabilities
- `--multi-turn-demo`: Demonstrates multi-turn conversations with context retention

### AWS Deployment

Deploy the entire stack to AWS ECS:

```bash
# 1. Verify AWS prerequisites
./infra/aws-checks.sh

# 2. Deploy everything (ECR + infrastructure + services)
./infra/deploy.sh all

# 3. Test the deployment
./infra/test_services.sh
```

The deployment script will output the load balancer URL for accessing your application.

## Architecture

### System Design

The application follows a microservices architecture with clear separation of concerns:

```
User Request → Application Load Balancer → Weather Agent (FastAPI)
                                                    ↓
                                            LangGraph Agent
                                                    ↓
                                         MCP Service Discovery
                                    ┌───────────────┴────────────────┐
                                    ↓               ↓                ↓
                            Forecast Server  Historical Server  Agricultural Server
                              (Port 7071)      (Port 7072)        (Port 7073)
                                    ↓               ↓                ↓
                            Open-Meteo API   Open-Meteo API    Custom Logic
```

**Key Components:**
- **Weather Agent**: Main application handling user queries via FastAPI
- **LangGraph Agent**: Orchestrates tool selection and execution
- **MCP Servers**: Specialized tools for different data domains
- **Service Discovery**: ECS Service Connect for internal communication

### API Endpoints

#### Weather Agent (Port 7075)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service information and status |
| `/health` | GET | Health check with MCP connectivity |
| `/query` | POST | Submit natural language queries |
| `/docs` | GET | Interactive API documentation |

#### MCP Server Tools (Internal)
Each server provides specialized tools discovered dynamically:

- **Forecast Server**: `get_weather_forecast` - 5-day forecasts
- **Historical Server**: `get_historical_weather` - Past 7 days data  
- **Agricultural Server**: `get_agricultural_conditions`, `get_frost_risk_assessment`


### Working with AWS Credentials in Docker

Docker containers are isolated from your host's AWS credentials, which can cause authentication errors. This project solves this elegantly using AWS CLI's `export-credentials` command.

#### The Solution

The `scripts/start_docker.sh` script automatically exports your AWS credentials as environment variables:

```bash
# Export AWS credentials if available
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
    export $(aws configure export-credentials --format env-no-export 2>/dev/null)
    echo "✓ AWS credentials exported"
fi
```

This works with ALL authentication methods:
- AWS CLI profiles
- AWS SSO (Single Sign-On)
- Temporary credentials from assume-role
- IAM instance roles
- MFA-enabled accounts

#### Why This Works

1. **Universal Compatibility**: No special configuration needed
2. **Security**: Credentials only exist during runtime
3. **Automatic**: Users don't need to set environment variables
4. **Session Support**: Handles temporary credentials properly

### Testing

Run the comprehensive test suite:

```bash
# Run all tests
./scripts/run_tests.sh

# Run with Docker integration tests
./scripts/run_tests.sh --with-docker

# Run specific test modules
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v
python -m pytest tests/test_coordinates_consolidated.py -v
```

Test coverage includes:
- MCP server functionality and error handling
- Agent initialization and query processing
- Coordinate handling and geocoding
- Structured output transformation
- End-to-end integration tests

### Viewing Logs

#### Local Development
```bash
# Docker logs
docker-compose logs -f weather-agent
docker-compose logs -f forecast-server

# Python server logs (non-Docker)
tail -f logs/forecast_server.log
tail -f logs/historical_server.log
tail -f logs/agricultural_server.log
```

#### Debugging Tips
- First request may be slow (model cold start)
- Check MCP server connectivity in health endpoint
- Verify AWS credentials with `aws sts get-caller-identity`
- Use LOG_LEVEL=DEBUG for detailed logging

### Development Scripts Reference

All scripts in the `scripts/` directory:

| Script | Purpose |
|--------|---------|
| `aws-setup.sh` | Configure AWS Bedrock and create `.env` file |
| `start_docker.sh` | Start Docker Compose with AWS credentials |
| `stop_docker.sh` | Stop all Docker containers |
| `test_docker.sh` | Run comprehensive Docker tests |
| `start_servers.sh` | Start MCP servers locally (Python) |
| `stop_servers.sh` | Stop local MCP servers |
| `run_tests.sh` | Execute the full test suite |

## AWS Deployment Guide

### Infrastructure Overview

The deployment creates a production-ready infrastructure using AWS best practices:

#### Base Infrastructure (`infra/base.cfn`)
- VPC with 2 public subnets across availability zones
- Application Load Balancer with health checks
- ECS Cluster running on Fargate
- Service Discovery namespace (agriculture.local)
- IAM roles with least-privilege permissions

#### Services Infrastructure (`infra/services.cfn`)
- 4 ECS Services (1 agent + 3 MCP servers)
- Task definitions with resource limits
- Service Connect for internal networking
- CloudWatch log groups with retention
- Auto-scaling policies (optional)

### Deployment Process

#### Step 1: Initial Setup
```bash
# Verify AWS configuration
./infra/aws-checks.sh

# This checks:
# - AWS CLI installation
# - Valid credentials
# - Bedrock model access
# - Required permissions
```

#### Step 2: Deploy Infrastructure
```bash
# Option 1: Deploy everything at once
./infra/deploy.sh all

# Option 2: Deploy in stages
./infra/deploy.sh setup-ecr      # Create ECR repositories
./infra/deploy.sh build-push     # Build and push images
./infra/deploy.sh base           # Deploy base infrastructure
./infra/deploy.sh services       # Deploy ECS services
```

#### Step 3: Verify Deployment
```bash
# Run automated tests
./infra/test_services.sh

# Check status manually
./infra/deploy.sh status
```

#### Updating Deployments
After code changes:
```bash
# Rebuild and push new images
./infra/deploy.sh build-push

# Update running services
./infra/deploy.sh update-services
```

### Infrastructure Scripts Reference

All scripts in the `infra/` directory:

| Script | Purpose |
|--------|---------|
| `deploy.sh` | Main deployment orchestrator |
| `aws-checks.sh` | Verify AWS prerequisites |
| `setup-ecr.sh` | Create ECR repositories |
| `build-push.sh` | Build and push Docker images |
| `test_services.sh` | Test deployed services |
| `status.sh` | Detailed deployment status |
| `cleanup-ecr-images.sh` | Remove old ECR images |

### Monitoring & Operations

#### CloudWatch Logs
All services log to CloudWatch under `/ecs/agriculture-*`:
```bash
# View logs in AWS Console or CLI
aws logs tail /ecs/agriculture-main --follow
```

#### ECS Monitoring
- **Service Health**: ECS console shows task status
- **Resource Usage**: CPU/memory metrics in CloudWatch
- **Target Health**: ALB target group health checks

#### Cost Optimization
- Services run on Fargate Spot for cost savings
- Adjust task sizes based on actual usage
- Monitor Bedrock API calls for cost tracking

### Troubleshooting AWS Deployments

#### ECR Authentication Issues
```bash
# Error: "Your authorization token has expired"
./infra/setup-ecr.sh  # Refreshes authentication
```

#### Service Won't Start
```bash
# Check detailed status
./infra/status.sh

# Common causes:
# - Image not found (rebuild and push)
# - Health check failing (check logs)
# - Resource constraints (increase task size)
```

#### Bedrock Access Denied
```bash
# Verify model access
./infra/aws-checks.sh

# Enable model in Bedrock console
# Or switch to available model in services.cfn
```

## Configuration Reference

### Environment Variables

#### Local Development
```bash
# Required
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0

# Optional
BEDROCK_REGION=us-east-1
BEDROCK_TEMPERATURE=0
LOG_LEVEL=INFO

# AWS credentials (handled automatically by start.sh)
AWS_ACCESS_KEY_ID=<auto>
AWS_SECRET_ACCESS_KEY=<auto>
AWS_SESSION_TOKEN=<auto>
```

#### AWS ECS Configuration
Environment variables are set in `services.cfn`:
- `MCP_SERVERS`: Service discovery endpoints
- `BEDROCK_MODEL_ID`: Configured during deployment
- `BEDROCK_REGION`: Uses stack region
- IAM role provides credentials (no env vars)

### Supported AWS Bedrock Models

| Model | ID | Characteristics |
|-------|-----|-----------------|
| **Amazon Nova Lite** | `amazon.nova-lite-v1:0` | Fast, cost-effective, good for simple queries |
| **Amazon Nova Pro** | `amazon.nova-pro-v1:0` | Balanced performance and capability |
| **Claude 3.5 Sonnet** | `us.anthropic.claude-3-5-sonnet-20241022-v2:0` | Best overall performance |
| **Claude 3 Haiku** | `us.anthropic.claude-3-haiku-20240307-v1:0` | Fast and affordable |
| **Llama 3 70B** | `meta.llama3-70b-instruct-v1:0` | Open source option |
| **Cohere Command R+** | `cohere.command-r-plus-v1:0` | Optimized for tool use |

**Important Notes**: 
- Model availability varies by region. Check AWS Bedrock console for your region.
- **Claude models require the "us." prefix** (e.g., `us.anthropic.claude-3-5-sonnet-20241022-v2:0`) when using inference profiles for cross-region redundancy. This prefix is automatically added by the `aws-setup.sh` script.
- If you see errors about "on-demand throughput isn't supported", ensure your model ID includes the region prefix.

### MCP Server Configuration

#### Health Checking
MCP servers using FastMCP don't provide traditional REST health endpoints. Use JSON-RPC:

```bash
curl -X POST http://localhost:7071/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'
```

#### Custom Tool Development
Add new tools to existing servers:

```python
from fastmcp import FastMCP

weather_server = FastMCP("weather-server")

@weather_server.tool()
async def get_weather_alerts(location: str) -> dict:
    """Get weather alerts for a location."""
    # Implementation here
    return {"alerts": [...]}
```

## Advanced Topics

### Extending the System

#### Adding New MCP Servers
1. Create server file in `mcp_servers/`
2. Implement tools with FastMCP decorators
3. Add Docker configuration
4. Update `docker-compose.yml` and ECS configs

#### Modifying Agent Behavior
- Edit prompts in `mcp_agent.py`
- Add response transformations
- Implement custom tool selection logic
- Add memory or conversation features

### Production Considerations

Before deploying to production:

1. **Security**
   - Add API authentication (API Gateway, JWT)
   - Enable HTTPS with certificates
   - Implement rate limiting
   - Use VPC endpoints for AWS services

2. **Performance**
   - Add caching layer (Redis/DynamoDB)
   - Implement request queuing
   - Use connection pooling
   - Consider multi-region deployment

3. **Reliability**
   - Add circuit breakers
   - Implement retry logic
   - Set up monitoring alerts
   - Create runbooks

## Troubleshooting Guide

### Common Local Issues

#### Docker Won't Start
```bash
# Check Docker daemon
docker ps

# Reset Docker state
docker-compose down -v
./scripts/start_docker.sh
```

#### AWS Credentials Error
```bash
# Verify credentials
aws sts get-caller-identity

# Re-export credentials
./scripts/stop_docker.sh
./scripts/start_docker.sh
```

#### Port Conflicts
```bash
# Find process using port
lsof -i :7075

# Change port in docker-compose.yml
```

### Common AWS Issues

#### Stack Creation Failed
- Check CloudFormation events tab
- Verify IAM permissions
- Check region service availability

#### Services Unhealthy
- Review CloudWatch logs
- Check security group rules
- Verify service discovery

### Debugging Tools

```bash
# Local debugging
docker-compose logs weather-agent
docker exec -it weather-agent-app /bin/bash

# AWS debugging
aws ecs describe-services --cluster agriculture-cluster --services agriculture-main
aws logs tail /ecs/agriculture-main --follow
```

## Clean Up

### Local Resources
```bash
# Stop containers
./scripts/stop.sh

# Remove all Docker resources
docker-compose down -v --remove-orphans
docker system prune -a
```

### AWS Resources
```bash
# Remove in order (services before base)
./infra/deploy.sh cleanup-services
./infra/deploy.sh cleanup-base

# Optional: Remove ECR repositories
./infra/setup-ecr.sh --delete
```

## Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Open-Meteo API](https://open-meteo.com/)

## Example Queries

Try these queries to explore the system's capabilities:

**Weather Queries:**
- "What's the weather like in Chicago?"
- "Give me a 5-day forecast for Seattle"
- "What were the temperatures in New York last week?"

**Agricultural Queries:**
- "Are conditions good for planting corn in Iowa?"
- "What's the frost risk for tomatoes in Minnesota?"
- "Is it too wet to plant soybeans in Illinois?"

**Complex Queries:**
- "Compare this week's weather to last week in Denver"
- "Should I plant my garden this weekend in Portland?"
- "What crops are suitable for the current weather in Texas?"

## Next Steps

To make this production-ready:

1. **Add Authentication**: API keys, OAuth, or AWS Cognito
2. **Implement Rate Limiting**: Protect against abuse
3. **Add Caching**: Reduce API calls and improve response time
4. **Set Up CI/CD**: GitHub Actions for automated deployment
5. **Add Monitoring**: DataDog, New Relic, or CloudWatch dashboards
6. **Implement Logging**: Structured logs with correlation IDs
7. **Add HTTPS**: ACM certificates with Route 53
8. **Database Integration**: Store conversation history
9. **Error Handling**: Graceful degradation and fallbacks
10. **Documentation**: API docs, runbooks, and architecture diagrams