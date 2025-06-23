# Agriculture Agent ECS - Weather & Agricultural Data Assistant

## Overview

This is a **production-ready demonstration** project showing how to build model-agnostic AI agent systems using LangGraph for orchestration, FastMCP for distributed tool servers, and AWS Bedrock for foundation models. It showcases a multi-service architecture pattern: **User → Agent → MCP Servers → Weather APIs**.

The application demonstrates a weather and agricultural data assistant that can answer questions about current conditions, forecasts, and crop recommendations, powered by AWS Bedrock's AI models through a clean, model-agnostic interface.

**Purpose**: Educational demo showing advanced AI agent architecture with distributed tools - production-ready patterns for real-world deployment.


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

## Quick Start - Local Development

### Prerequisites
- Docker installed and running
- AWS CLI configured with appropriate credentials
- AWS account with Bedrock access enabled
- Python 3.11+ (for local development without Docker)

### Running Locally

**Important:** AWS credentials are required for AI features to work properly.

You have two options for running the application locally:

#### Option 1: Direct Python Execution (Development/Debugging)

```bash
# 1. Configure AWS Bedrock (one-time setup)
./scripts/aws-setup.sh
cp bedrock.env .env

# 2. Start MCP servers in the background
./scripts/start_servers.sh

# 3. Run the main application
python main.py

# 4. Stop servers when done
./scripts/stop_servers.sh
```

#### Option 2: Docker Compose (Production-like Environment)

```bash
# 1. Configure AWS Bedrock (one-time setup)
./scripts/aws-setup.sh
cp bedrock.env .env

# 2. Start services with AWS credentials
./scripts/start.sh

# 3. Test all endpoints
./scripts/test_docker.sh

# 4. Stop services when done
./scripts/stop.sh
```

### Local Development Scripts

All local development scripts are in the `scripts/` directory:
- `aws-setup.sh` - Configure AWS Bedrock for local development
- `start.sh` - Start services with AWS credentials (Docker)
- `stop.sh` - Stop all Docker services
- `test_docker.sh` - Run comprehensive Docker tests
- `start_servers.sh` - Start MCP servers locally (non-Docker)
- `stop_servers.sh` - Stop local MCP servers
- `run_tests.sh` - Run the test suite

### Testing the API
```bash
# Check health
curl http://localhost:7075/health

# Ask about weather
curl -X POST http://localhost:7075/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What is the weather like in Chicago?"}'

# Get a forecast
curl -X POST http://localhost:7075/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Give me a 5-day forecast for Seattle"}'

# Agricultural query
curl -X POST http://localhost:7075/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Are conditions good for planting corn in Iowa?"}'
```

## Quick Start - AWS Development

### Prerequisites
- AWS CLI configured with appropriate credentials
- [Rain CLI](https://github.com/aws-cloudformation/rain) (for CloudFormation deployment)
- AWS account with Bedrock access enabled
- Docker installed (for building images)

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
    --stack-name agriculture-base \
    --query "Stacks[0].Outputs[?OutputKey=='LoadBalancerDNS'].OutputValue" \
    --output text)

# Test the endpoints
curl http://$LB_URL/health
curl -X POST http://$LB_URL/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What is the weather forecast for Chicago?"}'
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
For running and testing the application locally:
- `aws-setup.sh` - Configure AWS Bedrock for local development
- `start.sh` - Start Docker Compose services with AWS credentials
- `stop.sh` - Stop all Docker services
- `test_docker.sh` - Run comprehensive tests against Docker endpoints
- `start_servers.sh` - Start MCP servers locally (non-Docker)
- `stop_servers.sh` - Stop local MCP servers
- `run_tests.sh` - Run the full test suite

