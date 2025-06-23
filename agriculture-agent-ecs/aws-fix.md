# Agriculture Agent Services - AWS ECS Deployment Investigation

## CURRENT STATE (2025-06-23)

### Status Summary
- **CloudFormation Stack**: CREATE_IN_PROGRESS (stuck since 2025-06-22 20:19 CST)
- **Main Service**: 0/1 tasks running - failing to connect to MCP services
- **MCP Services**: All running 1/1 tasks
- **Root Cause**: Docker images contain old code with localhost binding

### Fixes Already Applied to Code
1. ✅ **Dependencies Fixed**: Added `fastapi` and `uvicorn` to requirements.txt
2. ✅ **Host Binding Fixed**: Changed all MCP servers from `127.0.0.1` to `0.0.0.0`
3. ✅ **Environment Variables**: Added support for MCP_*_URL env vars in mcp_agent.py

### Problem
The deployed Docker images (tag: f8576dc-20250622-214534) were built BEFORE the host binding fix was applied. The MCP servers in the running containers are still binding to 127.0.0.1, making them inaccessible to the main service.

### NEXT STEPS REQUIRED
Execute these commands in order:

```bash
# 1. Clean up all old ECR images to ensure fresh builds
./infra/cleanup-ecr-images.sh

# 2. Force rebuild all Docker images without cache
FORCE_BUILD=true ./infra/build-push.sh

# 3. Deploy the new images to ECS
./infra/deploy.sh services
```

After deployment, the CloudFormation stack should complete successfully as the main service will be able to connect to the MCP services.

---

## Issue Description
The agriculture-agent-services deployment to AWS ECS appears to be stuck. This document tracks the investigation and resolution steps.

## Investigation Plan

### Phase 1: Current State Assessment
1. **CloudFormation Stack Analysis**
   - Check stack status and events
   - Identify any failed resources
   - Review stack parameters
   
2. **ECS Service Status**
   - Verify service deployment status
   - Check task health and running count
   - Review service events
   
3. **Container Health**
   - Check task logs in CloudWatch
   - Verify health check endpoints
   - Review container exit codes

### Phase 2: Infrastructure Analysis
1. **Networking**
   - Security group rules
   - Target group health
   - ALB configuration
   
2. **IAM Permissions**
   - Task execution role
   - Task role permissions
   - ECR access
   
3. **Resource Constraints**
   - CPU/Memory allocation
   - Container instance capacity

### Phase 3: Application Debugging
1. **Application Logs**
   - Server startup issues
   - MCP server connectivity
   - Environment variable configuration
   
2. **Dependencies**
   - External service connectivity
   - AWS Bedrock access
   - Port configurations

## Investigation Progress

### Initial Setup
- **Time**: Starting investigation
- **Status**: Created investigation plan and todo list
- **Next Step**: Check CloudFormation stack status

---
## Findings

### CloudFormation Stack Status (20:30 CST)
- **agriculture-agent-base**: CREATE_COMPLETE ✓
- **agriculture-agent-services**: CREATE_IN_PROGRESS (stuck since 20:19 CST)
- **Issue**: MainService is stuck in CREATE_IN_PROGRESS while other services completed

### ECS Service Analysis
- **Services Status**:
  - AgriculturalService: CREATE_COMPLETE ✓
  - ForecastService: CREATE_COMPLETE ✓  
  - HistoricalService: CREATE_COMPLETE ✓
  - MainService: CREATE_IN_PROGRESS ❌

- **MainService Details**:
  - Status: ACTIVE
  - Desired Count: 1
  - Running Count: 0
  - Pending Count: 1
  - **Pattern**: Tasks are starting but then being deregistered repeatedly
  - **Indication**: Tasks are failing ALB health checks

### Task Cycling Pattern
The service events show a repeating pattern:
1. Task starts
2. Task registers with target group
3. Task is deregistered from target group
4. Task drains connections
5. New task starts (cycle repeats)

This indicates the tasks are not passing health checks.

### Container Exit Analysis
- **Exit Code**: 1 (Error)
- **Stop Reason**: Essential container in task exited
- **Tasks Affected**: All MainService tasks are crashing immediately

### CloudWatch Logs Analysis (20:35 CST)
**Root Cause Identified**: Missing Python dependencies

