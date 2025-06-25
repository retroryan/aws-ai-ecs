# Strands Ollama Weather Agent

This project demonstrates how to build a model-agnostic AI agent system using AWS Strands for orchestration, FastMCP for distributed tool servers, and Ollama for local LLM inference. It showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations using any model available through Ollama.

## Critical Configuration: MCP Server Health Checks

### Understanding MCP Server Health Checks
MCP servers using FastMCP don't provide traditional REST health endpoints at the root path. The `/mcp/` endpoint requires specific headers and a session ID, making it unsuitable for simple health checks.

### Health Check Strategy

#### For Local Development (Docker Compose)
The MCP servers implement custom health endpoints for Docker Compose only:

```python
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

server = FastMCP(name="my-server")

@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Simple health check endpoint for Docker health checks."""
    return JSONResponse({"status": "healthy", "service": "my-server"})
```

Docker Compose uses these endpoints:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
```

#### For ECS Deployment
**IMPORTANT**: Do NOT add health checks to MCP server task definitions in ECS. Unlike traditional REST services, MCP servers:
1. Use JSON-RPC protocol which requires session management
2. Register with service discovery immediately on startup
3. Have built-in retry logic in the main service to handle connection timing

### Current Implementation Status
- ✅ All MCP servers have `/health` endpoints implemented (for Docker only)
- ✅ Docker Compose has health checks configured
- ✅ ECS task definitions correctly have NO health checks for MCP servers
- ✅ Main service has proper health check configuration and retry logic

## Architecture Overview

### Core Technologies

- **AWS Strands**: Provides the agent orchestration framework with:
  - Native MCP integration without custom wrappers
  - Built-in streaming and session management
  - Automatic tool discovery and execution
  - Multi-turn conversation support
  - Model-agnostic design with 50% less code

- **FastMCP**: Implements Model Context Protocol servers with:
  - HTTP-based tool serving
  - Async request handling
  - JSON-RPC communication
  - Easy tool discovery and registration

- **Ollama**: Provides local LLM inference with:
  - Local model hosting for privacy and control
  - Support for multiple open-source models (Llama, Mistral, Gemma, etc.)
  - Fast inference without cloud dependencies
  - Cost-effective operation without API fees

### System Components

1. **MCP Servers** (Running on separate ports):
   - **Forecast Server** (port 8081): Weather forecast data
   - **Historical Server** (port 8082): Historical weather information
   - **Agricultural Server** (port 8083): Agricultural conditions and recommendations

2. **Weather Agent**: 
   - Built with AWS Strands' native Agent class
   - Discovers and calls MCP server tools
   - Handles responses with built-in streaming
   - Maintains conversation state automatically

3. **Support Components**:
   - Query classifier for intent detection
   - Structured data models for type safety
   - Logging and monitoring utilities

## Key Files

- `main.py`: Application entry point with FastAPI interface
- `weather_agent/mcp_agent.py`: AWS Strands agent implementation
- `mcp_servers/`: FastMCP server implementations
  - `forecast_server.py`: Weather forecast tools
  - `historical_server.py`: Historical weather tools
  - `agricultural_server.py`: Agricultural data tools
- `models/`: Pydantic models for structured responses
- `start_servers.sh` / `stop_servers.sh`: Server lifecycle management

## Development Setup

### Prerequisites
- Python 3.11+
- Docker (for containerized deployment)
- Ollama installed locally (https://ollama.ai)
- At least one Ollama model pulled (e.g., `ollama pull llama3.2`)

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env and set your OLLAMA_MODEL (required, e.g., 'llama3.2')
```

### Running with Docker (Recommended)

When running with Docker, ensure Ollama is accessible from within the containers. The docker-compose configuration handles the networking to connect to the host's Ollama instance.

#### Ollama Configuration for Docker

The application connects to Ollama running on the host machine. Docker Compose is configured to use `host.docker.internal` to access the host's Ollama service.

#### Docker Commands

