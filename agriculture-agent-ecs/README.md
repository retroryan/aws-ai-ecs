# LangGraph + FastMCP Weather Agent Demo

A demonstration of building AI agent systems using LangGraph for orchestration and FastMCP for distributed tool servers. This project showcases a weather and agricultural data agent that can answer questions about weather conditions, forecasts, and agricultural recommendations.

## Features

- **LangGraph Agent Orchestration**: React agent pattern with conversation memory
- **FastMCP Tool Servers**: Distributed HTTP-based Model Context Protocol servers
- **Structured Output Support**: Optional transformation to typed Pydantic models
- **Multi-turn Conversations**: Maintains context across interactions
- **Real Weather Data**: Integration with OpenWeatherMap API

## Quick Start

```bash
# Prerequisites: Python 3.11+ and OpenWeatherMap API key

# Clone the repository
git clone <repository-url>
cd agriculture-agent-ecs

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENWEATHER_API_KEY

# Start MCP servers
./start_servers.sh

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

2. **LangGraph Agent**:
   - Built with `create_react_agent` for tool selection
   - Discovers tools from MCP servers via HTTP
   - Supports both text and structured responses
   - Maintains conversation state with memory

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
│   └── agricultural_server.py # Agricultural data tools
├── models/                 # Data models
├── utils/                  # Utility functions
├── tests/                  # Test suite
└── logs/                   # Server logs and PIDs
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
./start_servers.sh

# Check server status
ps aux | grep python | grep server

# View server logs
tail -f logs/forecast_server.log
tail -f logs/historical_server.log
tail -f logs/agricultural_server.log

# Stop all servers
./stop_servers.sh
```

## Configuration

### Environment Variables

Create a `.env` file with:

```env
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional
LOG_LEVEL=INFO
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

# Add to start_servers.sh
```

### Customizing the Agent

Modify `weather_agent/mcp_agent.py` to:
- Change agent prompts
- Add new response formats
- Implement custom tool selection logic
- Add new structured output models

## Troubleshooting

### Common Issues

1. **Servers not starting**: Check if ports are already in use
   ```bash
   lsof -i :7071
   lsof -i :7072
   lsof -i :7073
   ```

2. **API key errors**: Ensure your OpenWeatherMap API key is valid and set in `.env`

3. **Import errors**: Verify all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

4. **Server connection errors**: Ensure MCP servers are running:
   ```bash
   ./start_servers.sh
   ps aux | grep python | grep server
   ```

## License

This project is provided as a demonstration of LangGraph and FastMCP integration patterns.

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent orchestration
- Uses [FastMCP](https://github.com/jlowin/fastmcp) for Model Context Protocol servers
- Weather data from [OpenWeatherMap API](https://openweathermap.org/api)