```
ModuleNotFoundError: No module named 'fastapi'
```

The container is failing to start because FastAPI (and likely other dependencies) are not installed in the Docker image. This is causing the container to exit immediately with code 1.

### Dockerfile Analysis
The `docker/Dockerfile.main` expects:
- FastAPI (imported in app.py)
- uvicorn (used to run the app)

However, **requirements.txt is missing these critical dependencies**:
- ❌ fastapi
- ❌ uvicorn

This explains why the container fails with `ModuleNotFoundError: No module named 'fastapi'`

## Resolution Steps

### 1. Fix Missing Dependencies
Add the missing dependencies to requirements.txt:
- fastapi
- uvicorn

### 2. Rebuild and Push Docker Image
After fixing requirements.txt:
1. Rebuild the main Docker image
2. Push to ECR
3. Force a new deployment

### 3. CloudFormation Stack Recovery
The stack should automatically complete once the service stabilizes.

## Implementation Progress

### Step 1: Fixed requirements.txt (20:40 CST) ✓
Added missing dependencies:
```
fastapi>=0.110.0
uvicorn>=0.27.0
```

### Step 2: Rebuild and Push Docker Image (20:50 CST) ✓
User rebuilt and deployed the images.

### Step 3: Current Service Status Check (20:52 CST)

#### CloudFormation Stack
- **Status**: Still CREATE_IN_PROGRESS
- **Issue**: MainService preventing stack completion

#### ECS Services Status
| Service | Status | Running/Desired | Health |
|---------|--------|-----------------|--------|
| agriculture-agent-forecast | ACTIVE | 1/1 | ✓ |
| agriculture-agent-historical | ACTIVE | 1/1 | ✓ |
| agriculture-agent-agricultural | ACTIVE | 1/1 | ✓ |
| agriculture-agent-main | ACTIVE | 0/1 | ❌ |

#### New Error in Main Service
The dependency issue is fixed (FastAPI loads), but now facing a new error:

```
ERROR:__main__:Failed to initialize agent: unhandled errors in a TaskGroup (1 sub-exception)
httpx.ConnectError: All connection attempts failed
```

### Root Cause Analysis
The main service cannot connect to the MCP services. This is likely because:

1. **Service Discovery Issue**: The main service is trying to connect to MCP services but doesn't know their addresses
2. **Environment Variables**: The MCP service URLs are not properly configured

Looking at the Dockerfile.main, it expects these environment variables:
- `MCP_FORECAST_URL`
- `MCP_HISTORICAL_URL`  
- `MCP_AGRICULTURAL_URL`