### AWS Infrastructure Scripts (`infra/`)
The AWS Infrastructure Scripts are in the `infra/` directory. See the [AWS Setup and Configuration](#aws-setup-and-configuration) section for detailed documentation of these scripts.

## Architecture Overview

### System Architecture
```
User → Weather Agent (FastAPI:7075) → LangGraph Agent → MCP Servers → Open-Meteo API
             ↓                              ↓
        AWS ALB                    Service Discovery
                                  (*.agriculture.local)
                                           ↓
                        ┌──────────┬───────────────┬──────────────┐
                        │ Forecast │  Historical   │ Agricultural │
                        │  Server  │    Server     │    Server    │
                        │  (7071)  │    (7072)     │    (7073)    │
                        └──────────┴───────────────┴──────────────┘
```

### Key Technologies
- Python 3.11+ with FastAPI and Uvicorn
- LangGraph 0.4.8 for agent orchestration
- FastMCP 0.2.5 for Model Context Protocol servers
- AWS Bedrock (supports all models with tool calling)
- Docker with linux/amd64 targeting
- AWS ECS Fargate with Service Discovery
- langchain-aws for Bedrock integration

### AWS Bedrock Integration

The agent uses **langchain-aws** to integrate with AWS Bedrock for AI-powered responses:

1. **How it works**:
   - Agent receives natural language queries
   - Uses `init_chat_model` for model-agnostic initialization
   - LangGraph orchestrates tool discovery and selection
   - MCP servers provide weather and agricultural data
   - Agent combines tool responses into natural language answers

2. **Model-Agnostic Design**:
   - Built with LangChain's `init_chat_model` for unified interface across LLM providers
   - AWS Bedrock Converse API ensures consistent tool calling across different models
   - Switch between models by changing a single environment variable (`BEDROCK_MODEL_ID`)
   - No code changes required when switching models

3. **Required IAM Permissions**:
   - `bedrock:InvokeModel` for the following models:
     - `amazon.nova-lite-v1:0` (default)
     - `amazon.nova-pro-v1:0`
     - `anthropic.claude-3-5-sonnet-*`
     - `anthropic.claude-3-haiku-*`
     - `meta.llama3-*` models
     - `cohere.command-r-*` models
   - These permissions are automatically configured in the ECS task role

### Project Structure
```
agriculture-agent-ecs/
├── main.py                 # FastAPI application entry
├── weather_agent/          # LangGraph agent implementation
│   ├── mcp_agent.py       # Main agent with MCP integration
│   ├── chatbot.py         # Interactive chat interface
│   └── query_classifier.py # Intent classification
├── mcp_servers/           # FastMCP server implementations
│   ├── forecast_server.py # Weather forecast tools
│   ├── historical_server.py # Historical weather tools
│   ├── agricultural_server.py # Agricultural data tools
│   └── api_utils.py       # Open-Meteo API utilities
├── models/                # Data models
│   ├── weather.py         # Weather-specific models
│   ├── responses.py       # Tool response models
│   └── queries.py         # Query classification
├── docker/                # Docker configurations
│   ├── Dockerfile.main    # Main agent container
│   ├── Dockerfile.forecast # Forecast server
│   ├── Dockerfile.historical # Historical server
│   └── Dockerfile.agricultural # Agricultural server
├── infra/                 # Infrastructure as code
│   ├── base.cfn          # Base infrastructure
│   ├── services.cfn      # ECS services
│   └── *.sh              # Deployment scripts
├── scripts/              # Development scripts
│   ├── aws-setup.sh      # Initial AWS setup
│   ├── start.sh          # Start Docker services
│   ├── test_docker.sh    # Run Docker tests
│   └── stop.sh           # Stop services
├── tests/                # Test suite
└── docker-compose.yml    # Local Docker orchestration
```

### API Endpoints

#### Weather Agent (Port 7075)
- `GET /` - Service information
- `GET /health` - Health check with MCP server connectivity
- `POST /query` - Submit natural language queries about weather or agriculture
- `GET /docs` - Interactive API documentation (FastAPI)

#### MCP Servers (Internal)
Each MCP server provides specialized tools discovered dynamically by the agent:

**Forecast Server (Port 7071)**
- `get_weather_forecast` - 5-day weather forecast for any location

**Historical Server (Port 7072)**
- `get_historical_weather` - Past 7 days of weather data

**Agricultural Server (Port 7073)**
- `get_agricultural_conditions` - Crop suitability analysis
- `get_frost_risk_assessment` - Frost risk for specific crops

### Supported Models
The system works with any AWS Bedrock model that supports tool/function calling:

1. **Amazon Nova Models** - Cost-effective, good performance
   - `amazon.nova-lite-v1:0` (default)
   - `amazon.nova-pro-v1:0`

2. **Claude Models** (Anthropic) - Best overall performance
   - `anthropic.claude-3-5-sonnet-20241022-v2:0`
   - `anthropic.claude-3-haiku-20240307-v1:0`
   - `anthropic.claude-3-opus-20240229-v1:0` (Most capable)

3. **Llama Models** (Meta) - Open source option
   - `meta.llama3-70b-instruct-v1:0`
   - `meta.llama3-1-70b-instruct-v1:0`

4. **Cohere Models** - Optimized for RAG and tool use
   - `cohere.command-r-plus-v1:0`
   - `cohere.command-r-v1:0`

5. **Mistral Models** - Alternative option
   - `mistral.mistral-large-2407-v1:0`

**Note:** Model availability varies by AWS region. Check the [AWS Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html) for model availability in your region.

## Local Development

### Development Scripts

All local development scripts are in the `scripts/` directory:

- **`aws-setup.sh`** - Configure AWS Bedrock for local development
  - Runs `infra/aws-setup.sh` to check AWS credentials
  - Lists available Bedrock models
  - Creates `bedrock.env` configuration file
  - Tests model access

- **`start.sh`** - Start services with AWS credentials
  - Exports AWS credentials for Docker
  - Starts Docker Compose services
  - Services run on localhost:7075

- **`stop.sh`** - Stop all Docker services

- **`test_docker.sh`** - Run comprehensive tests
  - Tests health endpoints
  - Tests query functionality
  - Validates MCP server connectivity

- **`start_servers.sh`** - Start MCP servers locally (non-Docker)
  - Runs servers in background
  - Creates PID files for management
  - Logs to `logs/` directory

- **`stop_servers.sh`** - Stop local MCP servers

- **`run_tests.sh`** - Run the test suite
  - Runs all unit and integration tests
  - Tests MCP servers, agent functionality, and coordinate handling
  - Optional `--with-docker` flag for Docker integration tests

### Environment Configuration

Local development requires AWS credentials for Bedrock access:
```bash
# Generated by aws-setup.sh
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_REGION=us-east-1
LOG_LEVEL=INFO

# Optional
BEDROCK_TEMPERATURE=0
```

### Docker Development

```bash
# Start with Docker Compose
./scripts/start.sh

# View logs
docker-compose logs -f

# Rebuild specific service
docker-compose up -d --build weather-agent

# Run tests
./scripts/test_docker.sh
```

### Testing Different Models

You can easily test different Bedrock models by changing the `BEDROCK_MODEL_ID` environment variable:

```bash
# Test with Claude 3.5 Sonnet
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
./scripts/start.sh

# Test with Claude 3 Haiku (faster, cheaper)
export BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
./scripts/start.sh

# Test with Amazon Nova Lite
export BEDROCK_MODEL_ID="amazon.nova-lite-v1:0"
./scripts/start.sh

# Test with Llama 3
export BEDROCK_MODEL_ID="meta.llama3-70b-instruct-v1:0"
./scripts/start.sh
```

**Note:** The application will exit with an error if `BEDROCK_MODEL_ID` is not set.

### Running Tests

The project includes a comprehensive test suite covering MCP servers, agent functionality, and coordinate handling:

```bash
# Run all tests (requires MCP servers to be started)
python tests/run_all_tests.py

# Or use the convenience script
./scripts/run_tests.sh

# Run with Docker integration tests (requires Docker running)
./scripts/run_tests.sh --with-docker

# Run individual test suites
python tests/test_mcp_servers.py      # Test MCP server functionality
python tests/test_mcp_agent.py        # Test agent and LangGraph integration
python tests/test_coordinates_consolidated.py  # Test coordinate handling
python tests/test_structured_output_demo.py    # Demo structured outputs
```

Test suite includes:
- **MCP Server Tests**: JSON response validation, error handling, data quality
- **Agent Tests**: Initialization, query processing, memory, structured outputs
- **Coordinate Tests**: Direct coordinates vs geocoding, performance comparison
- **Integration Tests**: End-to-end testing with all components running

## AWS Setup and Configuration

### Infrastructure Overview

The deployment uses two CloudFormation stacks:

1. **Base Stack** (`infra/base.cfn`): 
   - VPC with 2 public subnets
   - Application Load Balancer
   - ECS Cluster (agriculture-cluster)
   - IAM roles with Bedrock permissions
   - Security groups and networking
   - Service discovery namespace (agriculture.local)

2. **Services Stack** (`infra/services.cfn`): 
   - ECS Task Definitions with Bedrock environment variables
   - 4 ECS Services running on Fargate
   - Service Connect for internal communication
   - CloudWatch logging
   - Auto-scaling configuration

### Naming Convention
All resources follow the `agriculture-*` naming pattern:
- **ECR Repositories**: `agriculture-main`, `agriculture-forecast`, `agriculture-historical`, `agriculture-agricultural`
- **ECS Cluster**: `agriculture-cluster`
- **CloudFormation Stacks**: `agriculture-base`, `agriculture-services`
- **Log Groups**: `/ecs/agriculture-main`, `/ecs/agriculture-forecast`, etc.
- **Service Discovery**: `*.agriculture.local`

### IAM Permissions
The ECS task roles include permissions for:
- All supported Bedrock models (see Supported Models section)
- CloudWatch Logs for centralized logging
- X-Ray for distributed tracing (optional)

Required IAM policy for Bedrock access:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        }
    ]
}
```

### Environment Variables

#### Local Development (Docker)
- `MCP_SERVERS`: JSON configuration for MCP server endpoints
- `BEDROCK_MODEL_ID`: Selected AWS Bedrock model (required)
- `BEDROCK_REGION`: AWS region for Bedrock
- AWS credentials can be provided via:
  - Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
  - AWS CLI profiles (`aws configure`)
  - IAM roles (if running on EC2)

#### AWS ECS
- `MCP_SERVERS`: Service discovery URLs (e.g., `forecast-server.agriculture.local:7071`)
- `BEDROCK_MODEL_ID`: Configured during deployment
- `BEDROCK_REGION`: Uses deployment region
- IAM role provides AWS credentials automatically (no env vars needed)

### Container Details
- **Base Image**: python:3.11-slim
- **Weather Agent**: Port 7075, FastAPI with Uvicorn
- **MCP Servers**: Ports 7071-7073, FastMCP HTTP servers
- **Health Checks**: All services provide `/health` endpoints
- **Production**: Uvicorn with auto-reload disabled

### Infrastructure Scripts

#### `infra/deploy.sh`
Main deployment script with the following commands:
- `aws-checks` - Verify AWS configuration and Bedrock access
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
- Creates ECR repositories for all four service images
- Authenticates Docker with ECR (logs in for docker push)
- Sets up proper repository lifecycle policies
- Provides the ECR_REPO environment variable for builds
- **Important:** Run this script if you get "Your authorization token has expired" errors during docker push

#### `infra/build-push.sh`
Builds and pushes Docker images to ECR:
- Builds Docker images for all four services (agent + 3 MCP servers)
- Uses linux/amd64 architecture for ECS Fargate compatibility
- Tags and pushes images to ECR with versioning
- Handles authentication and error checking
- Detects expired authentication tokens and suggests running `setup-ecr.sh`
- **Common failures:** Most push failures are due to expired ECR authentication tokens

#### `infra/test_services.sh`
Tests the deployed services end-to-end:
- Retrieves the load balancer URL from CloudFormation
- Tests health endpoints for all services
- Sends test queries to the weather agent
- Validates that services are responding correctly
- Provides immediate feedback on deployment success

#### `infra/aws-setup.sh`
Configures AWS Bedrock settings:
- Checks AWS CLI configuration and credentials
- Lists available Bedrock models in your region
- Creates a bedrock.env configuration file
- Tests model access with actual invocation
- Used by `scripts/aws-setup.sh` for local development

#### `infra/status.sh`
Comprehensive infrastructure status checking:
- Shows CloudFormation stack status
- Displays ECS service health and task counts
- Performs health check calls
- Shows recent errors from CloudWatch logs
- Provides troubleshooting guidance

## Health Checking MCP Servers

### Overview
FastMCP servers using the `streamable-http` transport don't provide traditional HTTP health endpoints at the root path. Instead, they use the MCP protocol over HTTP, requiring specific JSON-RPC requests to verify server health.

**Important Notes:**
- The path must include a trailing slash (`/mcp/` not `/mcp`)
- The Accept header must include both `application/json` and `text/event-stream`
- A "Missing session ID" error response still indicates a healthy server

### Health Check Methods

#### 1. JSON-RPC Method (Recommended)
MCP servers respond to JSON-RPC requests at their configured path (typically `/mcp`). The most reliable health check uses the `mcp/list_tools` method:

```bash
# Check a single MCP server (note the trailing slash and Accept header)
curl -X POST http://localhost:7071/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'
```

A healthy server will respond with either:
- A list of available tools (if no session is required)
- An error about missing session (which still indicates the server is alive)

#### 2. Docker Compose Health Checks
The project's `docker-compose.yml` includes health checks for all MCP servers:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "-X", "POST", "http://localhost:7071/mcp", 
         "-H", "Content-Type: application/json", 
         "-d", '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}']
  interval: 30s
  timeout: 3s
  retries: 3
  start_period: 5s
```