```bash
# Start all services with AWS credentials
./scripts/start_docker.sh

# Start with Ollama (includes Ollama container)
./scripts/start_docker_ollama.sh

# Test the services
./scripts/test_docker.sh      # For Bedrock
./scripts/test_ollama.sh     # For Ollama

# Stop all services
./scripts/stop_docker.sh
```

#### Key Docker Patterns

1. **Ensure Ollama is running** - Start Ollama before running Docker containers
2. **Check model availability** - Verify required models are pulled (`ollama list`)
3. **Monitor Ollama logs** - Use `ollama logs` for debugging
4. **Use start_docker.sh script** - Handles container orchestration

### Running Locally (Without Docker)

1. Start all MCP servers:
```bash
./scripts/start_servers.sh
```

2. Run the main application:
```bash
python main.py
```

3. Access the API at http://localhost:8090
   - Health check: GET /health
   - Submit query: POST /query

4. Stop servers when done:
```bash
./scripts/stop_servers.sh
```

## Testing

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test modules
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v
```

## Docker Configuration

### Important Docker Patterns

1. **Port Configuration**:
   - Weather Agent API: Port 8090
   - Forecast Server: Port 8081
   - Historical Server: Port 8082
   - Agricultural Server: Port 8083

2. **Environment Variables in docker-compose.yml**:
   ```yaml
   environment:
     # Ollama configuration
     - OLLAMA_HOST=${OLLAMA_HOST:-http://host.docker.internal:11434}
     - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2}
     # Optional Ollama settings
     - OLLAMA_TEMPERATURE=${OLLAMA_TEMPERATURE:-0.7}
     - OLLAMA_TIMEOUT=${OLLAMA_TIMEOUT:-60}
   ```

3. **Service Dependencies**:
   - Weather Agent depends on all MCP servers being healthy
   - Health checks ensure proper startup order
   - Retry logic handles temporary startup delays

4. **Dockerfile Best Practices**:
   - Copy only necessary files (not entire context)
   - Run as non-root user for security
   - Use specific base image versions

## MCP Server Health Checks

FastMCP servers require special handling for health checks in Docker:

1. **MCP Protocol Endpoints**: The `/mcp/` endpoint requires a session ID and uses Server-Sent Events (SSE), making it unsuitable for simple health checks.

2. **Custom Health Endpoints**: Each MCP server implements a custom `/health` endpoint using FastMCP's `@server.custom_route` decorator:
   ```python
   @server.custom_route("/health", methods=["GET"])
   async def health_check(request: Request) -> JSONResponse:
       return JSONResponse({"status": "healthy", "service": "forecast-server"})
   ```

3. **Docker Health Checks**: The docker-compose.yml uses these endpoints:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
   ```

4. **Testing MCP Endpoints**: To properly test MCP functionality, use:
   ```bash
   # Test with proper headers
   curl -X POST http://localhost:8081/mcp/ \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'
   ```

## How It Works

1. **User Query**: User submits a natural language query about weather or agriculture
2. **Agent Processing**: Strands agent analyzes the query and determines which tools to use
3. **Tool Discovery**: Agent discovers available tools from MCP servers via HTTP
4. **Tool Execution**: Agent calls appropriate MCP server tools with extracted parameters
5. **Response Processing**: Strands handles response formatting automatically
6. **User Response**: Agent formulates a natural language response with the data

## Example Queries

- "What's the weather like in Chicago?"
- "Give me a 5-day forecast for Seattle"
- "What were the temperatures in New York last week?"
- "Are conditions good for planting corn in Iowa?"
- "What's the frost risk for tomatoes in Minnesota?"

## Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── weather_agent/          # AWS Strands agent implementation
│   ├── mcp_agent.py       # Main agent logic
│   └── query_classifier.py # Query intent classification
├── mcp_servers/           # FastMCP server implementations
│   ├── forecast_server.py
│   ├── historical_server.py
│   └── agricultural_server.py
├── models/                # Data models
│   ├── requests.py
│   └── responses.py
├── utils/                 # Utility functions
├── tests/                 # Test suite
├── logs/                  # Server logs and PIDs
└── requirements.txt       # Python dependencies
```

## Logging and Monitoring

- Server logs are written to `logs/` directory
- Each MCP server maintains its own log file
- PID files enable process management
- Structured logging for debugging and monitoring

## Environment Variables

Key environment variables (configured in `.env`):
- `OLLAMA_MODEL`: Ollama model to use (required, e.g., 'llama3.2')
- `OLLAMA_HOST`: Ollama API endpoint (default: http://localhost:11434)
- `OLLAMA_TEMPERATURE`: Model temperature setting (default: 0.7)
- `OLLAMA_TIMEOUT`: Request timeout in seconds (default: 60)
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- MCP server ports are configured in the server files

### Supported Ollama Models
- `llama3.2` (3B parameters - Fast and efficient)
- `llama3.1:8b` (8B parameters - Good balance)
- `mistral` (7B parameters - Strong performance)
- `gemma2:9b` (9B parameters - Google's model)
- `qwen2.5:7b` (7B parameters - Multilingual support)

## Extending the System

To add new capabilities:

1. **Add a new MCP server**:
   - Create a new server file in `mcp_servers/`
   - Implement tools using FastMCP decorators
   - Add server startup to `start_servers.sh`

2. **Add new tools to existing servers**:
   - Add new methods with `@weather_server.tool()` decorator
   - Define input/output schemas
   - Tools are automatically discovered by the agent

3. **Customize agent behavior**:
   - Modify prompts in `mcp_agent.py`
   - Add new response transformations
   - Implement custom tool selection logic

## Local Testing and Development

### Prerequisites for Local Testing

1. **Python Environment**:
   ```bash
   pyenv local 3.12.10  # Set Python version
   pip install -r requirements.txt  # Install dependencies
   ```

2. **Ollama Configuration**:
   ```bash
   # Ensure Ollama is running
   ollama serve  # If not already running
   
   # Pull a model if needed
   ollama pull llama3.2
   
   # Set required environment variable
   export OLLAMA_MODEL=llama3.2
   export OLLAMA_HOST=http://localhost:11434
   ```

### Local Testing Steps

#### 1. Start MCP Servers
```bash
# Start all three MCP servers (forecast, historical, agricultural)
./scripts/start_servers.sh

# Verify servers are running
curl http://localhost:8081/health  # Forecast server
curl http://localhost:8082/health  # Historical server  
curl http://localhost:8083/health  # Agricultural server
```

#### 2. Test Basic Agent Functionality
```bash
# Test agent creation and connectivity
python -c "
import asyncio
from weather_agent.mcp_agent import MCPWeatherAgent

async def test():
    agent = MCPWeatherAgent()
    print('✅ Agent created')
    
    connectivity = await agent.test_connectivity()
    print('🔗 Server connectivity:', connectivity)
    
    if any(connectivity.values()):
        response = await agent.query('What is the weather in Seattle?')
        print('📝 Response length:', len(response))
        print('✅ Basic test PASSED')
    else:
        print('❌ No servers available')

asyncio.run(test())
"
```

#### 3. Test Structured Output
```bash
# Test structured output functionality
python -c "
import asyncio
from weather_agent.mcp_agent import MCPWeatherAgent

async def test():
    agent = MCPWeatherAgent()
    response = await agent.query_structured('What is the weather in Chicago?')
    
    print('✅ Structured response generated')
    print('📍 Locations found:', len(response.locations))
    if response.locations:
        loc = response.locations[0]
        print(f'🌍 Location: {loc.name}')
        print(f'📍 Coordinates: ({loc.latitude}, {loc.longitude})')
    print('✅ Structured output test PASSED')

asyncio.run(test())
"
```

#### 4. Test System Prompt Loading
```bash
# Test different prompt types
python -c "
from weather_agent.prompts import PromptManager

pm = PromptManager()
print('Available prompts:', pm.get_available_prompts())

# Test environment variable control
import os
os.environ['SYSTEM_PROMPT'] = 'agriculture'

