# AWS Strands + FastMCP Weather Agent Demo (Model-Agnostic with AWS Bedrock)

This project demonstrates how to build a model-agnostic AI agent system using AWS Strands for orchestration and FastMCP for distributed tool servers. It showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations using any AWS Bedrock foundation model.

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

- **AWS Bedrock**: Provides access to foundation models with:
  - Unified API through Converse interface
  - Multiple model options (Claude, Llama, Cohere, etc.)
  - Consistent tool calling across models
  - Cost-effective scalability

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
# The start.sh script handles this automatically:
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
./scripts/start.sh

# Test the services
./scripts/test_docker.sh

# Stop all services
./scripts/stop.sh
```

#### Key Docker Patterns

1. **Never hardcode credentials** - Security risk and maintenance nightmare
2. **Don't use volume mounts for ~/.aws** - Doesn't work with SSO or temporary credentials
3. **Always export AWS_SESSION_TOKEN** - Required for temporary credentials
4. **Use start.sh script** - Handles all credential complexities automatically

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
     # AWS credentials passed from start.sh
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
- `BEDROCK_MODEL_ID`: AWS Bedrock model to use (required)
- `BEDROCK_REGION`: AWS region for Bedrock (default: us-west-2)
- `BEDROCK_TEMPERATURE`: Model temperature setting (default: 0)
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- MCP server ports are configured in the server files

### Supported Bedrock Models
- `anthropic.claude-3-5-sonnet-20240620-v1:0` (Recommended)
- `anthropic.claude-3-haiku-20240307-v1:0` (Fast & cost-effective)
- `meta.llama3-70b-instruct-v1:0`
- `cohere.command-r-plus-v1:0`

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

## Important Reminders

### Docker and AWS Credentials
1. **Always use the start.sh script** - It handles AWS credential export automatically
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
2. **Follow the scripts pattern** - start.sh → test_docker.sh → stop.sh
3. **Monitor logs** - Use `docker compose logs -f` for debugging
4. **Clean restarts** - Use `./scripts/stop.sh && ./scripts/start.sh` for issues