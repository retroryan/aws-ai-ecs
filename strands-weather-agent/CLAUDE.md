# AWS Strands + FastMCP Weather Agent Demo (Model-Agnostic with AWS Bedrock)

This project demonstrates how to build a model-agnostic AI agent system using AWS Strands for orchestration and FastMCP for distributed tool servers. It showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations using any AWS Bedrock foundation model.

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
  test: ["CMD", "curl", "-f", "http://localhost:7778/health"]
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
  - Pure async implementation for better performance
  - Integrated telemetry and observability support

- **FastMCP**: Implements Model Context Protocol servers with:
  - HTTP-based tool serving with streamable clients
  - Async request handling
  - JSON-RPC communication
  - Easy tool discovery and registration
  - Custom health endpoints for Docker deployments

- **AWS Bedrock**: Provides access to foundation models with:
  - Unified API through Converse interface
  - Multiple model options (Claude, Llama, Cohere, etc.)
  - Consistent tool calling across models
  - Cost-effective scalability

- **Langfuse**: Provides comprehensive observability with:
  - OpenTelemetry-based distributed tracing
  - Token usage and cost tracking
  - Latency and performance metrics
  - Session and user analytics
  - Custom tags and metadata support

### System Components

1. **MCP Servers** (Running on separate ports):
   - **Forecast Server** (port 7778): Weather forecast data
   - **Historical Server** (port 7779): Historical weather information
   - **Agricultural Server** (port 7780): Agricultural conditions and recommendations

2. **Weather Agent**: 
   - Built with AWS Strands' native Agent class
   - Pure async implementation with `stream_async()`
   - Discovers and calls MCP server tools via HTTP
   - Handles responses with built-in streaming
   - Maintains conversation state automatically
   - Integrated Langfuse telemetry for observability
   - Debug logging with separate console/file handlers

3. **Support Components**:
   - Query classifier for intent detection
   - Structured data models for type safety
   - Comprehensive logging and monitoring utilities
   - Langfuse telemetry integration for metrics
   - Validation and monitoring scripts

## Key Files

- `main.py`: Application entry point with FastAPI interface and debug logging
- `weather_agent/mcp_agent.py`: AWS Strands agent implementation with pure async
- `weather_agent/langfuse_telemetry.py`: Langfuse observability integration
- `mcp_servers/`: FastMCP server implementations
  - `forecast_server.py`: Weather forecast tools
  - `historical_server.py`: Historical weather tools
  - `agricultural_server.py`: Agricultural data tools
- `models/`: Pydantic models for structured responses
- `strands-metrics-guide/`: Validation and monitoring scripts
  - `run_and_validate_metrics.py`: End-to-end metrics validation
  - `debug_telemetry.py`: Telemetry configuration debugging
  - `inspect_traces.py`: Trace inspection utility
  - `monitor_performance.py`: Performance impact analysis
- `scripts/start_servers.sh` / `stop_servers.sh`: Server lifecycle management

## Development Setup

### Prerequisites
- Python 3.11+
- Docker (for containerized deployment)
- AWS account with Bedrock access enabled
- AWS CLI configured with credentials

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env and set your BEDROCK_MODEL_ID (required)
```

### Running with Docker (Recommended)

The key to running AWS applications in Docker is proper credential handling. Our solution uses the AWS CLI's `export-credentials` command to automatically extract and pass credentials.

#### The Magic: AWS Credentials in Docker

```bash
# The start_docker.sh script handles this automatically:
export $(aws configure export-credentials --format env-no-export 2>/dev/null)
```

This command:
- Extracts credentials from your current AWS CLI configuration
- Exports them as environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
- Works with ALL authentication methods:
  - AWS CLI profiles
  - AWS SSO (Single Sign-On)
  - Temporary credentials
  - IAM roles
  - MFA-enabled accounts

#### Docker Commands

```bash
# Start all services with AWS credentials
./scripts/start_docker.sh

# Test the services
./scripts/test_docker.sh

# Stop all services
./scripts/stop_docker.sh
```

#### Key Docker Patterns

1. **Never hardcode credentials** - Security risk and maintenance nightmare
2. **Don't use volume mounts for ~/.aws** - Doesn't work with SSO or temporary credentials
3. **Always export AWS_SESSION_TOKEN** - Required for temporary credentials
4. **Use start_docker.sh script** - Handles all credential complexities automatically

### Running Locally (Without Docker)

1. Start all MCP servers:
```bash
./scripts/start_servers.sh
```

2. Run the main application:
```bash
# Run with default settings
python main.py

# Run with debug logging enabled
python main.py --debug

