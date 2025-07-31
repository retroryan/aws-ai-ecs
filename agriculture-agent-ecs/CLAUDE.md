# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LangGraph + FastMCP Weather Agent Demo that implements a model-agnostic AI agent system. It uses LangGraph for orchestration and FastMCP for distributed tool servers, providing weather and agricultural data through a containerized microservices architecture deployable to AWS ECS.

## Commands

### Local Development
```bash
# Start MCP servers locally
./scripts/start_servers.sh

# Stop MCP servers
./scripts/stop_servers.sh

# Run the interactive chatbot
cd weather_agent && python chatbot.py

# Run main application with different modes
python main.py                # Interactive chatbot (default)
python main.py --demo         # Run demo queries
python main.py --structured   # Structured output mode
python main.py --multi-turn-demo  # Multi-turn conversation demo
```

### Docker Operations
```bash
# Start Docker services
./scripts/start_docker.sh

# Stop Docker services
./scripts/stop_docker.sh

# Test running Docker services
./scripts/test_docker.sh
```

### Testing
```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test modules
cd tests
python -m pytest test_mcp_servers.py -v
python -m pytest test_mcp_agent.py -v
python -m pytest test_coordinates_consolidated.py -v
python -m pytest test_structured_output_demo.py -v
python docker_test.py  # Docker integration tests
```

### AWS Deployment
```bash
cd infra

# Full deployment
./deploy.sh all

# Individual deployment steps
./deploy.sh aws-checks    # Verify AWS setup
./deploy.sh setup-ecr     # Create ECR repositories
./deploy.sh build-push    # Build and push Docker images
./deploy.sh base          # Deploy base infrastructure
./deploy.sh services      # Deploy application services

# Clean up
./deploy.sh cleanup       # Remove all AWS resources
```

## Architecture

### System Flow
```
User Query → Weather Agent (LangGraph) → MCP Server (FastMCP) → External APIs
```

### Core Components

1. **Weather Agent** (`weather_agent/`):
   - `mcp_agent.py`: LangGraph React agent that discovers and calls MCP tools
   - `chatbot.py`: Interactive chat interface with session management
   - `models.py`: Pydantic models for structured weather/agricultural responses
   - Uses conversation memory with checkpointing for multi-turn support

2. **MCP Server** (`mcp_servers/weather_server.py`):
   - Unified FastMCP server running on port 7071
   - Provides tools: `get_weather_forecast`, `get_historical_weather`, `get_agricultural_conditions`
   - HTTP-based with JSON-RPC communication

3. **Infrastructure**:
   - Docker containers with health checks
   - AWS ECS deployment via CloudFormation
   - Service discovery through environment variables

### Key Design Patterns

- **Model-Agnostic**: Works with any AWS Bedrock model via `init_chat_model`
- **Tool Discovery**: Agent dynamically discovers available tools from MCP servers
- **Structured Output**: Optional transformation of tool responses to Pydantic models
- **Session Management**: Conversation state persistence across interactions

## Environment Configuration

Required environment variables (set in `.env`):
- `BEDROCK_MODEL_ID`: AWS Bedrock model ID (e.g., `anthropic.claude-3-5-sonnet-20240620-v1:0`)
- `BEDROCK_REGION`: AWS region (default: us-west-2)
- `MCP_SERVER_URL`: MCP server endpoint (default: http://127.0.0.1:7071/mcp)

## Development Tips

1. **Adding New Tools**: Add methods with `@weather_server.tool()` decorator in `mcp_servers/weather_server.py`
2. **Testing Changes**: Always run `tests/run_all_tests.py` before committing
3. **Docker Development**: Use `docker-compose up` for local containerized testing
4. **Logging**: Check `logs/` directory for server logs and debugging
5. **Model Selection**: Test with different Bedrock models by changing `BEDROCK_MODEL_ID`

## Common Issues

- **Port Conflicts**: Ensure ports 7071 (MCP server) and 7075 (agent) are available
- **AWS Credentials**: Configure AWS CLI or set AWS_PROFILE for Bedrock access
- **Docker Memory**: Allocate sufficient Docker memory for model inference
- **Server Startup**: Wait for "Server ready" message before making requests