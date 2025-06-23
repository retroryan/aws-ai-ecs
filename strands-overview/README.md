# AWS Strands + FastMCP Weather Agent Demo (Model-Agnostic with AWS Bedrock)

A production-ready demonstration of building model-agnostic AI agent systems using AWS Strands for orchestration and FastMCP for distributed tool servers. This project showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations using any AWS Bedrock foundation model.

## Overview

This project demonstrates a clean separation between application logic and model providers through AWS Strands' native integration. The system features:

- **True Model Agnosticism**: Switch between Claude, Llama, Cohere, and Amazon Nova models via environment variable
- **Zero Code Changes Required**: Model selection happens entirely through configuration
- **Production-Ready**: Docker containerized with AWS ECS deployment scripts
- **Distributed Architecture**: Multiple MCP servers for different data domains
- **Real Weather Data**: Integration with Open-Meteo API for live weather information (no API key required)
- **50% Less Code**: Compared to traditional orchestration frameworks

## Quick Start

### Option 1: Run Weather Agent Directly with Python

Run the weather agent chatbot directly from the command line. The multi-turn demo shows a complete conversation flow with weather queries, comparisons, historical data, and agricultural recommendations:

```bash
# Prerequisites: Python 3.12+, AWS account with Bedrock access

# 1. Configure environment
cp .env.example .env
# Edit .env and set BEDROCK_MODEL_ID

# 2. Start MCP servers (in background)
./scripts/start_servers.sh

# 3. Navigate to weather agent and set Python version
cd weather_agent
pyenv local 3.12.10  # or your Python 3.12+ version

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the weather agent
python main.py              # Interactive mode
python main.py --demo       # Demo mode with example queries
python main.py --structured # Show detailed tool calls
python main.py --multi-turn-demo # Full multi-turn conversation example

# 6. Stop servers when done (from project root)
cd ..
./scripts/stop_servers.sh
```

### Option 2: Run with Docker (Production-Ready)

```bash
# Prerequisites: Docker, AWS CLI configured with Bedrock access

# 1. Configure AWS Bedrock model (required)
cp .env.example .env
# Edit .env and set BEDROCK_MODEL_ID

# 2. Start all services with AWS credentials
./scripts/start.sh

# 3. Test the services
./scripts/test_docker.sh

# 4. Access the API at http://localhost:8090
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather like in Chicago?"}'

# 5. Stop services when done
./scripts/stop.sh
```

### Option 3: Run API Server Locally

```bash
# Prerequisites: Python 3.11+, AWS account with Bedrock access

# 1. Configure environment
cp .env.example .env
# Edit .env and set BEDROCK_MODEL_ID

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start MCP servers
./scripts/start_servers.sh

# 4. Run the API server
python api.py

# 5. Test the API
curl http://localhost:8090/health
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather like in Chicago?"}'

# 6. Stop servers when done
./scripts/stop_servers.sh
```

## Quick Start - AWS Deployment

```bash
# Prerequisites: AWS CLI configured, Docker installed

# 1. Navigate to infrastructure directory
cd infra

# 2. Deploy everything to AWS ECS
./deploy.sh all

# 3. Get the application URL
./deploy.sh status

# The deployment will:
# - Create ECR repositories
# - Build and push Docker images
# - Deploy VPC, ECS cluster, and ALB
# - Deploy all services with auto-scaling
```

## AWS Infrastructure Scripts Guide

The `infra/` directory contains scripts for deploying to AWS ECS:

### deploy.sh - Main Deployment Script
```bash
# View all available commands
./infra/deploy.sh help

# Deploy everything (recommended for first time)
./infra/deploy.sh all

# Deploy with specific model
BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0" ./infra/deploy.sh all

# Deploy to production environment
ENVIRONMENT=prod ./infra/deploy.sh all

# Individual deployment steps
./infra/deploy.sh setup-ecr    # Create ECR repositories
./infra/deploy.sh build        # Build Docker images
./infra/deploy.sh push         # Push images to ECR
./infra/deploy.sh deploy-base  # Deploy VPC, ECS cluster, ALB
./infra/deploy.sh deploy-services  # Deploy application services
./infra/deploy.sh status       # Check deployment status
./infra/deploy.sh cleanup      # Remove all resources
```

