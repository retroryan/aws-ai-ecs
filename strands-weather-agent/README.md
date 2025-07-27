# AWS Strands Weather Agent

## Overview

This project demonstrates a **fundamental paradigm shift in AI development** using **AWS Strands** - a model-driven development framework that revolutionizes how we build AI agent systems.

### The AI Agent Revolution

Instead of manually parsing LLM output and calling APIs yourself, AWS Strands enables true **model-driven development**:

- **Declare the Structure**: Define your desired output format and available tools
- **Let the Agent Orchestrate**: The agent automatically:
  - Interprets user queries using the LLM
  - Selects and calls appropriate tools
  - Gathers and consolidates results  
  - Produces structured or natural language output as needed

### What is AWS Strands?

AWS Strands provides:
- **Native MCP Support**: Built-in client for Model Context Protocol servers
- **Automatic Tool Discovery**: Tools are found and bound automatically
- **Streaming by Default**: Native streaming and session management
- **Model-Driven Development**: Declare what you want, not how to get it

### Core Simplification

```python
# 1. Set up MCP servers with your tools
from fastmcp import FastMCP

weather_server = FastMCP("Weather Tools")

@weather_server.tool
async def get_weather_forecast(location: str, days: int = 3) -> dict:
    """Get weather forecast for a location."""
    # Implementation here
    return {"forecast": "sunny", "temp": 72}

# 2. Connect to MCP servers and create agent
from strands import Agent
from strands.tools.mcp import MCPClient

mcp_client = MCPClient(lambda: streamablehttp_client("http://localhost:7778/mcp"))
with mcp_client:
    tools = mcp_client.list_tools_sync()
    
    agent = Agent(
        model=bedrock_model,
        tools=tools,
        system_prompt="You are a helpful weather assistant."
    )
```

### This Demo Showcases

- **Any AWS Bedrock Model**: Switch between Claude, Llama, Cohere, and Amazon Nova models via a single environment variable
- **Unified MCP Server**: A single server providing weather forecast, historical, and agricultural data tools
- **Real Weather Data**: Integration with Open-Meteo API for live weather information (no API key required)
- **Multi-turn Conversations**: Context retention across queries for natural dialogue
- **Production Observability**: Optional Langfuse integration for metrics and monitoring (see [docs/LANGFUSE.md](docs/LANGFUSE.md))

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).


## Quick Start

### Prerequisites

✅ **Docker** installed and running  
✅ **AWS CLI** configured with credentials (`aws configure`)  
✅ **AWS Account** with Bedrock access enabled  
✅ **Python 3.12** (for direct Python execution)

**Recommended Model**: Use `BEDROCK_MODEL_ID="us.anthropic.claude-sonnet-4-20250514-v1:0"` for the best performance. Claude Sonnet 4 provides superior tool calling capabilities and structured output generation, especially for agricultural queries.

### Configure Environment
```bash
cp .env.example .env
# Edit .env and set your BEDROCK_MODEL_ID (required)
```

For optional Langfuse observability setup, see [docs/LANGFUSE.md](docs/LANGFUSE.md).

### Local Development: Docker (FastAPI Web Server)

Run the weather agent as a web API server with all services containerized:

```bash
# 1. Configure AWS Bedrock model
./scripts/aws-setup.sh

# 2. Start all services with AWS credentials
./scripts/start_docker.sh
# Optional flags:
#   --debug     Enable debug logging

# 3. Test the services
./scripts/test_docker.sh

# 4. Multi-turn conversation testing
./scripts/multi-turn-test.sh

# 5. Stop services when done
./scripts/stop_docker.sh
```


### Local Development

For detailed instructions on local development, debugging, and testing, see [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md).

Quick start for interactive development:
```bash
# Configure and start services
./scripts/aws-setup.sh
./scripts/start_server.sh

# Run interactive chatbot
cd weather_agent
python chatbot.py --demo

# Stop services
cd .. && ./scripts/stop_server.sh
```


### AWS ECS Deployment

For detailed instructions on deploying to AWS ECS, including infrastructure setup, auto-scaling configuration, and monitoring, see [docs/AWS_DEPLOYMENT.md](docs/AWS_DEPLOYMENT.md).