# Or set environment variable
export WEATHER_AGENT_DEBUG=true
python main.py
```

3. Access the API at http://localhost:7777
   - Health check: GET /health
   - Submit query: POST /query
   - Debug logs are saved to `logs/weather_agent_debug_YYYYMMDD_HHMMSS.log`

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
   - Weather Agent API: Port 7777
   - Forecast Server: Port 7778
   - Historical Server: Port 7779
   - Agricultural Server: Port 7780

2. **Environment Variables in docker-compose.yml**:
   ```yaml
   environment:
     # AWS credentials passed from start_docker.sh
     - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
     - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
     - AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
     - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-west-2}
     # Bedrock configuration
     - BEDROCK_MODEL_ID=${BEDROCK_MODEL_ID}
     - BEDROCK_REGION=${BEDROCK_REGION:-us-west-2}
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
     test: ["CMD", "curl", "-f", "http://localhost:7778/health"]
   ```

4. **Testing MCP Endpoints**: To properly test MCP functionality, use:
   ```bash
   # Test with proper headers
   curl -X POST http://localhost:7778/mcp/ \
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

### Debug Logging
- **Comprehensive Debug Mode**: Enable with `--debug` flag or `WEATHER_AGENT_DEBUG=true`
- **Dual Logging**: Console shows INFO level, file shows DEBUG level
- **Timestamped Log Files**: Saved to `logs/weather_agent_debug_YYYYMMDD_HHMMSS.log`
- **Module-Specific Debugging**: Enables debug for Strands modules:
  - `strands`, `strands.tools`, `strands.models`
  - `strands.tools.mcp`, `strands_agent.tools`
- **Structured Format**: Includes timestamps, logger name, level, function, and line numbers

### Server Logs
- Server logs are written to `logs/` directory
- Each MCP server maintains its own log file
- PID files enable process management
- Structured logging for debugging and monitoring

### Observability with Langfuse
- **Automatic Tracing**: All agent interactions are traced
- **Token Usage Tracking**: Monitor LLM token consumption and costs
- **Latency Metrics**: Track response times and performance
- **Session Management**: Group related queries together
- **Custom Tags**: Add metadata for filtering and analysis
- **OpenTelemetry Integration**: Standard OTEL protocol support

## Environment Variables

Key environment variables (configured in `.env`):

### AWS Bedrock Configuration
- `BEDROCK_MODEL_ID`: AWS Bedrock model to use (required)
- `BEDROCK_REGION`: AWS region for Bedrock (default: us-west-2)
- `BEDROCK_TEMPERATURE`: Model temperature setting (default: 0)

### Logging Configuration
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `WEATHER_AGENT_DEBUG`: Enable debug logging (true/false)