from weather_agent.mcp_agent import MCPWeatherAgent
agent = MCPWeatherAgent()
print('Agent using prompt type:', agent.prompt_type)
print('✅ Prompt loading test PASSED')
"
```

#### 5. Run Comprehensive Tests
```bash
# Run the comprehensive test suite
python tests/test_mcp_agent_strands.py

# Run structured output demo
python -m weather_agent.structured_output_demo
```

#### 6. Clean Up
```bash
# Stop all servers when done
./scripts/stop_servers.sh
```

### Testing Different Components

#### Test Individual MCP Servers
```bash
# Test forecast server
curl -X POST http://localhost:8081/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test historical server  
curl -X POST http://localhost:8082/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test agricultural server
curl -X POST http://localhost:8083/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

#### Test Agent with Different Models
```bash
# Test with different Ollama models
OLLAMA_MODEL=mistral python -c "
import asyncio
from weather_agent.mcp_agent import MCPWeatherAgent

async def test():
    agent = MCPWeatherAgent()
    print('Using model:', agent.model_id)
    response = await agent.query('Weather in Denver?')
    print('Response length:', len(response))

asyncio.run(test())
"
```

### Troubleshooting Local Testing

#### Common Issues and Solutions

1. **MCP Servers Won't Start**:
   ```bash
   # Check if ports are in use
   lsof -i :8081,8082,8083
   
   # Kill processes using the ports
   lsof -ti:8081,8082,8083 | xargs kill -9
   
   # Restart servers
   ./scripts/start_servers.sh
   ```

2. **Ollama Connection Issues**:
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/api/tags
   
   # List available models
   ollama list
   
   # Test Ollama directly
   curl -X POST http://localhost:11434/api/generate -d '{
     "model": "llama3.2",
     "prompt": "Hello"
   }'
   ```

3. **Import Errors**:
   ```bash
   # Ensure you're in the project root
   pwd  # Should be strands-weather-agent
   
   # Test imports
   python -c "from weather_agent.mcp_agent import MCPWeatherAgent; print('Imports work')"
   ```

4. **Model Loading Issues**:
   ```bash
   # Pull the model if not available
   ollama pull llama3.2
   
   # Check model details
   ollama show llama3.2
   
   # Test model directly
   ollama run llama3.2 "Say hello"
   ```

### Performance Testing

#### Test Response Times
```bash
python -c "
import asyncio
import time
from weather_agent.mcp_agent import MCPWeatherAgent

async def benchmark():
    agent = MCPWeatherAgent()
    
    queries = [
        'Weather in New York?',
        'Temperature in London?', 
        'Forecast for Tokyo?'
    ]
    
    total_time = 0
    for query in queries:
        start = time.time()
        await agent.query(query)
        elapsed = time.time() - start
        total_time += elapsed
        print(f'{query}: {elapsed:.2f}s')
    
    print(f'Average: {total_time/len(queries):.2f}s')

asyncio.run(benchmark())
"
```

## Important Reminders

### Docker and Ollama Integration
1. **Ensure Ollama is running on host** - Docker containers connect to host's Ollama
2. **Use host.docker.internal** - Docker Desktop's special hostname for host access
3. **Test with test_docker.sh** - Verifies both health and functionality
4. **Monitor Ollama performance** - Check memory usage with larger models

### Common Pitfalls to Avoid
1. **Don't forget to start Ollama** - Must be running before containers start
2. **Don't use large models without enough RAM** - Check system requirements
3. **Don't hardcode ports** - Use environment variables for flexibility
4. **Don't skip health checks** - They ensure services start in the correct order

### Best Practices
1. **Use Docker for consistency** - Same environment locally and in production
2. **Follow the scripts pattern** - start_docker.sh → test_docker.sh → stop_docker.sh
3. **Monitor logs** - Use `docker compose logs -f` for debugging
4. **Clean restarts** - Use `./scripts/stop_docker.sh && ./scripts/start_docker.sh` for issues
5. **Test locally first** - Always validate with local testing before Docker/deployment