# Development Guide

This guide covers local development, testing, debugging, and development scripts for the Strands Weather Agent project.

## Local Development

### Prerequisites

- Python 3.12+
- Docker (optional, for containerized development)
- AWS CLI configured with Bedrock access
- pyenv (recommended for Python version management)

### Local Development: Direct Python Execution (Interactive Chatbot)

Run the weather agent as an interactive chatbot:

```bash
# 1. Configure AWS Bedrock access
./scripts/aws-setup.sh

# 2. Start MCP servers (runs in background)
./scripts/start_server.sh

# 3. Navigate to weather agent directory
cd weather_agent

# 4. Set Python version and install dependencies
pyenv local 3.12.10
pip install -r requirements.txt

# 5. Run the interactive chatbot
python chatbot.py                    # Interactive mode
python chatbot.py --demo             # Demo mode with example queries
python chatbot.py --multi-turn-demo  # Multi-turn conversation demo

# Add --debug to any mode to see internal processing:
python chatbot.py --demo --debug     # Shows tool calls and streaming
python chatbot.py --multi-turn-demo --debug  # Shows context retention

# 6. Stop servers when done (from project root)
cd .. && ./scripts/stop_server.sh
```

## Testing

### Running Test Suites

```bash
# Comprehensive testing with one command
./scripts/run_tests.sh

# With Docker integration tests
./scripts/run_tests.sh --with-docker

# Quick test of core functionality
./scripts/test_agent.sh

# Run specific test modules
python -m pytest tests/test_mcp_servers.py -v
python -m pytest tests/test_weather_agent.py -v
python -m pytest tests/test_coordinates_consolidated.py -v
```

### Unit Testing

The test suite includes:
- **MCP Server Tests**: Validates all weather tools and API interactions
- **Agent Tests**: Tests the AWS Strands agent functionality
- **Coordinate Tests**: Tests geographic coordinate extraction and validation
- **Structured Output Tests**: Validates Pydantic models and response formatting

### Integration Testing

Integration tests verify:
- MCP server connectivity
- Tool discovery and execution
- Multi-turn conversation handling
- Session management
- Error handling and recovery

## Debugging

### Debug Mode - Understanding the Output

When running demos with `--debug`, you'll see the internal workings of AWS Strands:

```
🔍 DEBUG MODE ENABLED:
   - Model's natural language will appear as it streams
   - 🔧 [AGENT DEBUG - Tool Call] = Our agent's tool usage logging
   - 📥 [AGENT DEBUG - Tool Input] = Tool parameters being sent
   - Strands internal debug logs = Framework's internal processing
```

Example output breakdown:
- **"Tool #1: get_weather_forecast"** - The LLM's natural language describing what it's doing
- **"🔧 [AGENT DEBUG - Tool Call]: get_weather_forecast"** - Our agent tracking tool execution
- **"📥 [AGENT DEBUG - Tool Input]: {'location': 'Seattle'}"** - Parameters sent to the tool
- **Strands logs** - Framework's internal processing (event loops, streaming, etc.)

This helps you understand:
1. How the LLM thinks about tool usage
2. Which tools are actually being called
3. What parameters are being passed
4. How Strands orchestrates the entire flow

### Debug Logging Configuration

Debug logs are saved to timestamped files in the `logs/` directory:
- Console shows INFO level messages
- Log files contain detailed DEBUG information
- Includes AWS Strands internal processing details

Enable debug mode:
```bash
# Via command line flag
python main.py --debug

# Via environment variable
export WEATHER_AGENT_DEBUG=true
python main.py
```

## Running Interactive Demos

### 1. Simple Interactive Chatbot
```bash
# Start MCP servers and run chatbot
./scripts/start_server.sh
python -m weather_agent.main               # Interactive mode
python -m weather_agent.main --demo        # Demo mode with examples
./scripts/stop_server.sh
```

### 2. Multi-Turn Conversation Demos 🎯

```bash
# Basic multi-turn conversation demo
python -m weather_agent.demo_scenarios

# Context switching demo (advanced scenarios)
python -m weather_agent.demo_scenarios --context-switching

# Show detailed tool calls during demo
python -m weather_agent.demo_scenarios --structured
```