### Langfuse Telemetry Configuration
- `LANGFUSE_PUBLIC_KEY`: Public key for Langfuse API
- `LANGFUSE_SECRET_KEY`: Secret key for Langfuse API
- `LANGFUSE_HOST`: Langfuse API host (default: https://us.cloud.langfuse.com)
- `ENABLE_TELEMETRY`: Enable/disable telemetry (true/false, default: false)
- `TELEMETRY_USER_ID`: Default user ID for telemetry
- `TELEMETRY_SESSION_ID`: Default session ID for telemetry
- `TELEMETRY_TAGS`: Comma-separated tags for filtering

### MCP Server Configuration
- MCP server ports are configured in the server files (7778, 7779, 7780)

### Supported Bedrock Models

**IMPORTANT**: AWS Bedrock now requires inference profiles for most models. Use the `us.` prefix for cross-region redundancy:

- `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (Latest, recommended - uses inference profile)
- `us.anthropic.claude-3-5-sonnet-20240620-v1:0` (Stable - uses inference profile)
- `us.anthropic.claude-3-5-haiku-20241022-v1:0` (Fast & cost-effective - uses inference profile)
- `us.meta.llama3-1-70b-instruct-v1:0` (Open source - uses inference profile)
- `cohere.command-r-plus-v1:0` (RAG optimized - may not require profile)

Note: The `us.` prefix indicates an inference profile that provides cross-region failover between us-east-1 and us-west-2. The `scripts/aws-setup.sh` script will automatically detect and use inference profiles when available.

## Recent Improvements and Updates

### Pure Async Implementation
- **Eliminated ThreadPoolExecutor**: The agent now uses pure async patterns throughout
- **Streamable HTTP Clients**: MCP clients use `streamablehttp_client` for better async communication
- **Async Streaming**: Uses `stream_async()` for processing queries with better performance
- **Context Management**: Proper use of `ExitStack` to keep MCP clients open during execution

### Enhanced Debug Logging
- **Dual-Level Logging**: Console (INFO) and file (DEBUG) with separate handlers
- **Timestamped Log Files**: Automatic file creation with timestamps
- **Module-Specific Debug**: Targeted debugging for Strands components
- **CLI Integration**: Simple `--debug` flag or environment variable control

### Comprehensive Metrics with Langfuse
- **Full OpenTelemetry Support**: Standard OTEL protocol integration
- **Automatic Instrumentation**: Zero-code changes needed for basic metrics
- **Rich Metadata**: Session tracking, user identification, and custom tags
- **Performance Monitoring**: Token usage, latency, and cost tracking
- **Validation Tools**: Complete suite of scripts for testing and monitoring

### Code Simplification
- **50% Less Code**: Major cleanup removed over 10,000 lines
- **Consolidated Structure**: Streamlined project organization
- **Native Strands Integration**: Eliminated custom wrapper code
- **Better Error Handling**: Specific exception types for different failures

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

2. **AWS Configuration**:
   ```bash
   # Set required environment variable
   export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
   export BEDROCK_REGION=us-west-2
   
   # Ensure AWS credentials are configured
   aws configure list  # Check current configuration
   ```

### Local Testing Steps

#### 1. Start MCP Servers
```bash
# Start all three MCP servers (forecast, historical, agricultural)
./scripts/start_servers.sh

# Verify servers are running
curl http://localhost:7778/health  # Forecast server
curl http://localhost:7779/health  # Historical server  
curl http://localhost:7780/health  # Agricultural server
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
curl -X POST http://localhost:7778/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test historical server  
curl -X POST http://localhost:7779/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'

# Test agricultural server
curl -X POST http://localhost:7780/mcp/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

#### Test Agent with Different Models
```bash
# Test with different AWS Bedrock models
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0 python -c "
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
   lsof -i :7778,7779,7780
   
   # Kill processes using the ports
   lsof -ti:7778,7779,7780 | xargs kill -9
   
   # Restart servers
   ./scripts/start_servers.sh
   ```

2. **AWS Credentials Issues**:
   ```bash
   # Check AWS identity
   aws sts get-caller-identity
   
   # Export credentials manually if needed
   export $(aws configure export-credentials --format env-no-export)
   ```

3. **Import Errors**:
   ```bash
   # Ensure you're in the project root
   pwd  # Should be strands-weather-agent
   
   # Test imports
   python -c "from weather_agent.mcp_agent import MCPWeatherAgent; print('Imports work')"
   ```

4. **Model Access Issues**:
   ```bash
   # Test AWS Bedrock access
   aws bedrock list-foundation-models --region us-west-2
   
   # Check model availability
   aws bedrock get-foundation-model --model-identifier anthropic.claude-3-5-sonnet-20241022-v2:0 --region us-west-2
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

### Testing with Telemetry

#### Enable Telemetry for a Session
```bash
# Set up Langfuse credentials
export LANGFUSE_PUBLIC_KEY=your_public_key
export LANGFUSE_SECRET_KEY=your_secret_key
export LANGFUSE_HOST=https://us.cloud.langfuse.com

# Run with telemetry enabled
python -c "
import asyncio
from weather_agent.mcp_agent import MCPWeatherAgent

async def test_with_telemetry():
    agent = MCPWeatherAgent(
        enable_telemetry=True,
        telemetry_user_id='test-user-123',
        telemetry_session_id='test-session-456',
        telemetry_tags=['test', 'development']
    )
    
    response = await agent.query('What is the weather in Chicago?')
    print('Response received')
    print('Check Langfuse dashboard for traces')

asyncio.run(test_with_telemetry())
"
```

#### Validate Metrics Collection
```bash
# Run comprehensive validation
cd strands-metrics-guide
python run_and_validate_metrics.py

# Debug telemetry configuration
python debug_telemetry.py

# Inspect collected traces
python inspect_traces.py

# Monitor performance impact
python monitor_performance.py
```

## Important Reminders

### Docker and AWS Credentials
1. **Always use the start_docker.sh script** - It handles AWS credential export automatically
2. **Never commit credentials** - Use environment variables and .env files (in .gitignore)
3. **Test with test_docker.sh** - Verifies both health and functionality
4. **Check AWS identity** - The start script shows which AWS account is being used

### Common Pitfalls to Avoid
1. **Don't use AWS profiles in Docker** - Containers can't access ~/.aws/config
2. **Don't forget AWS_SESSION_TOKEN** - Required for SSO and temporary credentials
3. **Don't hardcode ports** - Use environment variables for flexibility
4. **Don't skip health checks** - They ensure services start in the correct order

### Best Practices
1. **Use Docker for consistency** - Same environment locally and in production
2. **Follow the scripts pattern** - start_docker.sh → test_docker.sh → stop_docker.sh
3. **Monitor logs** - Use `docker compose logs -f` for debugging
4. **Clean restarts** - Use `./scripts/stop_docker.sh && ./scripts/start_docker.sh` for issues
5. **Test locally first** - Always validate with local testing before Docker/deployment