# LangGraph + FastMCP Weather Agent Demo (Model-Agnostic with AWS Bedrock)

A demonstration of building model-agnostic AI agent systems using LangGraph for orchestration and FastMCP for distributed tool servers. This project showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations using any AWS Bedrock foundation model.

## Features

- **Model-Agnostic Design**: Works with any AWS Bedrock model via `init_chat_model`
- **LangGraph Agent Orchestration**: React agent pattern with conversation memory
- **FastMCP Tool Servers**: Distributed HTTP-based Model Context Protocol servers
- **Structured Output Support**: Optional transformation to typed Pydantic models
- **Multi-turn Conversations**: Maintains context across interactions
- **Real Weather Data**: Integration with OpenWeatherMap API
- **AWS Bedrock Integration**: Supports Claude, Llama, Cohere, Amazon Nova, and more

## Quick Start

```bash
# Prerequisites: Python 3.11+, AWS account with Bedrock access, OpenWeatherMap API key

# Clone the repository
git clone <repository-url>
cd agriculture-agent-ecs

# Install dependencies
pip install -r requirements.txt

# Auto-configure AWS Bedrock (recommended)
./aws-setup.sh
cp bedrock.env .env

# Or manually configure
cp .env.example .env
# Edit .env and set:
# - BEDROCK_MODEL_ID (required)
# - BEDROCK_REGION
# - OPENWEATHER_API_KEY

# Start MCP servers
./scripts/start_servers.sh

# Run the application
python main.py

# Access the API
curl http://localhost:8000/health
```

## Architecture

### System Components

1. **FastMCP Servers** (HTTP endpoints):
   - **Forecast Server** (port 7071): Weather forecast data
   - **Historical Server** (port 7072): Historical weather information
   - **Agricultural Server** (port 7073): Agricultural conditions and recommendations

2. **Model-Agnostic LangGraph Agent**:
   - Uses `init_chat_model` for provider-agnostic initialization
   - Built with `create_react_agent` for tool selection
   - Discovers tools from MCP servers via HTTP
   - Supports both text and structured responses
   - Maintains conversation state with memory
   - Works with any AWS Bedrock foundation model

3. **FastAPI Application**:
   - REST API interface for queries
   - Health check endpoints
   - Request/response models

### Data Flow

1. User submits natural language query via API
2. LangGraph agent analyzes query and selects appropriate tools
3. Agent calls FastMCP server tools with extracted parameters
4. Raw JSON responses optionally transformed to structured models
5. Agent formulates natural language response

## Usage Examples

### API Usage

```python
import requests

# Submit a weather query
response = requests.post("http://localhost:8000/query", 
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

## Model Configuration

### Supported AWS Bedrock Models

The system works with any Bedrock model that supports tool/function calling:

- **Claude Models** (Anthropic):
  - `anthropic.claude-3-5-sonnet-20240620-v1:0` - Best overall performance
  - `anthropic.claude-3-haiku-20240307-v1:0` - Fast and cost-effective
  - `anthropic.claude-3-opus-20240229-v1:0` - Most capable

- **Amazon Nova Models**:
  - `amazon.nova-pro-v1:0` - High performance
  - `amazon.nova-lite-v1:0` - Cost-effective, good for demos

- **Llama Models** (Meta):
  - `meta.llama3-70b-instruct-v1:0` - Open source, excellent performance
  - `meta.llama3-1-70b-instruct-v1:0` - Latest Llama 3.1

- **Cohere Models**:
  - `cohere.command-r-plus-v1:0` - Optimized for RAG and tool use
  - `cohere.command-r-v1:0` - Efficient alternative

### Switching Models

Simply change the `BEDROCK_MODEL_ID` environment variable:

```bash
# For best performance
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20240620-v1:0"

# For cost-effective operation
export BEDROCK_MODEL_ID="amazon.nova-lite-v1:0"

# For open source
export BEDROCK_MODEL_ID="meta.llama3-70b-instruct-v1:0"
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
curl http://localhost:8000/health
```

### Docker Architecture

The application is containerized with the following services:

- **forecast-server**: Weather forecast MCP server (port 7071)
- **historical-server**: Historical weather MCP server (port 7072)  
- **agricultural-server**: Agricultural conditions MCP server (port 7073)
- **weather-agent**: Main agent application (port 8000)

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
- Forecast Server: 7071
- Historical Server: 7072
- Agricultural Server: 7073

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

## Testing

### Run Tests

```bash
# Run all tests
python tests/run_all_tests.py

# Test specific components
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v
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
   - Try `./scripts/aws-setup.sh` to diagnose

2. **Servers not starting**: Check if ports are already in use
   ```bash
   lsof -i :7071
   lsof -i :7072
   lsof -i :7073
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

5. **Permission issues**: Ensure proper file permissions
   ```bash
   chmod +x scripts/test_docker.sh
   chmod +x tests/docker_test.py
   ```

## License

This project is provided as a demonstration of LangGraph and FastMCP integration patterns.

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- Uses [FastMCP](https://github.com/jlowin/fastmcp) for Model Context Protocol servers
- Weather data from [OpenWeatherMap API](https://openweathermap.org/api)