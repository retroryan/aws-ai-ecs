# AWS Deployment Troubleshooting - Coordinate Formatting Error

## Issue Summary

After implementing Langfuse cloud telemetry integration, the deployed AWS ECS service exhibits a consistent formatting error when the agent attempts to use location coordinates. This issue:
- **Does NOT occur** in local development
- **Does NOT occur** in Docker (as reported by user)
- **ONLY occurs** in AWS ECS deployment
- **Occurs regardless** of whether Langfuse telemetry is enabled or disabled

## Error Pattern

The agent exhibits the following behavior:
1. Receives a weather query (e.g., "Weather in Seattle")
2. Recognizes the location and attempts to use coordinates "for a faster response"
3. Encounters a formatting error when passing coordinates to the MCP tool
4. Outputs: "I apologize for the formatting error. Let me try again..."
5. Retries using only the location name (no coordinates)
6. Successfully completes the request

## Timeline of Investigation

### 1. Initial Discovery
- User reported truncated responses in test script
- Fixed test script to show full responses (removed [:200] truncation)
- Discovered consistent "formatting error" pattern in responses

### 2. Environment Comparison
- Confirmed same Bedrock model in both environments: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- `.env` and `cloud.env` both use the same model configuration
- Deployed CloudFormation stack uses the same model

### 3. Langfuse Investigation
- Initially suspected Langfuse telemetry was interfering
- Disabled telemetry and redeployed: **Issue persisted**
- Re-enabled telemetry as it was ruled out as the cause
- Confirmed Langfuse configuration is correct in ECS task definition

### 4. Testing Patterns

#### Test Results Summary:
```
Query Type                           | Local | Docker | AWS ECS
------------------------------------|-------|--------|--------
Simple city name (Boston)           | ✅    | ✅     | ❌*
Known city (Seattle)                | ✅    | ✅     | ❌*
Explicit coordinates                | ✅    | ✅     | ❌*
City with coordinates in query      | ✅    | ✅     | ❌*
Agricultural queries                | ✅    | ✅     | Timeout

* = Works after retry without coordinates
```

### 5. Key Findings

1. **Consistent Error Pattern**: Every query that might trigger coordinate usage fails first
2. **Agent Behavior**: The agent says "Since I know [City]'s coordinates, I'll use them for a faster response"
3. **Retry Success**: After the formatting error, the agent retries with just the location name and succeeds
4. **No Python Errors**: No tracebacks or exceptions in CloudWatch logs
5. **MCP Servers Healthy**: All three MCP servers (forecast, historical, agricultural) report as connected
6. **Timeout Issue**: Agricultural queries consistently timeout (30-second limit exceeded)

### 6. Technical Details

#### Expected MCP Tool Format (from forecast_server.py):
```python
# The server accepts either:
# 1. location: string (city name)
# 2. latitude: float, longitude: float (separate parameters)
# 3. Both (coordinates take priority)
```

#### Agent's Attempted Pattern:
The agent appears to be trying to pass coordinates but in a format that causes an error. The exact format being sent is unknown as it's not logged.

## Hypotheses

1. **JSON Serialization Issue**: The coordinates might be serialized differently in the AWS environment
2. **Float Precision**: Coordinate float values might be formatted differently (e.g., scientific notation)
3. **Strands Version**: Possible version mismatch between local and deployed environments
4. **Environment Variable**: Some environment-specific configuration affecting tool argument formatting
5. **Network/Proxy**: AWS ECS networking might be modifying the request format

## What We've Ruled Out

- ❌ **Langfuse Telemetry**: Issue occurs with telemetry disabled
- ❌ **Bedrock Model**: Same model used everywhere
- ❌ **MCP Server Issues**: Servers are healthy and connected
- ❌ **Python Exceptions**: No errors in logs, just the agent's retry behavior
- ❌ **CloudFormation Config**: Parameters match expected values

## Next Steps

1. Create comprehensive debug test suite
2. Add detailed logging to capture exact tool call arguments
3. Compare behavior between Docker and AWS ECS
4. Instrument the agent to log tool call details before sending
5. Check Strands library version in deployed container

## Commands Used During Investigation

```bash
# Check deployment status
python3 infra/deploy.py status

# Test services
python3 infra/test_services.py

# Check CloudWatch logs
aws logs filter-log-events \
  --log-group-name /ecs/strands-weather-agent-main \
  --start-time $(echo $(($(date +%s) - 300)))000 \
  --filter-pattern "ERROR" \
  --region us-east-1

# Check task definition
aws ecs describe-task-definition \
  --task-definition strands-weather-agent-main \
  --region us-east-1

# Deploy without telemetry
python3 infra/deploy.py services --disable-telemetry

# Direct API test
curl -X POST http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}'
```

## Test Scripts Created

1. **debug_deployment.py**: Basic connectivity and query tests
2. **test_tool_calls.py**: MCP server status and tool format testing
3. **test_coordinate_issue.py**: Specific tests for coordinate formatting
4. **test_mcp_direct.py**: Direct MCP integration testing

## Error Examples

### Typical Error Response:
```
I'll check the current weather conditions and forecast for Seattle, Washington. 
Since I know Seattle's coordinates, I'll use them for a faster response.
I apologize for the formatting error. Let me try again with the location name:
[Successful response follows]
```

### Agricultural Query Timeout:
```
Query: 'Are conditions good for planting corn in Iowa?'
Error: HTTPConnectionPool(host='strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com', port=80): 
Read timed out. (read timeout=30)
```