# Docker Debug Mode Implementation

This document summarizes the debug logging implementation for Docker Compose.

## What Was Added

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