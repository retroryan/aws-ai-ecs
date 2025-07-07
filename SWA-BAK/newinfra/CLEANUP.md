# Debugging Code Added for Coordinate Issue

This document tracks all debugging code added to investigate the coordinate formatting issue. All items listed here should be removed once the issue is resolved.

## Files Modified for Debugging

### 0. infra/deploy.py (NEW - added by --debug flag feature)
**Added:** --debug flag support to deployment script
**Location:** Multiple locations
**Changes:**
- Lines 451-455: Added --debug argument to parser
- Lines 139-155: Modified deploy_services() to accept debug_mode parameter and add STRANDS_DEBUG_TOOL_CALLS to cloud.env
- Line 179: Modified update_services() signature to accept debug_mode
- Line 369: Modified deploy_all() signature to accept debug_mode
- Lines 480, 484, 486: Updated calls to pass args.debug
- Lines 416, 429: Added documentation for --debug flag
**Cleanup:** 
- Remove --debug argument from parser
- Remove debug_mode parameter from all methods
- Remove logic that adds STRANDS_DEBUG_TOOL_CALLS to cloud.env

### 0.5. scripts/start_docker.sh (NEW - added by --debug flag feature)
**Added:** STRANDS_DEBUG_TOOL_CALLS export when --debug flag is used
**Location:** Lines 96, 98, 140
**Changes:**
- Line 96: Added `export STRANDS_DEBUG_TOOL_CALLS=true`
- Line 98: Added echo message for tool call debugging
- Line 140: Added info about [COORDINATE_DEBUG] prefix
**Cleanup:** Remove STRANDS_DEBUG_TOOL_CALLS export and related messages

### 1. weather_agent/mcp_agent.py
**Added:** Tool call argument logging in stream_async method
**Location:** Lines 389-405, in the event handling for "current_tool_use"
**Changes:**
- Added environment variable check for STRANDS_DEBUG_TOOL_CALLS
- Added logger.debug with [COORDINATE_DEBUG] prefix
- Logs tool_name, input arguments, and timestamp
**Cleanup:** Remove lines 393-400 (the debug logging block)

### 2. weather_agent/main.py
**Added:** Debug endpoint to check if debugging is enabled
**Location:** Lines 484-495, new endpoint `/debug/tool-calls`
**Purpose:** Provide guidance on finding debug logs in CloudWatch
**Cleanup:** Remove entire endpoint (lines 484-495)

### 3. Environment Variables Added
**Added:** `STRANDS_DEBUG_TOOL_CALLS=true`
**Purpose:** Enable verbose tool call logging
**Where to add:** .env, cloud.env, and ECS task definitions
**Cleanup:** Remove from .env, cloud.env, and deployment configs

## Debug Logging Format

All debug logs use the prefix `[COORDINATE_DEBUG]` for easy filtering:
```python
logger.debug("[COORDINATE_DEBUG] Tool call: %s", json.dumps(tool_args))
```

## How to Find Debug Code

Search for these markers in the codebase:
1. `COORDINATE_DEBUG` - All debug log statements
2. `TODO: Remove debug` - Inline comments marking debug code
3. `/debug/` - Debug API endpoints

## Cleanup Commands

After resolving the issue, run:
```bash
# Find all debug code
grep -r "COORDINATE_DEBUG" .
grep -r "TODO: Remove debug" .

# Remove debug environment variable
sed -i '' '/STRANDS_DEBUG_TOOL_CALLS/d' .env
sed -i '' '/STRANDS_DEBUG_TOOL_CALLS/d' cloud.env
```

## Debug Scripts and Tools Added

### newinfra/ Directory
This entire directory was created for debugging:
- `newinfra-troubleshooting.md` - Investigation documentation
- `debug_test_suite.py` - Automated test suite
- `compare_environments.py` - Environment comparison tool
- `run_debug_tests.sh` - Test runner script
- `toggle_debug.sh` - Enable/disable debug mode
- `README.md` - Documentation for debug tools
- `CLEANUP.md` - This file

**Cleanup:** The entire newinfra/ directory can be removed after issue resolution

## How to Enable/Disable Debug Mode

### Enable Debug Mode:

#### Option 1: Using --debug flag (NEW - Recommended)
```bash
# For AWS deployment
python3 infra/deploy.py update-services --debug

# For Docker
./scripts/start_docker.sh --debug
```

#### Option 2: Using toggle script (Original method)
```bash
./newinfra/toggle_debug.sh enable
python3 infra/deploy.py update-services  # Redeploy with debug
```

### Disable Debug Mode:
```bash
# Remove STRANDS_DEBUG_TOOL_CALLS from cloud.env manually or:
./newinfra/toggle_debug.sh disable
python3 infra/deploy.py update-services  # Redeploy without debug
```

### Check Debug Status:
```bash
./newinfra/toggle_debug.sh status
```

## Testing After Cleanup

After removing debug code:
1. Run local tests to ensure nothing broke
2. Deploy to Docker and test
3. Deploy to AWS and verify fix remains

## Debug Features to Keep (Maybe)

Consider keeping these improvements after cleanup:
1. Structured logging for tool calls (without verbose details)
2. Request ID tracking for better observability
3. Performance metrics for tool execution
4. The test suite framework (adapted for regular testing)