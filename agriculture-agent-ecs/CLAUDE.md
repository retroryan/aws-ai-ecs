# LangGraph + FastMCP Weather Agent Demo (Model-Agnostic with AWS Bedrock)

This project demonstrates how to build a model-agnostic AI agent system using LangGraph for orchestration and FastMCP for distributed tool servers. It showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations using any AWS Bedrock foundation model.

## Architecture Overview

### Core Technologies

- **LangGraph**: Provides the agent orchestration framework with:
  - React agent pattern for tool selection and execution
  - Conversation memory with checkpointing
  - Structured output transformation
  - Multi-turn conversation support
  - Model-agnostic design via `init_chat_model`

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
   - **Forecast Server** (port 7071): Weather forecast data
   - **Historical Server** (port 7072): Historical weather information
   - **Agricultural Server** (port 7073): Agricultural conditions and recommendations

2. **Weather Agent**: 
   - Built with LangGraph's `create_react_agent`
   - Discovers and calls MCP server tools
   - Optionally transforms responses to structured Pydantic models
   - Maintains conversation state across interactions

3. **Support Components**:
   - Query classifier for intent detection
   - Structured data models for type safety
   - Logging and monitoring utilities

## Key Files

- `main.py`: Application entry point (interactive chatbot)
- `weather_agent/mcp_agent.py`: LangGraph agent implementation
- `mcp_servers/`: FastMCP server implementations
  - `forecast_server.py`: Weather forecast tools
  - `historical_server.py`: Historical weather tools
  - `agricultural_server.py`: Agricultural data tools
- `weather_agent/models.py`: Pydantic models for structured responses
- `start_servers.sh` / `stop_servers.sh`: Server lifecycle management

## Development Setup

### Prerequisites
- Python 3.11+
- AWS account with Bedrock access enabled
- AWS credentials configured

### Installation
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env and set your BEDROCK_MODEL_ID (required)

# Install dependencies (from weather_agent directory)
cd weather_agent
pip install -r requirements.txt
cd ..
```

### Running the System

1. Start all MCP servers:
```bash
./start_servers.sh
```

2. Run the weather agent:
```bash
cd weather_agent
python chatbot.py
```

3. Stop servers when done:
```bash
./stop_servers.sh
```

## Testing

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test modules
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v
```

## How It Works

1. **User Query**: User submits a natural language query about weather or agriculture
2. **Agent Processing**: LangGraph agent analyzes the query and determines which tools to use
3. **Tool Discovery**: Agent discovers available tools from MCP servers via HTTP
4. **Tool Execution**: Agent calls appropriate MCP server tools with extracted parameters
5. **Response Transformation**: Raw tool responses are optionally transformed to structured models
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
├── weather_agent/          # LangGraph agent implementation
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