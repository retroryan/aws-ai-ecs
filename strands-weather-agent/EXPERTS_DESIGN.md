# Spring Agriculture Experts MCP Server Integration

## Overview

This document details the integration of the Spring Agriculture Experts MCP server into the Strands Weather Agent system. The experts server provides specialized agricultural expertise through the Model Context Protocol (MCP), extending the weather agent's capabilities with domain-specific knowledge.

The experts server is implemented as an **optional component** that can be enabled when needed, using Docker Compose profiles for local development.

## Architecture

### MCP Server Details
- **Service Name**: experts-server
- **Docker Image**: spring-agriculture-experts:dev
- **Port**: 7781
- **Protocol**: HTTP-based MCP (Model Context Protocol)
- **Health Endpoint**: /health

### Integration Points

The experts server integrates with the weather agent system at multiple levels:

1. **Docker Compose** - Local development environment
2. **Weather Agent** - MCP client configuration
3. **ECS Deployment** - Production cloud deployment

## Implementation Details

### 1. Docker Compose Configuration

Added the experts server as an optional service in `docker-compose.yml` using Docker Compose profiles:

```yaml
experts-server:
  image: spring-agriculture-experts:dev
  container_name: mcp-experts-server
  profiles:
    - experts
  ports:
    - "7781:7781"
  environment:
    - LOG_LEVEL=${LOG_LEVEL:-INFO}
    - MCP_PORT=7781
  networks:
    - weather-network
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:7781/health"]
    interval: 30s
    timeout: 3s
    retries: 3
    start_period: 5s
```

The weather-agent service was updated to:
- Include `MCP_EXPERTS_URL=http://experts-server:8010/mcp/` environment variable
- The experts-server dependency was removed from `depends_on` to make it optional

### 2. Weather Agent MCP Client Configuration

Modified `weather_agent/mcp_agent.py` to handle the optional experts server:

```python
servers = {
    "forecast": os.getenv("MCP_FORECAST_URL", "http://localhost:7778/mcp"),
    "historical": os.getenv("MCP_HISTORICAL_URL", "http://localhost:7779/mcp"),
    "agricultural": os.getenv("MCP_AGRICULTURAL_URL", "http://localhost:7780/mcp")
}

# Only add experts server if URL is provided (optional)
experts_url = os.getenv("MCP_EXPERTS_URL")
if experts_url:
    servers["experts"] = experts_url
```

The connectivity test dynamically determines server names based on configuration.

### 3. Testing Infrastructure

#### Docker Testing (`scripts/test_docker.sh`)
- Added conditional health check for experts server on port 7781
- Only checks experts server if it's running (detects via docker ps)
- Shows message if experts server is not running with instructions to enable it
- Added experts server URL to the service URLs output only when running

#### Local Development (`scripts/start_servers.sh`)
- Added note that experts server runs as Docker container
- Included experts endpoint in the server endpoints list

#### Docker Start Script (`scripts/start_docker.sh`)
- Added support for `add-experts` parameter
- Without parameter: starts only core services (forecast, historical, agricultural)
- With `add-experts` parameter: includes the experts server using Docker Compose profile
- Provides user feedback about which mode is being used

### 4. ECS Deployment Configuration

Updated `infra/services.cfn` CloudFormation template:

#### Parameters
- Added `ExpertsImageTag` parameter (default: "dev")

#### Resources
- **ExpertsLogGroup**: CloudWatch log group for the experts server
- **ExpertsServiceDiscovery**: Service discovery configuration for internal DNS
- **ExpertsTaskDefinition**: ECS task definition with 256 CPU, 512 memory
- **ExpertsService**: ECS service configuration with Fargate launch type

#### Main Service Updates
- Added `MCP_EXPERTS_URL` environment variable pointing to `http://experts.strands-weather.local:7781/mcp/`
- Added `ExpertsService` to the MainService `DependsOn` list

