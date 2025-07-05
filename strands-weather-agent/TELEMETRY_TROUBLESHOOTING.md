# Telemetry Troubleshooting Guide

This guide helps you troubleshoot and fix telemetry integration issues with Langfuse.

## Common Issues and Solutions

### 1. Telemetry Not Working in Docker

**Problem**: Telemetry is enabled but no traces appear in Langfuse when running in Docker.

**Root Cause**: The weather agent and Langfuse are running in different Docker networks and cannot communicate.

**Solution**: Use the provided docker-compose override file to connect both services:

```bash
# Option 1: Use the helper script (recommended)
./scripts/start_docker_with_langfuse.sh

# Option 2: Manual docker-compose
docker compose -f docker-compose.yml -f docker-compose.langfuse.yml up -d
```

### 2. Network Connection Issues

**Problem**: "Cannot connect to Langfuse" errors in logs.

**Possible Causes**:
1. Langfuse is not running
2. Services are on different Docker networks
3. Incorrect LANGFUSE_HOST configuration

**Debugging Steps**:

```bash
# Check if Langfuse is running
docker ps | grep langfuse

# Check if Langfuse network exists
docker network ls | grep langfuse

# Test connectivity from weather-agent container
docker exec weather-agent-app curl -f http://langfuse-web:3000/api/public/health
```

### 3. Configuration Issues

**Problem**: Telemetry is enabled but not working.

**Check these environment variables**:

```bash
# In your .env file:
ENABLE_TELEMETRY=true
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=http://langfuse-web:3000  # For Docker
# or
LANGFUSE_HOST=https://cloud.langfuse.com  # For cloud
```

**Verify configuration is loaded**:

```python
# Check in weather_agent/langfuse_telemetry.py logs
logger.info(f"Langfuse telemetry initialized successfully")
logger.info(f"  Host: {self.host}")
```

### 4. Missing Traces

**Problem**: Agent runs but no traces appear in Langfuse.

**Debugging Steps**:

1. **Check if telemetry is actually enabled**:
   ```bash
   # Look for this log message when the agent starts
   docker compose logs weather-agent | grep "Telemetry enabled"
   ```

2. **Verify OTEL configuration**:
   ```bash
   # Check environment variables inside container
   docker exec weather-agent-app env | grep OTEL
   ```

3. **Force flush telemetry**:
   The agent already calls `force_flush_telemetry()` after each query, but you can add more logging:
   ```python
   # In mcp_agent.py, after query execution
   if self.telemetry_enabled:
       logger.info("Flushing telemetry...")
       force_flush_telemetry()
   ```

### 5. Authentication Errors

**Problem**: 401 or 403 errors when sending telemetry.

**Solution**: Verify your Langfuse credentials:

```bash
# Test credentials directly
curl -u "PUBLIC_KEY:SECRET_KEY" https://cloud.langfuse.com/api/public/health
```

## Docker Network Architecture

When running with Docker, the services need to communicate:

```
┌─────────────────────┐     ┌─────────────────────┐
│   Weather Agent     │     │     Langfuse        │
│   Network:          │     │   Network:          │
│   - weather-network │ ←→  │   - langfuse_       │
│   - langfuse_       │     │     langfuse-network│
│     langfuse-network│     │                     │
└─────────────────────┘     └─────────────────────┘
```

The weather agent must be on BOTH networks to:
1. Communicate with MCP servers (weather-network)
2. Send telemetry to Langfuse (langfuse_langfuse-network)

## Testing Telemetry

### 1. Run Validation Script

```bash
cd strands-metrics-guide
python run_and_validate_metrics.py
```

This script will:
- Check connectivity to all services
- Run a test query with telemetry
- Verify traces were created in Langfuse
- Show detailed trace attributes

### 2. Manual Testing

```bash
# Start services with telemetry
./scripts/start_docker_with_langfuse.sh

# Run a test query
curl -X POST http://localhost:7777/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}'

# Check Langfuse UI
open http://localhost:3000
```

### 3. Debug Logging

Enable debug logging to see telemetry details:

```bash
# In .env file
WEATHER_AGENT_DEBUG=true
OTEL_LOG_LEVEL=debug

# Restart services
docker compose restart weather-agent
```

## Environment Variable Reference

| Variable | Description | Docker Value | Local Value |
|----------|-------------|--------------|-------------|
| ENABLE_TELEMETRY | Enable/disable telemetry | true | true |
| LANGFUSE_PUBLIC_KEY | Your public key | (from Langfuse UI) | (same) |
| LANGFUSE_SECRET_KEY | Your secret key | (from Langfuse UI) | (same) |
| LANGFUSE_HOST | Langfuse API endpoint | http://langfuse-web:3000 | http://localhost:3000 |
| LANGFUSE_HOST_DOCKER | Docker-specific host | http://langfuse-web:3000 | (not used) |

## Quick Fixes

### Fix 1: Telemetry not working in Docker

```bash
# Use the Langfuse integration script
./scripts/start_docker_with_langfuse.sh
```

### Fix 2: Telemetry not working locally

```bash
# Ensure MCP servers are running
./scripts/start_servers.sh

# Set environment variables
export ENABLE_TELEMETRY=true
export LANGFUSE_PUBLIC_KEY=your_key
export LANGFUSE_SECRET_KEY=your_secret

# Run the agent
python weather_agent/main.py
```

### Fix 3: Reset and retry

```bash
# Stop everything
./scripts/stop_docker.sh

# Clear Docker volumes
docker compose down -v

# Start fresh with Langfuse
./scripts/start_docker_with_langfuse.sh
```

## Additional Resources

- [Langfuse OpenTelemetry Docs](https://langfuse.com/docs/integrations/opentelemetry)
- [AWS Strands Telemetry Guide](strands-guide/STRANDS_DEFINITIVE_GUIDE.md)
- [Docker Networking Guide](https://docs.docker.com/network/)