### Key Infrastructure Features
- **Auto-scaling**: Main service scales based on CPU/memory utilization
- **Service Discovery**: Internal DNS for MCP server communication
- **Load Balancing**: ALB distributes traffic to healthy containers
- **Health Checks**: All services monitored with health endpoints
- **CloudWatch Logs**: Centralized logging for all services
- **IAM Roles**: Secure access to AWS Bedrock without API keys

## Available Scripts

### Docker Scripts (Recommended)
- **`./scripts/start.sh`**: Start all services with Docker Compose
  - Automatically exports AWS credentials from AWS CLI
  - Supports all AWS authentication methods (profiles, SSO, IAM roles)
  - Shows current AWS identity being used
  
- **`./scripts/test_docker.sh`**: Test running Docker services
  - Checks health of all MCP servers and Weather Agent
  - Runs sample queries to verify functionality
  - Shows service URLs and endpoints
  
- **`./scripts/stop.sh`**: Stop all Docker services

### Local Development Scripts
- **`./scripts/start_servers.sh`**: Start MCP servers locally
- **`./scripts/stop_servers.sh`**: Stop local MCP servers
- **`./scripts/aws-setup.sh`**: Configure AWS Bedrock access

### Testing the System

The test script performs comprehensive checks:

1. **Service Health Checks**:
   - MCP servers respond to JSON-RPC requests
   - Weather Agent API health endpoint
   
2. **Sample Queries**:
   - Weather forecast: "What's the weather forecast for Chicago?"
   - Historical data: "How much rain did Seattle get last week?"
   - Agricultural: "Are conditions good for planting corn in Iowa?"

3. **Expected Output**:
   ```
   ✓ All services are healthy!
   ✓ Query responses show actual weather data
   ⚠ AWS credentials warning is normal without configuration
   ```

### MCP Server Health Checks

FastMCP servers require special handling for health checks:

1. **MCP Protocol**: The standard `/mcp/` endpoint requires session management and uses Server-Sent Events (SSE), making it unsuitable for simple health checks.

2. **Custom Health Endpoints**: Each MCP server implements a `/health` endpoint:
   ```python
   @server.custom_route("/health", methods=["GET"])
   async def health_check(request: Request) -> JSONResponse:
       return JSONResponse({"status": "healthy", "service": "forecast-server"})
   ```

3. **Docker Configuration**: Health checks in docker-compose.yml:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
     interval: 30s
     timeout: 3s
     retries: 3
     start_period: 5s
   ```

4. **Testing MCP Functionality**: To test MCP endpoints directly:
   ```bash
   curl -X POST http://localhost:8081/mcp/ \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'
   ```

## Troubleshooting

### AWS Credentials in Docker
If you see "Unable to locate credentials" errors:
1. Ensure AWS CLI is configured: `aws sts get-caller-identity`
2. Use the start script which exports credentials: `./scripts/start.sh`
3. The script handles all authentication methods (profiles, SSO, IAM roles)

### Port Conflicts
If ports are already in use:
- Weather Agent API: 8090 (change in docker-compose.yml)
- MCP Servers: 8081-8083 (change in respective Dockerfiles)

### Service Health Issues
If services fail health checks:
1. Check logs: `docker compose logs -f <service-name>`
2. Verify MCP servers are responding: `./scripts/test_docker.sh`
3. Ensure all containers are running: `docker ps`

## Architecture Overview

### System Architecture

The system consists of multiple containerized services working together:

```
┌─────────────────┐     ┌──────────────────────────────────────┐
│   User Request  │────▶│         Application Load          │
└─────────────────┘     │          Balancer (ALB)            │
                        └────────────────┬─────────────────────┘
                                        │
                        ┌───────────────▼─────────────────┐
                        │    Weather Agent Service        │
                        │  (LangGraph + AWS Bedrock)      │
                        └───────┬────────┬────────┬───────┘
                                │        │        │
                   Service Discovery (Internal DNS: *.agriculture.local)
                                │        │        │
                 ┌──────────────▼──┐ ┌──▼───────┐ ┌──▼──────────────┐
                 │ Forecast Server │ │Historical│ │  Agricultural   │
                 │   (Port 8081)   │ │  Server  │ │     Server      │
                 └─────────────────┘ │(Port 8082)│ │  (Port 8083)    │
                                    └──────────┘ └─────────────────┘