#### 3. Automated Health Check Script
The `test_docker.sh` script includes a function to check MCP server health:

```bash
# Function from test_docker.sh
check_mcp_service() {
    local service=$1
    local url=$2
    
    response=$(curl -s -X POST "$url" \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}')
    
    # Check for valid response (tools list or session error)
    if echo "$response" | grep -q "session" || echo "$response" | grep -q "tools"; then
        echo "✓ $service is healthy"
    else
        echo "✗ $service is not responding"
    fi
}
```

### Health Check Examples

#### Local Development
```bash
# Check all MCP servers
for port in 7071 7072 7073; do
    echo "Checking server on port $port..."
    curl -s -X POST http://localhost:$port/mcp/ \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}' | jq .
done

# Check specific servers
# Forecast server
curl -X POST http://localhost:7071/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'

# Historical server  
curl -X POST http://localhost:7072/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'

# Agricultural server
curl -X POST http://localhost:7073/mcp/ \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'
```

#### AWS ECS Health Checks
In AWS ECS, health checks are configured in the task definitions and monitored by the load balancer:

```bash
# Check service health via AWS CLI
aws ecs describe-services \
    --cluster agriculture-cluster \
    --services agriculture-agent-forecast \
    --query 'services[0].healthCheckGracePeriodSeconds'

# View target health in load balancer
aws elbv2 describe-target-health \
    --target-group-arn <target-group-arn> \
    --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]'
```

