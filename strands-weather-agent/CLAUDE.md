# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Strands Weather Agent - A demonstration of model-driven AI development using AWS Strands framework, showcasing AI agents that can discover and use tools via Model Context Protocol (MCP) servers.

## Key Commands

### Development
```bash
# Configure AWS Bedrock access
./scripts/aws-setup.sh

# Start MCP servers (background)
./scripts/start_server.sh

# Run interactive chatbot
cd weather_agent
python chatbot.py --demo             # Demo mode
python chatbot.py --multi-turn-demo  # Multi-turn demo
python chatbot.py --debug            # Debug mode

# Stop servers
cd .. && ./scripts/stop_server.sh
```

### Docker Deployment
```bash
# Start all services with AWS credentials
./scripts/start_docker.sh [--debug]

# Test Docker services
./scripts/test_docker.sh

# Multi-turn conversation test
./scripts/multi-turn-test.sh

# Stop services
./scripts/stop_docker.sh
```

### Testing
```bash
# Run comprehensive test suite
./scripts/run-tests.sh

# Run specific tests
python tests/test_mcp_agent_strands.py
python -m pytest tests/test_mcp_servers.py -v
```

### AWS ECS Deployment
```bash
# Deploy infrastructure and services
cd infra
python deploy.py all

# Deploy updates only
python deploy.py deploy-services

# Check deployment status
python status.py

# Cleanup (in order)
python deploy.py cleanup-services
python deploy.py cleanup-base
python deploy.py cleanup-ecr
```

## Architecture

### Core Pattern: Model-Driven Development
1. **MCP Server** exposes tools via FastMCP (weather forecast, historical data, agricultural info)
2. **AWS Strands Agent** automatically discovers tools from the unified MCP server
3. **Agent** interprets queries, selects tools, and orchestrates responses
4. **FastAPI** provides REST interface with health endpoints

### Key Components
- **weather_agent/mcp_agent.py**: Main AWS Strands agent implementation
- **mcp_servers/weather_server.py**: Unified MCP server with all weather tools
- **weather_agent/main.py**: FastAPI application entry point
- **weather_agent/chatbot.py**: Interactive CLI interface

### MCP Client Pattern (CRITICAL - DO NOT CHANGE)
```python
# Per-request MCP client creation
def create_mcp_client() -> MCPClient:
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:7778/mcp")
    return MCPClient(lambda: streamablehttp_client(server_url))

# Usage in request handlers
async def process_query(request):
    with create_mcp_client() as mcp_client:
        tools = mcp_client.list_tools_sync()
        agent = MCPWeatherAgent(tools=tools)
        response = await agent.query(request.query)
    return response
```

### Docker Configuration (DO NOT SIMPLIFY)
The Docker setup handles AWS credential complexities:
- `start_docker.sh` exports AWS credentials via `aws configure export-credentials`
- Works with SSO, temporary credentials, IAM roles
- `docker-compose.yml` + `docker-compose.langfuse.yml` for optional telemetry
- MCP servers have `/health` endpoints for Docker health checks only
- ECS task definitions have NO health checks for MCP servers

## Environment Configuration

Required:
- `BEDROCK_MODEL_ID`: AWS Bedrock model (e.g., `us.anthropic.claude-sonnet-4-20250514-v1:0`)
- `BEDROCK_REGION`: AWS region (default: us-east-1)

Optional:
- `WEATHER_AGENT_DEBUG`: Enable debug logging (true/false)
- `LANGFUSE_*`: Telemetry configuration (see docs/LANGFUSE.md)

## Testing Approach

1. **Unit Tests**: Test individual components (MCP servers, agent logic)
2. **Integration Tests**: Test full system with real MCP servers
3. **Structured Output Tests**: Validate Pydantic models and responses
4. **Multi-turn Tests**: Verify conversation context retention

Always run `./scripts/run-tests.sh` before major changes.

## Important Patterns

### AWS Credentials in Docker
```bash
# ALWAYS use this pattern in Docker scripts
eval $(aws configure export-credentials --format env 2>/dev/null)
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}
```

### MCP Server Health Checks
- Docker Compose: Use custom `/health` endpoints
- ECS: NO health checks on MCP task definitions
- Main service: Has proper health check with retry logic

### Debug Logging
```bash
# Enable via flag or environment
python main.py --debug
export WEATHER_AGENT_DEBUG=true
```
Debug logs saved to `logs/weather_agent_debug_YYYYMMDD_HHMMSS.log`

## Common Issues

1. **MCP Server Connection**: Ensure servers are running (`./scripts/start_server.sh`)
2. **AWS Credentials**: Use scripts that handle credential export automatically
3. **Port Conflicts**: Weather agent (7777), MCP server (7778)
4. **Model Access**: Verify Bedrock model access with `./scripts/aws-setup.sh`