## Key Features

- **Any Bedrock Model**: Works with Claude, Llama, Cohere, Amazon Nova and other models that support tool calling
- **Unified MCP Server**: Single server providing weather forecast, historical, and agricultural data
- **Multi-turn Conversations**: Context retention across queries
- **Structured Output**: Type-safe responses with Pydantic models
- **Health Monitoring**: Custom health endpoints for all services
- **One-Command Operations**: Scripts handle all complexity
- **AWS Credential Support**: Works with SSO, profiles, IAM roles, and temporary credentials



## Example Queries

The system handles sophisticated weather and agricultural queries:

- **"What are the soil moisture levels at my tree farm in Olympia, Washington?"**
- **"Compare current weather and agricultural conditions between Napa Valley and Sonoma County for grape growing. Which location has better conditions right now?"**
- **"What's the weather like in New York and should I bring an umbrella?"**
- **"Check current conditions in Des Moines, Iowa for corn, soybeans, and wheat - which crop has the best growing conditions right now?"**
- **"Compare weather patterns in Napa Valley for the first week of February, March, and April 2024. Which month had the best conditions for vineyard work?"**

### Multi-Turn Context Examples
- **Turn 1:** "What's the frost risk in Minnesota for tomatoes?"
- **Turn 2:** "How about Wisconsin?" (compares to Minnesota)
- **Turn 3:** "Which state should I choose for my greenhouse operation?" (considers both states)




## Configuration

Copy `.env.example` to `.env` and customize as needed. The most important setting is:
```bash
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
```

For all configuration see [.env.example](.env.example).



### AWS Setup and Configuration

#### Prerequisites

1. **AWS Account Setup**:
   - Create an AWS account if you don't have one
   - Configure AWS CLI: `aws configure`
   - Ensure your IAM user/role has appropriate permissions

2. **Enable AWS Bedrock**:
   - Navigate to AWS Console → Bedrock → Model access
   - Request access to desired models (instant for most models)
   - Wait for access approval (usually immediate)

3. **Required IAM Permissions**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "bedrock:InvokeModelWithResponseStream"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

### Supported AWS Bedrock Models

The system works with any Bedrock model that supports tool/function calling:

#### Claude Models (Anthropic)
- `anthropic.claude-3-5-sonnet-20241022-v2:0` - Best overall performance 
- `anthropic.claude-3-5-sonnet-20240620-v1:0` - Previous version

#### Amazon Nova Models  
- `amazon.nova-pro-v1:0` - High performance
- `amazon.nova-lite-v1:0` - Cost-effective, good for demos 

#### Meta Llama Models
- `meta.llama3-70b-instruct-v1:0` - Open source, excellent performance
- `meta.llama3-1-70b-instruct-v1:0` - Latest Llama 3.1


### Model Selection

Change the `BEDROCK_MODEL_ID` environment variable:

```bash
# For best performance
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"

# For open source
export BEDROCK_MODEL_ID="meta.llama3-70b-instruct-v1:0"
```

## Documentation

- **[Development Guide](docs/DEVELOPMENT_GUIDE.md)** - Local development, testing, debugging, and tooling
- **[Architecture](docs/ARCHITECTURE.md)** - System design and component details
- **[AWS Deployment](docs/AWS_DEPLOYMENT.md)** - Deploy to AWS ECS with auto-scaling
- **[Langfuse Integration](docs/LANGFUSE.md)** - Observability and metrics with Langfuse

## Clean Up

```bash
# Stop local services
./scripts/stop_docker.sh  # Docker
./scripts/stop_server.sh # Python servers

# Remove all Docker resources
docker-compose down -v --remove-orphans
docker system prune -a

# AWS cleanup (in order)
./infra/deploy.sh cleanup-services
./infra/deploy.sh cleanup-base
./infra/deploy.sh cleanup-ecr  # Optional
```


## Resources

- [AWS Strands Documentation](https://github.com/awslabs/multi-agent-orchestrator)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [AWS Bedrock Models](https://docs.aws.amazon.com/bedrock/)
- [Open-Meteo API](https://open-meteo.com/)