### Understanding MCP Server Responses

#### Healthy Response Examples
1. **With tools list** (when session not required):
```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "get_weather_forecast",
        "description": "Get weather forecast data"
      }
    ]
  },
  "id": 1
}
```

2. **Session error** (still indicates healthy server):
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "No active session"
  },
  "id": 1
}
```

#### Unhealthy Indicators
- Connection refused (server not running)
- Timeout (server hanging)
- HTTP 404 (wrong path)
- Empty response
- Invalid JSON response

### Integration with Monitoring

#### Docker Health Status
```bash
# View health status of all containers
docker-compose ps

# Get detailed health info
docker inspect mcp-forecast-server | jq '.[0].State.Health'
```

#### Custom Health Check Implementation
For production deployments, consider implementing a dedicated health endpoint in your MCP servers:

```python
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

mcp = FastMCP("MyServer")

# Add custom health route
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")
```

### Troubleshooting Health Check Failures

1. **Connection Refused**
   - Server not started
   - Wrong port number
   - Container not running

2. **404 Not Found**
   - Wrong path (should be `/mcp`)
   - Server not configured for HTTP transport

3. **Timeout**
   - Server overloaded
   - Network issues
   - Container resource constraints

4. **Invalid Response**
   - Server error
   - Wrong protocol (not JSON-RPC)
   - Authentication issues

### Best Practices

1. **Use appropriate timeouts**: 3-5 seconds is usually sufficient
2. **Set reasonable intervals**: 30 seconds prevents overwhelming servers
3. **Configure retries**: 3 retries helps with transient failures
4. **Monitor logs**: Check server logs when health checks fail
5. **Use service discovery**: In ECS, use internal DNS names for health checks

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
   - Check the region supports your selected model
   - Run `./infra/aws-checks.sh` to verify setup
   - Try a different model (e.g., Amazon Nova Lite)

4. **Services Not Responding**:
   - Check ECS service logs: `/ecs/agriculture-*`
   - Verify security groups allow traffic on required ports
   - Ensure service discovery is working
   - Check ALB target health

### Viewing Logs

Local:
```bash
# Docker logs
docker-compose logs -f

