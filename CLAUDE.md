# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository demonstrates AI-powered applications running on AWS ECS with Bedrock integration. It contains multiple subprojects showcasing different approaches to building intelligent, distributed AI systems using MCP (Model Context Protocol) servers, LangGraph, and AWS Strands.

## Common Development Commands

### Testing and Linting
```bash
# Python projects - run from project root
python -m pytest tests/ -v
ruff check .
ruff format .

# Run comprehensive test suites
./scripts/run-tests.sh  # Available in most projects
```

### Docker Operations
```bash
# Start services locally
./scripts/start_docker.sh

# Stop services
./scripts/stop_docker.sh

# Test Docker services
./scripts/test_docker.sh
```

### AWS Deployment
```bash
# Deploy to AWS ECS
cd infra
./deploy.sh all          # Full deployment
./deploy.sh build-push   # Build and push images
./deploy.sh services     # Deploy services only
./deploy.sh status       # Check deployment status
./deploy.sh cleanup-all  # Remove all resources
```

## Architecture Patterns

### MCP (Model Context Protocol) Architecture
All projects use MCP servers as distributed microservices:
- **Tool Servers**: Expose capabilities via JSON-RPC over HTTP
- **Agent Clients**: Discover and use tools dynamically
- **Service Discovery**: Environment variables for server URLs
- **Health Checks**: `/health` endpoints for Docker, no ECS health checks for MCP servers

### Project-Specific Patterns

#### agent-ecs-template
- Direct boto3 Bedrock integration
- Client-server Flask architecture
- Manual orchestration of API calls

#### agriculture-agent-ecs
- LangGraph for stateful orchestration
- Checkpointer system for conversation persistence
- React agent pattern with tool binding

#### strands-weather-agent
- AWS Strands for model-driven development
- Declarative agent configuration
- Automatic tool discovery and orchestration

## Key Development Guidelines

### AWS Credentials in Docker
```bash
# Always use this pattern for AWS credentials
eval $(aws configure export-credentials --format env 2>/dev/null)
export AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN:-}
```

### MCP Client Pattern
```python
# Create per-request MCP clients
def create_mcp_client() -> MCPClient:
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:7778/mcp")
    return MCPClient(lambda: streamablehttp_client(server_url))

# Use in request handlers
async def process_query(request):
    with create_mcp_client() as mcp_client:
        tools = mcp_client.list_tools_sync()
        # Process with tools
```

### Environment Variables
- `BEDROCK_MODEL_ID`: AWS Bedrock model identifier
- `BEDROCK_REGION`: AWS region (default: us-east-1)
- `MCP_SERVER_URL`: MCP server endpoint
- `SERVER_URL`: For client-server communication

### Port Assignments
- 7071: MCP server (agriculture-agent-ecs)
- 7075: Weather agent API (agriculture-agent-ecs)
- 7777: Weather agent API (strands-weather-agent)
- 7778: MCP server (strands-weather-agent)
- 8080: Client service (agent-ecs-template)
- 8081: Server service (agent-ecs-template)

## Testing Best Practices

1. **Run tests before deployment**: Always execute `./scripts/run-tests.sh` or `pytest`
2. **Test Docker locally**: Use `docker-compose up` before AWS deployment
3. **Check health endpoints**: Verify `/health` returns 200 after deployment
4. **Monitor logs**: Check CloudWatch logs for service issues

## Common Issues and Solutions

1. **Port Conflicts**: Ensure assigned ports are available
2. **AWS Credentials**: Run `aws configure` or set AWS_PROFILE
3. **ECR Authentication**: Run `./infra/setup-ecr.sh` if push fails
4. **Model Access**: Verify Bedrock model access with `./scripts/aws-setup.sh`
5. **MCP Connection**: Ensure MCP servers are running before starting agents

## Infrastructure Patterns

### CloudFormation Stacks
- **Base Stack**: VPC, subnets, ALB, ECS cluster, IAM roles
- **Services Stack**: Task definitions, ECS services, service discovery

### ECS Configuration
- Service Connect for internal discovery
- Application health checks (not shell commands)
- Proper IAM roles for Bedrock access
- Resource allocation tuned per service

### Deployment Workflow
1. Setup ECR repositories
2. Build and push Docker images
3. Deploy base infrastructure
4. Deploy application services
5. Verify with test scripts