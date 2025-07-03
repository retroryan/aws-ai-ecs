# Debug Logging Guide for AWS Strands Weather Agent

This guide explains how to enable and use debug logging for the AWS Strands Weather Agent to gain deeper insights into agent operations, tool executions, and MCP server interactions.

## Overview

Debug logging provides detailed visibility into:
- AWS Strands agent lifecycle and event loops
- MCP client connections and sessions
- Tool discovery, registration, and execution
- Model interactions with AWS Bedrock
- Token usage and performance metrics
- Thread management and async operations

## Enabling Debug Logging

### For the Chatbot CLI

Run the chatbot with the `--debug` flag:

```bash
cd weather_agent
python chatbot.py --debug
```

Or combine with demo mode:

```bash
python chatbot.py --demo --debug
```

### For the API Server

Start the API server with the `--debug` flag:

```bash
python weather_agent/main.py --debug
```

Or with custom port:

```bash
python weather_agent/main.py --debug --port 8080
```

### For Docker Compose

Start all services with debug logging enabled:

```bash
./scripts/start_docker.sh --debug
```

This will:
- Set the `WEATHER_AGENT_DEBUG=true` environment variable
- Enable debug logging in the containerized Weather Agent API
- Write logs to files inside the container's `logs/` directory

Test the debug mode with:

```bash
./scripts/test_docker_debug.sh
```

## Log File Locations

Debug logs are written to timestamped files in the `logs/` directory:

- **Chatbot logs**: `logs/chatbot_debug_YYYYMMDD_HHMMSS.log`
- **API server logs**: `logs/weather_api_debug_YYYYMMDD_HHMMSS.log`

### Accessing Docker Container Logs

When running with Docker, debug logs are stored inside the container. To access them:

```bash
# List debug log files
docker exec weather-agent-app ls -la logs/

# View the latest debug log
docker exec weather-agent-app tail -100 logs/weather_api_debug_*.log

# Copy logs to host machine
docker cp weather-agent-app:/app/logs/weather_api_debug_*.log ./
```

## What Gets Logged

### Console Output (INFO Level)
- Basic operation status
- MCP server connectivity
- High-level request processing

### File Output (DEBUG Level)
- Detailed Strands module operations
- MCP client session management
- Tool execution parameters and results
- Event loop processing details
- Token usage and metrics
- Thread and async operation details

## Example Debug Messages

### Tool Operations
```
DEBUG | strands.tools.registry | tool_name=<get_weather_forecast> | registering tool
DEBUG | strands.tools.executor | tool_name=<get_weather_forecast> | executing tool with parameters: {"latitude": 37.7749, "longitude": -122.4194}
```

### MCP Client Sessions
```
DEBUG | strands.tools.mcp.mcp_client | [Thread: MainThread, Session: 218d8aa8-944a-4ad3-b240-f6a5fa9fafd5] initializing MCPClient connection
DEBUG | strands.tools.mcp.mcp_client | [Thread: Thread-1, Session: 218d8aa8-944a-4ad3-b240-f6a5fa9fafd5] session initialized successfully
```

### Event Loop Processing
```
DEBUG | strands.event_loop.message_processor | message_index=<3> | replaced content with context message
DEBUG | strands.agent.conversation_manager | window_size=<4>, message_count=<20> | skipping context reduction
```

### Model Interactions
```
DEBUG | strands.models.bedrock | config=<{'model_id': 'anthropic.claude-3-5-sonnet-20241022-v2:0', 'temperature': 0.0}> | initializing
DEBUG | strands.models.bedrock | region=<us-west-2> | bedrock client created
```

## Analyzing Debug Logs

### Finding Specific Information

1. **Tool execution details**:
   ```bash
   grep "tool_name=" logs/chatbot_debug_*.log
   ```

2. **MCP session information**:
   ```bash
   grep "Session:" logs/chatbot_debug_*.log
   ```

3. **Error tracking**:
   ```bash
   grep -E "(ERROR|WARN|Exception)" logs/chatbot_debug_*.log
   ```

4. **Performance analysis**:
   ```bash
   grep -E "(latency|duration|tokens)" logs/chatbot_debug_*.log
   ```

### Common Debugging Scenarios

#### 1. MCP Server Connection Issues
Look for:
```
DEBUG | strands.tools.mcp.mcp_client | transport connection established
INFO | mcp_agent | ✅ forecast server: 1 tools available
```

#### 2. Tool Execution Problems
Search for:
```
DEBUG | strands.tools.executor | tool_name=<tool_name> | executing tool
ERROR | strands.tools.executor | tool execution failed
```

#### 3. Model/Token Issues
Check for:
```
WARNING | strands.models.bedrock | bedrock threw context window overflow error
DEBUG | strands.event_loop | message_index=<N> | replaced content with context message
```

## Demo Script

Run the included demo to see debug logging in action:

```bash
python demo_debug_logging.py
```

This will:
1. Enable debug logging
2. Run sample queries
3. Display key debug messages
4. Show log file location and size

## Best Practices

1. **Development**: Always use `--debug` during development to catch issues early
2. **Production**: Disable debug logging in production to avoid performance impact and large log files
3. **Log Rotation**: Implement log rotation for long-running services
4. **Sensitive Data**: Be aware that debug logs may contain query content and responses

## Configuration Details

The debug logging configuration:
- Creates separate handlers for console (INFO) and file (DEBUG)
- Enables debug for all Strands modules
- Includes detailed formatting with timestamps, module names, and line numbers
- Supports UTF-8 encoding for international content

## Integration with Monitoring

Debug logs can be integrated with monitoring tools:
- CloudWatch Logs (AWS deployment)
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- Datadog

See the [COMPLETE_METRICS_GUIDE.md](../strands-official/COMPLETE_METRICS_GUIDE.md) for comprehensive observability options.