# Local server logs
tail -f logs/forecast_server.log
tail -f logs/historical_server.log
tail -f logs/agricultural_server.log
```

AWS:
```bash
# View recent errors
./infra/status.sh

# Check CloudWatch logs in AWS Console
# Log groups: /ecs/agriculture-main, /ecs/agriculture-forecast, etc.
```

### Common Issues

1. **Model Not Available**:
   - Run `./infra/aws-setup.sh` to see available models
   - Enable the model in AWS Bedrock console
   - Switch to an available model via BEDROCK_MODEL_ID

2. **MCP Servers Not Connecting**:
   - Ensure all servers are running: `docker-compose ps`
   - Check server health: `curl http://localhost:7071/health`
   - Verify service discovery in ECS

3. **Slow Response Times**:
   - First request may be slow (cold start)
   - Consider using a faster model (e.g., Claude Haiku)
   - Check ECS task CPU/memory allocation

### Monitoring
- **CloudWatch Logs**: All container logs are in CloudWatch under `/ecs/agriculture-*`
- **ECS Console**: View task status, CPU/memory usage, and service events
- **Load Balancer**: Check target health in EC2 console under Target Groups
- **Service Map**: View service dependencies in AWS X-Ray (if enabled)

## Clean Up

### Local Resources
```bash
# Stop and remove containers
./scripts/stop.sh

# Clean all Docker resources
docker-compose down -v
```

