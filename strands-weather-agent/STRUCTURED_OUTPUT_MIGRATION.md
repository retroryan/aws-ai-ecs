# Structured Output Migration Summary

## Overview
This document summarizes the migration from separate `/query` and `/query/structured` endpoints to a single unified `/query` endpoint that always returns structured output.

## Key Changes

### 1. API Endpoint Consolidation
- **Removed**: `/query` endpoint that returned simple text responses
- **Renamed**: `/query/structured` → `/query`
- **Result**: Single endpoint that always returns `WeatherQueryResponse` objects

### 2. Response Format
The `/query` endpoint now returns:
```json
{
  "query_type": "current",
  "locations": [{
    "name": "Chicago, Illinois, US",
    "latitude": 41.8781,
    "longitude": -87.6298
  }],
  "weather_data": {
    "current_temperature": 22.5,
    "conditions": "Partly cloudy"
  },
  "summary": "Current weather in Chicago: 22.5°C, partly cloudy...",
  "session_id": "abc123...",
  "session_new": true,
  "conversation_turn": 1,
  "metrics": {...}
}
```

### 3. Code Changes

#### API (main.py)
- Removed `QueryResponse` model
- Removed old `/query` endpoint implementation
- Renamed `/query/structured` to `/query`
- Updated response model to always use `WeatherQueryResponse`

#### Agent (mcp_agent.py)
- Removed `async def query(...) -> str` method
- Renamed `query_structured` to `query`
- Now only has one query method that returns structured output

#### Scripts Updated
- `test_docker.sh`: Changed from `.response` to `.summary`
- `multi-turn-test.sh`: Changed from `.response` to `.summary`
- `infra/deploy.py`: Fixed query parameter from "question" to "query"
- `infra/status.py`: Fixed query parameter from "question" to "query"
- `infra/demos/multi-turn-demo.py`: Updated to use `.summary` field
- `infra/demos/demo_telemetry.py`: Updated to use `.summary` field
- `infra/tests/test_services.py`: Updated to use `.summary` field

#### Tests Updated
- All test files now use `agent.query()` instead of `agent.query_structured()`
- Tests expecting string responses now extract the `.summary` field

### 4. Benefits
- **Simplified API**: Single endpoint for all queries
- **Consistent Output**: Always returns structured, validated data
- **Better Type Safety**: All responses use Pydantic models
- **Richer Information**: Includes locations, weather data, and metadata
- **Session Support**: Built-in session management in all responses

### 5. Migration Guide for Clients
If you're updating client code:

**Before:**
```python
# Simple query
response = requests.post("/query", json={"query": "weather in Chicago"})
text = response.json()["response"]

# Structured query
response = requests.post("/query/structured", json={"query": "weather in Chicago"})
data = response.json()  # Full structured response
```

**After:**
```python
# All queries now return structured data
response = requests.post("/query", json={"query": "weather in Chicago"})
data = response.json()
text = data["summary"]  # For simple text summary
# Full structured data also available in data
```