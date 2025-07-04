# Debug Logging Guide for AWS Strands Weather Agent

This comprehensive guide combines all debug logging documentation for the AWS Strands Weather Agent, including local development, Docker deployment, and telemetry debugging.

## Table of Contents

1. [Overview](#overview)
2. [Local Development Debugging](#local-development-debugging)
3. [Docker Debug Mode](#docker-debug-mode)
4. [Telemetry Debug Scripts](#telemetry-debug-scripts)
5. [Log Analysis](#log-analysis)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

---

# Overview

Debug logging provides detailed visibility into:
- AWS Strands agent lifecycle and event loops
- MCP client connections and sessions
- Tool discovery, registration, and execution
- Model interactions with AWS Bedrock
- Token usage and performance metrics
- Thread management and async operations
- Langfuse telemetry integration

---

# Local Development Debugging

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

## Log File Locations

Debug logs are written to timestamped files in the `logs/` directory:

- **Chatbot logs**: `logs/chatbot_debug_YYYYMMDD_HHMMSS.log`
- **API server logs**: `logs/weather_api_debug_YYYYMMDD_HHMMSS.log`

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

---

# Docker Debug Mode

## Implementation Details

### 1. Updated `scripts/start_docker.sh`
- Added `--debug` flag support
- Sets `WEATHER_AGENT_DEBUG=true` environment variable when debug is enabled
- Added `--help` option for usage information

### 2. Updated `docker-compose.yml`
- Added `WEATHER_AGENT_DEBUG` environment variable to the weather-agent service
- Defaults to `false` when not explicitly set

### 3. Updated `weather_agent/main.py`
- Now checks both command-line argument and `WEATHER_AGENT_DEBUG` environment variable
- Enables debug logging if either is set

### 4. Created `scripts/test_docker_debug.sh`
- Tests all Docker services with debug mode
- Verifies debug logging is enabled
- Shows how to access debug logs in containers

## Usage

### Start with Debug Mode
```bash
./scripts/start_docker.sh --debug
```

This will:
- Set the `WEATHER_AGENT_DEBUG=true` environment variable
- Enable debug logging in the containerized Weather Agent API
- Write logs to files inside the container's `logs/` directory

### Test Debug Mode
```bash
./scripts/test_docker_debug.sh
```

### Access Debug Logs
```bash
# List log files in container
docker exec weather-agent-app ls -la logs/

# View latest debug log
docker exec weather-agent-app tail -f logs/weather_api_debug_*.log

# Copy logs to host
docker cp weather-agent-app:/app/logs/ ./docker-logs/
```

### Stop Services
```bash
./scripts/stop_docker.sh
```

## Debug Log Location

When running in Docker with debug mode:
- Logs are written to `/app/logs/` inside the container
- File format: `weather_api_debug_YYYYMMDD_HHMMSS.log`
- Contains detailed AWS Strands debug information

## Environment Variable

The `WEATHER_AGENT_DEBUG` environment variable controls debug logging:
- Set to `true` to enable debug logging
- Set to `false` or omit to disable debug logging
- Can be set in `.env` file for persistent configuration

---

# Telemetry Debug Scripts

The `strands-metrics-guide/` directory contains several debug and testing scripts for the Langfuse integration:

## 1. `debug_telemetry.py`
**Purpose**: Comprehensive configuration checker

Checks:
- Environment variables
- Import dependencies
- Langfuse connectivity

```bash
python strands-metrics-guide/debug_telemetry.py
```

Output example:
```
🔧 Langfuse Telemetry Debug Tool
==================================================
🔍 Environment Check:
  ✅ LANGFUSE_PUBLIC_KEY: pk-lf-5639...
  ✅ LANGFUSE_SECRET_KEY: sk-lf-42c8...
  ✅ LANGFUSE_HOST: http://loc...
  ✅ BEDROCK_MODEL_ID: anthropic....
  ✅ BEDROCK_REGION: us-west-2

🔍 Import Check:
  ✅ StrandsTelemetry importable
  ✅ LangfuseTelemetry importable

🔍 Connectivity Check:
  ✅ Langfuse reachable: {'status': 'OK', 'version': '3.78.1'}

✅ All checks passed! Telemetry should work.
```

## 2. `test_simple_telemetry.py`
**Purpose**: Quick test of telemetry functionality

Features:
- Runs a single weather query
- Shows trace session ID
- Minimal setup required

```bash
python strands-metrics-guide/test_simple_telemetry.py
```

## 3. `run_and_validate_metrics.py`
**Purpose**: Full integration test with validation

Features:
- Checks all prerequisites
- Runs multiple demo queries
- Validates traces via Langfuse API
- Detailed reporting

```bash
# Basic run
python strands-metrics-guide/run_and_validate_metrics.py

# Verbose mode
python strands-metrics-guide/run_and_validate_metrics.py --verbose

# Skip prerequisite checks
python strands-metrics-guide/run_and_validate_metrics.py --skip-checks
```

## 4. `inspect_traces.py`
**Purpose**: Analyze recent traces

Features:
- Fetches traces from Langfuse
- Groups by session
- Calculates token usage
- Configurable time window

```bash
# Last hour
python strands-metrics-guide/inspect_traces.py

# Last 24 hours
python strands-metrics-guide/inspect_traces.py --hours 24

# Last week
python strands-metrics-guide/inspect_traces.py --hours 168
```

## 5. `monitor_performance.py`
**Purpose**: Measure telemetry overhead

Features:
- Benchmarks with/without telemetry
- Statistical analysis
- Performance impact report

```bash
python strands-metrics-guide/monitor_performance.py
```

Output example:
```
🔍 Telemetry Performance Impact Analysis
==================================================

⏱️  Without telemetry...

⏱️  With telemetry...

📊 Results:
Without telemetry: 2.543s ± 0.234s
With telemetry: 2.612s ± 0.251s

Overhead: 0.069s (2.7%)
```

---

# Log Analysis

## Finding Specific Information

### 1. Tool execution details:
```bash
grep "tool_name=" logs/chatbot_debug_*.log
```

### 2. MCP session information:
```bash
grep "Session:" logs/chatbot_debug_*.log
```

### 3. Error tracking:
```bash
grep -E "(ERROR|WARN|Exception)" logs/chatbot_debug_*.log
```

### 4. Performance analysis:
```bash
grep -E "(latency|duration|tokens)" logs/chatbot_debug_*.log
```

## Common Debugging Scenarios

### 1. MCP Server Connection Issues
Look for:
```
DEBUG | strands.tools.mcp.mcp_client | transport connection established
INFO | mcp_agent | ✅ forecast server: 1 tools available
```

### 2. Tool Execution Problems
Search for:
```
DEBUG | strands.tools.executor | tool_name=<tool_name> | executing tool
ERROR | strands.tools.executor | tool execution failed
```

### 3. Model/Token Issues
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

---

# Best Practices

## Development
1. **Always use `--debug` during development** to catch issues early
2. **Check debug logs first** when troubleshooting any issue
3. **Use grep to filter logs** for specific components or operations
4. **Monitor log file sizes** as debug logs can grow quickly

## Production
1. **Disable debug logging in production** to avoid performance impact and large log files
2. **Use INFO level logging** for production monitoring
3. **Implement log rotation** for long-running services
4. **Be aware that debug logs may contain query content and responses**

## Docker Deployment
1. **Use environment variables** for debug configuration
2. **Copy logs to host** for detailed analysis
3. **Clean up old logs** inside containers to save space
4. **Use docker logs for quick checks**, debug files for detailed analysis

## Telemetry Debugging
1. **Always run debug_telemetry.py first** to check configuration
2. **Use test_simple_telemetry.py** for quick verification
3. **Run full validation** before production deployment
4. **Monitor performance impact** with benchmarking tools

---

# Troubleshooting

## Common Issues and Solutions

### No Debug Logs Appearing

1. **Check debug flag is set**:
   ```bash
   # For local development
   python chatbot.py --debug
   
   # For Docker
   ./scripts/start_docker.sh --debug
   ```

2. **Verify logs directory exists**:
   ```bash
   mkdir -p logs
   ```

3. **Check file permissions**:
   ```bash
   ls -la logs/
   ```

### Cannot Find Specific Debug Information

1. **Use broader grep patterns**:
   ```bash
   # Instead of exact matches
   grep -i "forecast" logs/*.log
   
   # Use context lines
   grep -C 5 "error" logs/*.log
   ```

2. **Check all log files**:
   ```bash
   # Combine and search all logs
   cat logs/*.log | grep "pattern"
   ```

### Docker Logs Not Accessible

1. **Ensure container is running**:
   ```bash
   docker ps | grep weather-agent
   ```

2. **Check container logs directory**:
   ```bash
   docker exec weather-agent-app ls -la logs/
   ```

3. **Copy logs to host**:
   ```bash
   docker cp weather-agent-app:/app/logs ./container-logs
   ```

### Telemetry Not Working

1. **Run debug checker**:
   ```bash
   python strands-metrics-guide/debug_telemetry.py
   ```

2. **Verify environment variables**:
   ```bash
   env | grep LANGFUSE
   ```

3. **Check connectivity**:
   ```bash
   curl -X GET "$LANGFUSE_HOST/api/public/health"
   ```

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

For comprehensive observability options, see the [LANGFUSE_INTEGRATION.md](./LANGFUSE_INTEGRATION.md) guide.