```

### Component Details

1. **FastMCP Servers** (Distributed Tool Servers):
   - **Forecast Server**: 5-day weather forecasts via Open-Meteo API
   - **Historical Server**: Past weather data and trends
   - **Agricultural Server**: Crop recommendations and frost risk analysis

2. **Model-Agnostic LangGraph Agent**:
   - Uses `init_chat_model` for seamless model switching
   - React agent pattern with tool selection capabilities
   - Maintains conversation memory across interactions
   - Optionally transforms responses to structured Pydantic models

3. **FastAPI Application**:
   - RESTful API for query submission
   - Health monitoring endpoints
   - Structured request/response models

### Data Flow

1. User submits natural language query via REST API
2. LangGraph agent analyzes intent and determines required tools
3. Agent discovers available tools from MCP servers via HTTP
4. Agent executes tools with appropriate parameters
5. Raw responses transformed and combined into natural language answer

## AWS Setup and Configuration

### Prerequisites

1. **AWS Account Setup**:
   - Create an AWS account if you don't have one
   - Configure AWS CLI: `aws configure`
   - Ensure your IAM user/role has appropriate permissions

2. **Enable AWS Bedrock**:
   - Navigate to AWS Console → Bedrock → Model access
   - Request access to desired models (instant for most models)
   - Wait for access approval (usually immediate)

3. **Required IAM Permissions**:
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

### Environment Configuration

Configure the system via environment variables in `.env`:

```env
# Required - AWS Bedrock Model
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0  # or any supported model
BEDROCK_REGION=us-east-1

# Optional
BEDROCK_TEMPERATURE=0
LOG_LEVEL=INFO

# AWS Credentials (if not using IAM role)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### Supported AWS Bedrock Models

The system works with any Bedrock model that supports tool/function calling:

#### Claude Models (Anthropic)
- `anthropic.claude-3-5-sonnet-20240620-v1:0` - Best overall performance ⭐
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast and cost-effective
- `anthropic.claude-3-opus-20240229-v1:0` - Most capable

#### Amazon Nova Models
- `amazon.nova-pro-v1:0` - High performance
- `amazon.nova-lite-v1:0` - Cost-effective, good for demos ⭐

#### Meta Llama Models
- `meta.llama3-70b-instruct-v1:0` - Open source, excellent performance
- `meta.llama3-1-70b-instruct-v1:0` - Latest Llama 3.1
- `meta.llama3-1-8b-instruct-v1:0` - Smaller, faster option

#### Cohere Models
- `cohere.command-r-plus-v1:0` - Optimized for RAG and tool use
- `cohere.command-r-v1:0` - Efficient alternative

### Model Selection

Simply change the `BEDROCK_MODEL_ID` environment variable:

```bash
# For best performance
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20240620-v1:0"

# For cost-effective operation
export BEDROCK_MODEL_ID="amazon.nova-lite-v1:0"

# For open source
export BEDROCK_MODEL_ID="meta.llama3-70b-instruct-v1:0"
```

### AWS Infrastructure Details

The CloudFormation templates create:

1. **Networking**:
   - VPC with public/private subnets across 2 AZs
   - Internet Gateway and NAT Gateways
   - Security groups for ALB and services

2. **ECS Cluster**:
   - Fargate launch type (serverless containers)
   - Container Insights enabled
   - Auto-scaling policies

3. **Services**:
   - 4 ECS services (agent + 3 MCP servers)
   - Service discovery for internal communication
   - Health checks for reliability

4. **Load Balancing**:
   - Application Load Balancer for external access
   - Target group with health checks
   - Auto-assigned DNS name

5. **Storage**:
   - ECR repositories for Docker images
   - CloudWatch Log Groups for each service

6. **Security**:
   - IAM roles with least-privilege access
   - No hardcoded credentials
   - VPC isolation for services

## Usage Examples

### API Usage

```python
import requests

# Submit a weather query
response = requests.post("http://localhost:8090/query", 
    json={"query": "What's the weather like in Chicago?"})
print(response.json())

# Example queries:
# - "Give me a 5-day forecast for Seattle"
# - "What were the temperatures in New York last week?"
# - "Are conditions good for planting corn in Iowa?"
# - "What's the frost risk for tomatoes in Minnesota?"
```

### Programmatic Usage

```python
from weather_agent.mcp_agent import MCPWeatherAgent

# Initialize agent
agent = MCPWeatherAgent()
await agent.initialize()

# Get text response
response = await agent.query("What's the weather forecast for Iowa?")
print(response)

# Get structured response
structured = await agent.query_structured(
    "What's the weather forecast for Iowa?", 
    response_format="forecast"
)
print(f"Location: {structured.location}")
print(f"Current temp: {structured.current_conditions.temperature}°C")
```