### AWS Resources
```bash
# Remove services first
./infra/deploy.sh cleanup-services

# Then remove base infrastructure
./infra/deploy.sh cleanup-all

# Delete ECR repositories (optional)
./infra/cleanup-ecr-images.sh
# Or completely remove repositories:
./infra/setup-ecr.sh --delete
```

## Important Notes

- **No Authentication**: Endpoints are publicly accessible (add API keys for production)
- **Rate Limiting**: No rate limiting implemented (add for production)
- **For Demo Only**: Includes production patterns but needs security hardening
- **Cost Monitoring**: Check AWS Console to monitor Bedrock API usage
- **Model Selection**: Different models have different costs and performance characteristics

## Next Steps

To make this production-ready, consider:
1. Adding authentication (API keys, JWT, or AWS Cognito)
2. Implementing rate limiting and request throttling
3. Adding a caching layer for common queries
4. Setting up CI/CD pipeline with GitHub Actions
5. Adding comprehensive integration tests
6. Implementing request/response logging
7. Adding HTTPS with proper certificates
8. Setting up monitoring and alerting
9. Implementing graceful shutdown handling
10. Adding database for conversation history

## Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Open-Meteo API](https://open-meteo.com/)

---

**Status**: Production-ready architecture demonstration. This showcases advanced AI agent patterns with distributed tools - add security measures and authentication before real-world deployment.

## Working with AWS Credentials in Docker Containers

### The Challenge

