# Agriculture Agent ECS - Weather & Agricultural Data Assistant

A model-agnostic AI agent system demonstrating the power of **agent-driven orchestration**: simply declare tools and output structure, and the agent handles everything else. Built with LangGraph, FastMCP, and AWS Bedrock.

**Architecture**: User → Agent → MCP Servers → Weather APIs

## 🚀 The Paradigm Shift

Instead of manually orchestrating API calls and parsing, just define tools and let the agent handle everything:

```python
# This single function orchestrates the entire workflow
self.agent = create_react_agent(
    self.llm.bind_tools(self.tools),
    self.tools,
    checkpointer=self.checkpointer
)
```

The agent automatically interprets queries, selects tools, gathers results, and produces structured output.

## Quick Start

**Prerequisites**: AWS CLI configured, AWS Bedrock access enabled, Python 3.11+, Docker

### Option 1: Docker (Recommended)
```bash
./scripts/aws-setup.sh         # One-time AWS setup
./scripts/start_docker.sh      # Start all services
./scripts/test_docker.sh       # Test the application
```
FastAPI server runs at http://localhost:7075 (health: `/health`, query: `/query`, docs: `/docs`)

### Option 2: Python Direct
```bash
# Setup and start servers
./scripts/aws-setup.sh && cp bedrock.env .env
./scripts/start_servers.sh

# Run agent
cd weather_agent
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python chatbot.py              # Interactive mode
python chatbot.py --demo       # Demo queries  
python chatbot.py --multi-turn-demo  # Multi-turn demo

# Cleanup
cd .. && ./scripts/stop_servers.sh
```

### AWS Deployment
```bash
./infra/aws-checks.sh     # Verify prerequisites
./infra/deploy.sh all     # Deploy everything
./infra/test_services.sh  # Test deployment
```

## Architecture

```
User → ALB → Weather Agent (FastAPI) → LangGraph → MCP Server → Weather APIs
```

**Components**:
- **Weather Agent** (Port 7075): FastAPI app with `/health`, `/query`, `/docs` endpoints
- **MCP Server** (Port 7071): Provides tools via FastMCP
  - `get_weather_forecast`: 5-day forecasts
  - `get_historical_weather`: Past 7 days data
  - `get_agricultural_conditions`: Agricultural recommendations


### Docker & AWS Credentials

The project automatically handles AWS credentials in Docker using `aws configure export-credentials`, supporting all authentication methods (SSO, profiles, assume-role, MFA). No manual configuration needed.

## Testing & Debugging

```bash
# Testing
./scripts/run_tests.sh            # All tests
./scripts/run_tests.sh --with-docker  # Include Docker tests
python -m pytest tests/test_mcp_servers.py -v  # Specific test

# Logs
docker-compose logs -f weather-agent   # Docker logs
tail -f logs/weather.log              # Python logs

# Debug tips: First request may be slow (model cold start), use LOG_LEVEL=DEBUG for details
```

## AWS Infrastructure

Creates production-ready infrastructure with VPC, ALB, ECS on Fargate, Service Discovery, and CloudWatch logging.

```bash
# Deploy stages
./infra/deploy.sh all              # Everything at once
# Or individually:
./infra/deploy.sh setup-ecr        # ECR repositories  
./infra/deploy.sh build-push       # Build & push images
./infra/deploy.sh base             # Base infrastructure
./infra/deploy.sh services         # ECS services

# Operations
./infra/deploy.sh status           # Check status
./infra/deploy.sh update-services  # Update after code changes
./infra/test_services.sh           # Test deployment

# Monitoring
aws logs tail /ecs/agriculture-main --follow
```

For troubleshooting, see [CLAUDE.md](CLAUDE.md) or run `./infra/status.sh`.

## Configuration

### Environment Variables
```bash
# Required
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0

# Optional  
BEDROCK_REGION=us-east-1
BEDROCK_TEMPERATURE=0
LOG_LEVEL=INFO
```

AWS credentials handled automatically. ECS uses IAM roles.

### Supported Models

- **Amazon Nova**: `amazon.nova-lite-v1:0` (fast), `amazon.nova-pro-v1:0` (balanced)
- **Claude**: `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (best), `us.anthropic.claude-3-haiku-20240307-v1:0` (fast)
- **Others**: Llama 3 70B, Cohere Command R+

Note: Claude models need "us." prefix. Check region availability in AWS console.

## Example Queries

- **Weather**: "What's the weather in Chicago?", "5-day forecast for Seattle"
- **Agriculture**: "Good conditions for planting corn in Iowa?", "Frost risk for tomatoes in Minnesota?"
- **Complex**: "Compare this week vs last week in Denver", "Should I plant my garden this weekend?"

## Extending the System

- **Add Tools**: Create new `@weather_server.tool()` methods in `mcp_servers/weather_server.py`
- **Add Servers**: New FastMCP servers in `mcp_servers/`, update Docker configs
- **Customize Agent**: Modify prompts in `mcp_agent.py`, add transformations

For detailed development info, see [CLAUDE.md](CLAUDE.md).

## Production Considerations

Before production: Add authentication, rate limiting, caching, monitoring, HTTPS, error handling.

## Clean Up

```bash
# Local
docker-compose down -v --remove-orphans

# AWS  
./infra/deploy.sh cleanup-services
./infra/deploy.sh cleanup-base
```

## Resources

- [LangGraph Docs](https://python.langchain.com/docs/langgraph)
- [FastMCP Docs](https://github.com/jlowin/fastmcp)
- [AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Open-Meteo API](https://open-meteo.com/)