## Docker Deployment

### Quick Start with Docker

```bash
# 1. Clone the repository
git clone <repository-url>
cd agriculture-agent-ecs

# 2. Set up environment
cp .env.docker .env
# Edit .env with your AWS Bedrock configuration

# 3. Build and run with Docker Compose
docker-compose up -d

# 4. Verify all services are healthy
./scripts/test_docker.sh

# 5. Access the application
curl http://localhost:8090/health
```

### Docker Architecture

The application is containerized with the following services:

- **forecast-server**: Weather forecast MCP server (port 8081)
- **historical-server**: Historical weather MCP server (port 8082)  
- **agricultural-server**: Agricultural conditions MCP server (port 8083)
- **weather-agent**: Main agent application (port 8090)

All services communicate over an internal Docker network.

### Docker Commands

```bash
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and restart a specific service
docker-compose up -d --build weather-agent

# Run automated tests
python tests/docker_test.py
```

### Docker Environment Variables

Configure in `.env` file:

```env
# Required
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
BEDROCK_REGION=us-east-1

# AWS Credentials (if not using IAM role)
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret

# Optional
BEDROCK_TEMPERATURE=0
LOG_LEVEL=INFO
```

## Development

### Project Structure

```
.
├── main.py                  # FastAPI application entry
├── weather_agent/           # LangGraph agent implementation
│   ├── mcp_agent.py        # Main agent logic
│   └── query_classifier.py  # Query intent classification
├── mcp_servers/            # FastMCP server implementations
│   ├── forecast_server.py   # Weather forecast tools
│   ├── historical_server.py # Historical weather tools
│   ├── agricultural_server.py # Agricultural data tools
│   └── api_utils.py        # Common API utilities
├── models/                 # Data models
├── docker/                 # Docker configuration files
│   ├── Dockerfile.base     # Base image
│   ├── Dockerfile.agent    # Agent application
│   └── Dockerfile.*        # MCP server images
├── scripts/                # Operational scripts
│   ├── start_servers.sh    # Start MCP servers
│   ├── stop_servers.sh     # Stop MCP servers
│   ├── test_docker.sh      # Docker integration test
│   └── aws-setup.sh        # AWS Bedrock setup helper
├── tests/                  # Test suite
│   └── docker_test.py      # Docker integration tests
├── infra/                  # AWS infrastructure code
├── logs/                   # Server logs and PIDs
└── docker-compose.yml      # Docker Compose configuration
```

### Running Tests

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test suites
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v

# Test structured output functionality
python tests/test_structured_output_demo.py
```

### Server Management

```bash
# Start all MCP servers
./scripts/start_servers.sh

# Check server status
ps aux | grep python | grep server

# View server logs
tail -f logs/forecast_server.log
tail -f logs/historical_server.log
tail -f logs/agricultural_server.log

# Stop all servers
./scripts/stop_servers.sh
```

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required - AWS Bedrock Model
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0  # or any supported model
BEDROCK_REGION=us-east-1

# Optional
BEDROCK_TEMPERATURE=0
LOG_LEVEL=INFO

# AWS Credentials (if not using IAM role)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### AWS Setup

1. **Enable Bedrock Access**: Go to AWS Console → Bedrock → Model access
2. **Set IAM Permissions**: Ensure your user/role has:
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

### MCP Server Ports

Default ports (configurable in server files):
- Forecast Server: 8081
- Historical Server: 8082
- Agricultural Server: 8083

## Extending the System

### Adding New MCP Tools

1. Create a new tool in an existing server:

```python
@weather_server.tool()
async def get_uv_index(location: str) -> dict:
    """Get UV index for a location"""
    # Implementation here
    return {"location": location, "uv_index": 5}
```

2. Or create a new MCP server:

```python
from fastmcp import FastMCP

alert_server = FastMCP("Weather Alerts")

@alert_server.tool()
async def get_weather_alerts(location: str) -> dict:
    """Get weather alerts for a location"""
    # Implementation here
    return {"alerts": []}

# Add to scripts/start_servers.sh
```

### Customizing the Agent

Modify `weather_agent/mcp_agent.py` to:
- Change agent prompts
- Add new response formats
- Implement custom tool selection logic
- Add new structured output models

## AWS ECS Deployment

### Quick Deploy

```bash
# Build and push Docker image
./infra/build_and_push.sh