These need to point to the private IPs of the MCP services (e.g., http://10.0.1.202:7071 for forecast).

### CloudFormation Template Analysis
Checking `infra/services.cfn`, the MainTaskDefinition is **missing the MCP service URL environment variables**. It only has:
- BEDROCK_MODEL_ID
- BEDROCK_REGION
- BEDROCK_TEMPERATURE

But it's missing:
- MCP_FORECAST_URL
- MCP_HISTORICAL_URL
- MCP_AGRICULTURAL_URL

## Next Steps

### Option 1: Quick Fix via ECS Console
1. Update the task definition in ECS console
2. Add the missing environment variables with service URLs
3. Force a new deployment

### Option 2: Fix CloudFormation Template
1. Update services.cfn to include MCP URLs using service discovery
2. Update the stack
3. Let CloudFormation handle the deployment

### Option 3: Use AWS Service Discovery
Implement proper service discovery so services can find each other dynamically.

**Recommendation**: For immediate resolution, use Option 1 (ECS Console) to unblock the stack, then implement Option 2 or 3 for a permanent solution.

## Solution Found

After further investigation, the issue is clear:

1. **MCP services are healthy**: They're using Service Discovery (not ALB) and have reached steady state
2. **MainService can't connect**: Missing environment variables for MCP service URLs
3. **Service Discovery is configured**: Services are accessible via:
   - `http://forecast.agriculture.local:7071`
   - `http://historical.agriculture.local:7072`
   - `http://agricultural.agriculture.local:7073`

## ACTUAL Root Cause Found!

The CloudFormation template is actually correct - it already has the MCP URLs configured with the `/mcp` path:
- `MCP_FORECAST_URL: http://forecast.agriculture.local:7071/mcp`
- `MCP_HISTORICAL_URL: http://historical.agriculture.local:7072/mcp`
- `MCP_AGRICULTURAL_URL: http://agricultural.agriculture.local:7073/mcp`

**The real issue**: The MCP servers are binding to `127.0.0.1` (localhost) instead of `0.0.0.0`, making them inaccessible from other containers!

### Fix Required

Update all MCP server files to bind to `0.0.0.0` instead of `127.0.0.1`:

### Changes Made

1. **forecast_server.py** (line 86):
   ```python
   # Changed from: host="127.0.0.1"
   server.run(transport="streamable-http", host="0.0.0.0", port=7071, path="/mcp")
   ```

2. **historical_server.py** (line 108):
   ```python
   # Changed from: host="127.0.0.1"
   server.run(transport="streamable-http", host="0.0.0.0", port=7072, path="/mcp")
   ```

3. **agricultural_server.py** (line 85):
   ```python
   # Changed from: host="127.0.0.1"
   server.run(transport="streamable-http", host="0.0.0.0", port=7073, path="/mcp")
   ```

### Additional Consideration

The reference project (`spring-ai-agent-ecs`) doesn't use the `/mcp` path suffix. However, our FastMCP servers are configured with `path="/mcp"`, and the CloudFormation template correctly includes this in the URLs. This should work as long as both sides match.

## Summary

The agriculture-agent-services deployment was stuck due to two issues:

1. **Initial Issue**: Missing `fastapi` and `uvicorn` dependencies in requirements.txt
2. **Current Issue**: MCP servers binding to localhost (127.0.0.1) instead of all interfaces (0.0.0.0)

With these fixes applied, the services should be able to communicate properly and the CloudFormation stack should complete successfully.

## Post-Deployment Status Check (21:25 CST)

### Current Status
- **CloudFormation Stack**: Still CREATE_IN_PROGRESS
- **ECS Services**:
  - MCP services (forecast, historical, agricultural): ✅ Running 1/1
  - Main service: ❌ Running 0/1

### Persistent Issue
The main service is still failing with connection errors despite the host binding fix:

```
httpx.ConnectError: All connection attempts failed
```

### Analysis
The MCP servers are running but the main service still can't connect. This suggests:

1. **Network connectivity issue**: The services might not be able to reach each other through service discovery
2. **Timing issue**: The main service might be trying to connect before service discovery DNS is ready
3. **Security group issue**: Port 7071-7073 might be blocked

### Root Cause Confirmed!

The issue is now clear from the forecast server logs:
```
INFO     Starting MCP server 'openmeteo-forecast' with transport 'streamable-http' on http://127.0.0.1:7071/mcp
INFO:     Uvicorn running on http://127.0.0.1:7071 (Press CTRL+C to quit)
```

**The servers are STILL binding to 127.0.0.1!** This means:
1. ✅ Security groups are configured correctly (ports 7071-7073 open)
2. ❌ The Docker images were not rebuilt with the updated code
3. The old images with `host="127.0.0.1"` are still being used

### Resolution
The code changes were made but the Docker images need to be rebuilt and pushed again. The deployment used the old images that still have the localhost binding.

## Clean Build Instructions

I've created utilities to ensure a clean rebuild:

### 1. Clean up old ECR images (Optional but recommended)
```bash
./infra/cleanup-ecr-images.sh
```

### 2. Force rebuild without cache
```bash
FORCE_BUILD=true ./infra/build-push.sh
```

### 3. Deploy the services
```bash
./infra/deploy.sh services
```

### What was done:
1. **Created `cleanup-ecr-images.sh`**: This script deletes all images from the ECR repositories to ensure no old images are used
2. **Modified `build-push.sh`**: Added support for `FORCE_BUILD=true` environment variable that adds `--no-cache` to docker build commands
3. **Verified**: The `deploy.sh build-push` command simply calls `build-push.sh`, it doesn't force a rebuild by default

### Notes:
- The current deployment is using old Docker images where MCP servers still bind to 127.0.0.1
- Security groups and service discovery are configured correctly
- Once rebuilt with the 0.0.0.0 binding, the services should connect properly