**What the multi-turn demos showcase:**
- **Turn 1:** "What's the weather like in Seattle?"
- **Turn 2:** "How does it compare to Portland?" (remembers Seattle)
- **Turn 3:** "Which city would be better for outdoor activities?" (remembers both cities)
- **Turn 4:** Agricultural queries with location context
- **Turn 5:** Comprehensive summaries using accumulated context

## Development Scripts Reference

### Core Scripts

#### `scripts/aws-setup.sh`
Configures AWS Bedrock access and validates your environment:
- Checks AWS CLI configuration
- Verifies Bedrock access permissions
- Sets up required environment variables
- Lists available Bedrock models

#### `scripts/start_server.sh`
Starts the MCP weather server in the background:
- Launches the unified weather server on port 7778
- Creates PID file for process management
- Logs output to `logs/` directory

#### `scripts/stop_server.sh`
Stops all running MCP servers:
- Gracefully terminates server processes
- Cleans up PID files
- Preserves log files for debugging

### Docker Scripts

#### `scripts/start_docker.sh [--debug]`
Starts all services in Docker containers:
- Exports AWS credentials automatically
- Builds and starts all containers
- Optional `--debug` flag for verbose logging
- Shows container status and health

#### `scripts/test_docker.sh`
Tests the Docker deployment:
- Verifies health endpoints
- Runs sample queries
- Tests multi-turn conversations
- Shows full response output

#### `scripts/stop_docker.sh`
Stops and cleans up Docker services:
- Stops all containers
- Removes containers and networks
- Preserves volumes and images

### Testing Scripts

#### `scripts/run_tests.sh [--with-docker]`
Comprehensive test runner:
- Runs all unit tests
- Optional Docker integration tests
- Generates coverage reports
- Shows test summary

#### `scripts/test_agent.sh`
Quick agent functionality test:
- Tests MCP connectivity
- Runs sample queries
- Validates structured output
- Checks session management

## Best Practices

### Code Style
- Use type hints for all function parameters and returns
- Follow PEP 8 style guidelines
- Add docstrings to all public functions
- Keep functions focused and single-purpose

### Testing
- Write tests for new features before implementation
- Maintain test coverage above 80%
- Use meaningful test names that describe the scenario
- Mock external API calls in unit tests

### Error Handling
- Use specific exception types from `weather_agent.exceptions`
- Always log errors with appropriate context
- Provide helpful error messages to users
- Implement graceful degradation where possible

### Performance
- Use async/await for all I/O operations
- Cache MCP tool discoveries when possible
- Implement request timeouts
- Monitor memory usage in long-running sessions

## Common Development Tasks

### Adding a New Tool

1. Add the tool to the MCP server:
```python
@weather_server.tool
async def get_uv_index(location: str) -> dict:
    """Get UV index for a location."""
    # Implementation
    return {"location": location, "uv_index": 5}
```

2. The tool is automatically discovered by the agent - no additional configuration needed!

### Modifying the System Prompt

Edit the prompt files in `weather_agent/prompts/`:
- `default.txt` - Standard weather assistant prompt
- `agriculture_structured.txt` - Agricultural-focused prompt

### Adding Structured Output Models

Create new Pydantic models in `weather_agent/models/structured_responses.py`:
```python
class NewResponseModel(BaseModel):
    field1: str
    field2: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "field1": "value",
                "field2": 42
            }
        }
```

## Troubleshooting Development Issues

### MCP Server Connection Issues
- Check if server is running: `ps aux | grep weather_server`
- Verify port availability: `lsof -i :7778`
- Check server logs: `tail -f logs/weather_server_*.log`

### AWS Credentials Problems
- Verify credentials: `aws sts get-caller-identity`
- Check Bedrock access: `aws bedrock list-foundation-models`
- Ensure region is correct: `echo $AWS_DEFAULT_REGION`

### Python Import Errors
- Ensure correct Python version: `python --version`
- Install dependencies: `pip install -r requirements.txt`
- Check PYTHONPATH: `echo $PYTHONPATH`