# Deploy to ECS
./infra/deploy.sh
```

### CloudFormation Configuration

The stack accepts these parameters:
- `BedrockModelId`: Which Bedrock model to use
- `BedrockRegion`: AWS region for Bedrock
- `BedrockTemperature`: Model temperature (0-1)

The ECS task automatically uses IAM role credentials for Bedrock access.

## Key Implementation Details

### Model-Agnostic Design

The system achieves true model agnosticism through:

1. **LangChain's init_chat_model**: Automatically detects and initializes the correct model based on environment variables
2. **Unified Tool Interface**: All Bedrock models use the same tool calling format
3. **Environment-Based Configuration**: No code changes needed to switch models

### Challenges Solved

1. **Inference Profile Requirements**: 
   - Newer Claude models require inference profiles
   - Solution: Use models that support direct invocation
   - Future: Add inference profile support

2. **Model Access Permissions**:
   - Some models show available but return access denied
   - Solution: Created aws-setup.sh diagnostic script

3. **Simplified Architecture**:
   - Removed multi-provider complexity
   - Focused solely on AWS Bedrock integration

## Testing

### Run Tests

```bash
# Run all tests
python tests/run_all_tests.py

# Test specific components
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v

# Test structured output functionality
python tests/test_structured_output_demo.py

# Test Docker deployment
python tests/docker_test.py
```

### Model Comparison Testing

```bash
# Test different models
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20240620-v1:0"
python main.py --demo

export BEDROCK_MODEL_ID="amazon.nova-lite-v1:0"
python main.py --demo

export BEDROCK_MODEL_ID="meta.llama3-70b-instruct-v1:0"
python main.py --demo
```

## Troubleshooting

### Common Issues

1. **Model Access Denied**: 
   - Enable the model in AWS Bedrock console
   - Check IAM permissions
   - Run `./scripts/aws-setup.sh` to diagnose

2. **Servers not starting**: Check if ports are already in use
   ```bash
   lsof -i :8081
   lsof -i :8082
   lsof -i :8083
   ```

3. **Missing BEDROCK_MODEL_ID**: The application requires this environment variable
   ```bash
   export BEDROCK_MODEL_ID="amazon.nova-lite-v1:0"
   ```

4. **Import errors**: Verify all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

5. **Server connection errors**: Ensure MCP servers are running:
   ```bash
   ./scripts/start_servers.sh
   ps aux | grep python | grep server
   ```

### Docker-Specific Issues

1. **Docker build fails**: Ensure Docker daemon is running
   ```bash
   docker info
   ```

2. **Services not starting**: Check container logs
   ```bash
   docker-compose logs forecast-server
   docker-compose logs weather-agent
   ```

3. **Network issues**: Verify Docker network
   ```bash
   docker network ls
   docker network inspect agriculture-agent-ecs_weather-network
   ```

4. **Environment variables not loading**: Check .env file
   ```bash
   docker-compose config  # Shows resolved configuration
   ```

### AWS Deployment Issues

1. **CloudFormation Stack Fails**:
   - Check CloudFormation events for specific errors
   - Verify AWS quotas (VPCs, EIPs, etc.)
   - Ensure region supports all services

2. **ECS Tasks Not Starting**:
   - Check CloudWatch logs for task errors
   - Verify ECR images exist
   - Check IAM role permissions

3. **ALB Health Checks Failing**:
   - Verify security group allows health check traffic
   - Check service logs for startup errors
   - Ensure health check path returns 200 OK

## Performance Considerations

- **Model Selection**: Claude 3.5 Sonnet provides best quality, Nova Lite best cost
- **Scaling**: Auto-scaling configured for 1-10 tasks based on CPU/memory
- **Cold Starts**: First request may be slower due to container startup
- **Caching**: Consider implementing response caching for common queries

## Security Best Practices

1. **No Hardcoded Secrets**: All credentials via environment variables or IAM roles
2. **Least Privilege IAM**: Only necessary Bedrock permissions granted
3. **VPC Isolation**: Services communicate over private network
4. **HTTPS Only**: ALB configured for secure communication
5. **Container Security**: Non-root users, minimal base images

## License

This project is provided as a demonstration of LangGraph and FastMCP integration patterns.

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- Uses [FastMCP](https://github.com/jlowin/fastmcp) for Model Context Protocol servers
- Powered by [AWS Bedrock](https://aws.amazon.com/bedrock/) for model-agnostic AI
- Weather data from [Open-Meteo API](https://open-meteo.com/) (no API key required)