When running AWS applications in Docker containers, a common issue is that containers cannot access AWS credentials configured on the host machine. This leads to errors like:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

This happens because Docker containers are isolated from the host's filesystem and environment, including the `~/.aws` directory where AWS credentials are typically stored.

### The Solution: AWS CLI Export-Credentials

The key to solving this issue is using the AWS CLI's `export-credentials` command, which automatically extracts and exports credentials as environment variables that can be passed to Docker containers.

#### The Magic Command

```bash
export $(aws configure export-credentials --format env-no-export 2>/dev/null)
```

This command:
- Extracts credentials from your current AWS CLI configuration
- Exports them as standard AWS environment variables:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_SESSION_TOKEN` (if using temporary credentials)
- Works with ALL authentication methods:
  - AWS CLI profiles
  - AWS SSO (Single Sign-On)
  - Temporary credentials from assume-role
  - IAM instance roles
  - MFA-enabled accounts

### Implementation in scripts/start.sh

The project's `scripts/start.sh` implements this solution elegantly:

```bash
#!/bin/bash
set -e

echo "Starting Agriculture Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Export AWS credentials if available
if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
    export $(aws configure export-credentials --format env-no-export 2>/dev/null)
    echo "✓ AWS credentials exported"
fi

# Set AWS_SESSION_TOKEN to empty if not set (to avoid docker-compose warning)
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}

# Start services
docker-compose up -d
```

Key features of this implementation:
1. **Automatic detection**: Checks if AWS CLI is installed and configured
2. **Silent operation**: Redirects errors to avoid cluttering output
3. **Session token handling**: Sets empty value to prevent Docker Compose warnings
4. **No manual configuration**: Users don't need to set any AWS environment variables

### Docker Compose Configuration

The credentials are then passed to containers via `docker-compose.yml`:

```yaml
services:
  weather-agent:
    environment:
      # AWS Credentials (automatically populated by start.sh)
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
```

### What to Avoid

1. **Don't use AWS profiles in Docker**: Containers can't access `~/.aws/config` or `~/.aws/credentials`
2. **Don't hardcode credentials**: Security risk and maintenance nightmare
3. **Don't use volume mounts for ~/.aws**: 
   - Doesn't work with SSO or temporary credentials
   - Creates security risks
   - Causes permission issues
4. **Don't forget AWS_SESSION_TOKEN**: Required for temporary credentials (SSO, assume-role)
5. **Don't use wildcards in IAM policies**: Be specific about which Bedrock models to allow

### Additional Docker Fixes Implemented

Beyond credential handling, several other Docker-related fixes were implemented:

#### 1. Port Configuration
- Changed Weather Agent API from port 8000 to 7075 to avoid conflicts
- Consistently applied across all configuration files

#### 2. Health Check Corrections
- MCP servers don't have `/health` endpoints
- Updated Docker health checks to use the MCP protocol:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "-X", "POST", "http://localhost:7071/mcp", 
           "-H", "Content-Type: application/json", 
           "-d", '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}']
  ```

#### 3. Service Dependencies
- Main service depends on all MCP servers being healthy
- Docker Compose ensures proper startup order

### Why This Solution Works

1. **Universal Compatibility**: Works with any AWS authentication method
2. **Zero Configuration**: Users don't need to modify their AWS setup
3. **Security**: Credentials are only passed at runtime, never stored
4. **Temporary Credentials**: Handles session tokens for SSO/role assumption
5. **Error Handling**: Gracefully handles missing credentials

### Testing the Implementation

To verify AWS credentials are working in Docker:

```bash
# Start services with automatic credential export
./scripts/start.sh

# Check for credential errors in logs
docker logs weather-agent-app | grep -i credential

# Test with an actual query
curl -X POST http://localhost:7075/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Chicago?"}'
```

### Key Takeaways

1. **Always use `aws configure export-credentials`** for passing AWS credentials to Docker
2. **Handle all three credential variables** (access key, secret key, session token)
3. **Test with different authentication methods** to ensure compatibility
4. **Implement proper health checks** that match your service's actual protocol
5. **Document the credential flow** so team members understand the authentication
