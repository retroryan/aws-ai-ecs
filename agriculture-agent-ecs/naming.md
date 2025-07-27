# Infrastructure Naming Alignment Issues

## Summary
The infrastructure was adopted from the Spring AI MCP Agent project and contains several naming inconsistencies that need to be addressed for the Agriculture Agent project.

## Key Findings

### 1. status.sh Script
- **Line 3**: Contains header comment "Spring AI MCP Agent Infrastructure Status Script"
- **Lines 74-95**: References to Spring AI MCP Agent services:
  - Uses `ClientServiceName` and `ServerServiceName` outputs (not present in agriculture agent)
  - Default log groups: `/ecs/spring-ai-mcp-agent-client` and `/ecs/spring-ai-mcp-agent-server`
- **Lines 106-113**: References "Client" and "Server" services which don't exist in agriculture agent
- **Line 157**: References `mcp-server.${BASE_STACK_NAME}:8081` which is not applicable
- **Lines 148-156**: Health check endpoints for Spring AI actuator endpoints

### 2. CloudFormation Templates (Correctly Named)
The CloudFormation templates are correctly aligned:
- **base.cfn**: All resources properly prefixed with "agriculture-agent"
- **services.cfn**: All services correctly named (main, forecast, historical, agricultural)

### 3. Common.sh (Correctly Named)
- Properly defines agriculture agent defaults and repository names
- ECR repositories correctly prefixed with "agriculture-agent"

## Required Changes

### status.sh Updates Needed:
1. Update header comment to "Agriculture Agent Infrastructure Status Script"
2. Replace client/server service references with agriculture agent services:
   - Main Agent Service
   - Forecast Service  
   - Historical Service
   - Agricultural Service
3. Update default log groups to match services.cfn:
   - `/ecs/agriculture-agent-main`
   - `/ecs/agriculture-agent-forecast`
   - `/ecs/agriculture-agent-historical`
   - `/ecs/agriculture-agent-agricultural`
4. Update health check endpoint from `/actuator/health` to `/health`
5. Remove Spring Boot actuator references
6. Update API test example from employee skills query to weather/agriculture query
7. Update service discovery references to use agriculture.local namespace

## Action Plan Based on Answers

Based on the provided answers, here are the specific changes to implement in status.sh:

### 1. Service Architecture Updates
- Display all four services individually (main, forecast, historical, agricultural)
- Remove client/server terminology and references

### 2. Health Check Updates  
- Only check the main agent health via ALB endpoint (/health on port 7075)
- Remove internal health checks for MCP servers
- Remove references to Spring Boot actuator endpoints

### 3. Log Error Checking
- Only check error logs for the main agent service
- Remove error checking for the MCP server services

### 4. API Example Updates
Use examples from test_services.sh:
```bash
# Example 1: Weather query
curl -X POST "http://$LB_DNS/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "What is the weather like in Chicago?"}'

# Example 2: Agricultural query  
curl -X POST "http://$LB_DNS/query" \
    -H "Content-Type: application/json" \
    -d '{"query": "Are conditions good for planting corn in Iowa?"}'
```

### 5. Port References
- Main Agent: 7075 (exposed via ALB)
- Weather Server: 7071 (internal, unified)

## Implementation Summary

The status.sh script needs to be rewritten to:
1. Remove all Spring AI MCP Agent references
2. Display status for all four agriculture agent services
3. Only perform health checks on the main agent via ALB
4. Only check logs for errors in the main agent
5. Provide agriculture-specific API examples
6. Use the correct ports for each service