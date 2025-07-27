# MCP Server Consolidation Complete

## Summary
Successfully consolidated three separate MCP servers (forecast, historical, agricultural) into a single unified weather server following the pattern from strands-weather-agent.

## Changes Made

### 1. Created Unified Weather Server
- **File**: `mcp_servers/weather_server.py`
- **Port**: 7071 (same as old forecast server)
- **Tools**: 
  - `get_weather_forecast`
  - `get_historical_weather`
  - `get_agricultural_conditions`
- **Health Endpoint**: `/health` for Docker health checks

### 2. Updated Agent Configuration
- **File**: `weather_agent/mcp_agent.py`
- **Change**: Now uses single `MCP_SERVER_URL` environment variable
- **Default**: `http://127.0.0.1:7071/mcp`

### 3. Updated Docker Configuration
- **docker-compose.yml**: Single `weather-server` service instead of three
- **docker/Dockerfile.weather**: New unified Dockerfile
- **docker/Dockerfile.main**: Updated to use `MCP_SERVER_URL`

### 4. Updated Scripts
- **scripts/start_servers.sh**: Starts single server
- **scripts/stop_servers.sh**: Stops single server (with migration support)
- **scripts/test_docker.sh**: Tests single server health endpoint

### 5. Updated Documentation
- **CLAUDE.md**: All references updated to single server architecture
- Environment variable documentation updated

### 6. Removed Old Files
- Deleted `mcp_servers/forecast_server.py`
- Deleted `mcp_servers/historical_server.py`
- Deleted `mcp_servers/agricultural_server.py`
- Deleted `docker/Dockerfile.forecast`
- Deleted `docker/Dockerfile.historical`
- Deleted `docker/Dockerfile.agricultural`

## Architecture Comparison

### Before (Three Servers)
```
weather-agent → forecast-server:7071    → get_weather_forecast
             → historical-server:7072   → get_historical_weather
             → agricultural-server:7073 → get_agricultural_conditions
```

### After (Single Server)
```
weather-agent → weather-server:7071 → get_weather_forecast
                                   → get_historical_weather
                                   → get_agricultural_conditions
```

## Benefits
1. **Simplified Architecture**: One server to manage instead of three
2. **Reduced Resource Usage**: Single process, single port
3. **Easier Deployment**: One container in Docker/ECS
4. **Simplified Configuration**: Single URL to configure
5. **Better Maintainability**: All weather tools in one place

## Testing
```bash
# Local testing
./scripts/start_servers.sh
curl http://localhost:7071/health

# Docker testing
./scripts/start_docker.sh
./scripts/test_docker.sh
```