#### Outputs
- Added `ExpertsServiceName` to CloudFormation outputs

## Tool Discovery

The weather agent automatically discovers tools from the experts server through the MCP protocol. No additional configuration is needed - the AWS Strands framework handles:

1. **Automatic Tool Discovery**: On agent initialization, all MCP clients are queried for available tools
2. **Tool Registration**: Discovered tools are automatically registered with the agent
3. **Dynamic Updates**: The agent can discover new tools if the experts server is updated

## Network Architecture

### Local Development (Docker)
- All services communicate through the `weather-network` Docker network
- Services reference each other by container name (e.g., `experts-server`)

### ECS Deployment
- Services use AWS Cloud Map for service discovery
- Internal DNS names follow pattern: `{service}.strands-weather.local`
- All services run in private subnets with ALB for external access

## Environment Variables

### Required for Weather Agent
- `MCP_EXPERTS_URL`: URL of the experts MCP server
  - Docker: `http://experts-server:7781/mcp/`
  - ECS: `http://experts.strands-weather.local:7781/mcp/`
  - Local: `http://localhost:7781/mcp`

### Experts Server Configuration
- `LOG_LEVEL`: Logging verbosity (default: INFO)
- `MCP_PORT`: Port to listen on (default: 7781)
- `MCP_HOST`: Host to bind to (default: 0.0.0.0 in ECS)

## Health Monitoring

### Health Check Implementation
The experts server must implement a `/health` endpoint that returns HTTP 200 when healthy. This is used by:
- Docker Compose health checks
- Local testing scripts
- ECS service registration (through service discovery)

### Important Note on ECS Health Checks
MCP servers in ECS do NOT have traditional ECS health checks configured. This is because:
1. MCP protocol uses JSON-RPC which requires session management
2. The `/mcp/` endpoint isn't suitable for simple health checks
3. Service discovery handles registration immediately on startup
4. The main service has retry logic for MCP connections

## Optional Server Behavior

### When Experts Server is NOT Running
- The weather agent operates normally with forecast, historical, and agricultural servers
- No errors occur - the agent gracefully handles the absence of the experts server
- MCP_EXPERTS_URL environment variable can remain set without issues
- Tool discovery only includes tools from available servers

### When Experts Server IS Running  
- Additional agricultural expertise tools become available
- The agent automatically discovers and can use expert-specific tools
- All existing functionality remains unchanged
- Enhanced responses for agricultural queries with expert knowledge

## Usage Examples

### Testing Connectivity
```bash
# Test health endpoint
curl http://localhost:7781/health

# Test MCP endpoint (requires proper headers)
curl -X POST http://localhost:7781/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Running Locally with Docker
```bash
# Start services WITHOUT experts server (default)
./scripts/start_docker.sh

# Start services WITH experts server
./scripts/start_docker.sh add-experts

# Test all services
./scripts/test_docker.sh

# Stop all services
./scripts/stop_docker.sh
```

### Running Experts Server Standalone
```bash
# Run the experts server independently
docker run -p 7781:7781 spring-agriculture-experts:dev
```

## Future Considerations

1. **Scaling**: The experts server is configured with 1 instance but can be scaled horizontally in ECS
2. **Resource Allocation**: Currently set to 256 CPU / 512 MB memory - adjust based on load
3. **Model Updates**: The experts server image tag is parameterized for easy updates
4. **Monitoring**: CloudWatch logs are configured for debugging and monitoring

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure the experts server is running and healthy
2. **Tool Discovery Fails**: Check MCP server logs for errors
3. **ECS Deployment Issues**: Verify the Docker image is accessible to ECS
4. **Network Issues**: Ensure security groups allow traffic on port 7781

### Debug Commands

```bash
# Check Docker logs
docker logs mcp-experts-server

# Check ECS logs
aws logs tail /ecs/strands-weather-agent-experts --follow

# Test from within Docker network
docker exec weather-agent-app curl http://experts-server:7781/health
```