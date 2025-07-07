# Debug Infrastructure for Coordinate Formatting Issue

## 🚀 Quick Start - Redeploy with Debug and Test

### Step 1: Enable Debug Mode and Redeploy to AWS
```bash
# Redeploy with debug logging enabled
python3 infra/deploy.py update-services --debug
```

This command will:
- Add `STRANDS_DEBUG_TOOL_CALLS=true` to cloud.env
- Redeploy the services with debug logging enabled
- Enable [COORDINATE_DEBUG] prefixed logs in CloudWatch

### Step 2: Run the Debug Tests
```bash
# Run complete test suite against both Docker and AWS
./newinfra/run_debug_tests.sh both
```

This will:
- Automatically discover your AWS deployment URL
- Test both Docker and AWS environments
- Compare results and highlight differences
- Save everything in `debug_results/TIMESTAMP/`
- Open a summary report automatically (on macOS)

### Step 3: Check Debug Logs in CloudWatch
```bash
# View tool call debug logs from AWS (macOS)
aws logs filter-log-events \
  --log-group-name /ecs/strands-weather-agent-main \
  --filter-pattern '[COORDINATE_DEBUG]' \
  --region us-east-1 \
  --start-time $(date -u -v-5M +%s000)

# For Linux, use: --start-time $(date -u -d '5 minutes ago' +%s000)
```

## 📋 What We've Built

We've created a comprehensive debugging infrastructure to diagnose why the AWS-deployed agent fails when trying to use location coordinates, while the same code works perfectly in local and Docker environments.

## Issue Summary

The AWS-deployed agent exhibits a consistent pattern where it:
1. Attempts to use location coordinates "for a faster response"
2. Encounters a formatting error
3. Retries with just the location name (successfully)

This happens regardless of Langfuse telemetry being enabled/disabled.

## Debug Infrastructure Created

### 1. **Comprehensive Test Suite** (`debug_test_suite.py`)
- Tests multiple query formats and coordinate patterns
- Captures detailed metrics and error patterns
- Saves results as JSON for comparison
- Identifies formatting errors, retries, and timeouts

### 2. **Environment Comparison Tool** (`compare_environments.py`)
- Compares test results between Docker and AWS
- Highlights differences in behavior
- Groups issues by type (formatting errors, timeouts, etc.)
- Generates actionable insights

### 3. **Enhanced Agent Logging**
- Added tool call debugging to capture exact arguments
- Uses `[COORDINATE_DEBUG]` prefix for easy filtering
- Controlled by `STRANDS_DEBUG_TOOL_CALLS` environment variable
- Logs tool name, input arguments, and timestamp

### 4. **Debug Control Scripts**
- `toggle_debug.sh` - Enable/disable debug mode easily
- `run_debug_tests.sh` - Run tests against different environments
- Automatic comparison when testing both environments

### 5. **Deployment --debug Flag** (NEW)
- `python3 infra/deploy.py update-services --debug` - Redeploy with debug enabled
- `./scripts/start_docker.sh --debug` - Start Docker with debug enabled
- Automatically sets STRANDS_DEBUG_TOOL_CALLS=true

## Files in this Directory

### 📄 newinfra-troubleshooting.md
Comprehensive documentation of:
- Issue description and symptoms
- Investigation timeline
- Test results
- Hypotheses and findings
- Commands used during debugging

### 🧪 debug_test_suite.py
Automated test suite that:
- Runs identical tests against different environments
- Tests various coordinate formats
- Measures response times
- Detects formatting errors and retry patterns
- Saves results to JSON for comparison

### 🔍 compare_environments.py
Comparison tool that:
- Loads test results from two environments
- Identifies differences in behavior
- Highlights formatting errors unique to each environment
- Generates a summary report

### 🚀 run_debug_tests.sh
Complete test runner that:
- Automatically discovers AWS ALB URL from CloudFormation
- Tests both Docker and AWS environments
- Compares results automatically
- Creates timestamped output directories
- Generates summary reports

### 🔧 toggle_debug.sh
Debug mode control script:
- Enable/disable debug mode in env files
- Check current debug status
- Works with both .env and cloud.env

### 🧹 CLEANUP.md
Documentation of all debug code added:
- Lists every file modified for debugging
- Specific line numbers and changes
- Instructions for removing debug code
- Tracks --debug flag implementation

## Test Results Location

All results are saved in timestamped directories:
```
debug_results/
├── 20241206_143052/
│   ├── docker/
│   │   ├── results.json          # Test results
│   │   └── test_output.log       # Console output
│   ├── aws/
│   │   ├── results.json          # Test results
│   │   ├── test_output.log       # Console output
│   │   └── .url                  # AWS URL used
│   ├── comparison_report.txt     # Human-readable comparison
│   ├── comparison.json           # Structured comparison
│   └── summary.md               # Executive summary
```

## What to Look For

### In Test Results:
1. **Formatting Errors**: Look for queries that fail in AWS but not Docker
2. **Retry Patterns**: Agent says "Let me try again" after initial failure
3. **Coordinate Mentions**: Agent tries to use coordinates "for faster response"
4. **Response Times**: Significant differences between environments

### In CloudWatch Logs:
1. **Tool Call Arguments**: Exact JSON being sent to MCP servers
2. **Coordinate Format**: How latitude/longitude are formatted
3. **Error Messages**: Any exceptions or validation errors
4. **Timing**: When the error occurs in the tool call sequence

## Key Findings So Far

1. **Consistent Pattern**: Every query that might use coordinates fails first in AWS
2. **Retry Success**: After formatting error, retry with location name works
3. **No Python Errors**: No tracebacks or exceptions in logs
4. **Telemetry Not Related**: Issue occurs with Langfuse disabled
5. **Model Same**: Using same Bedrock model everywhere

## What the Tests Check

1. **Health and Connectivity**: Basic API health
2. **MCP Server Status**: All three servers connected
3. **Coordinate Formats**: Various ways of specifying locations
4. **Known Problem Queries**: Seattle, Boston, Chicago
5. **Response Timing**: Performance differences
6. **Agricultural Timeout**: Complex query handling

## Key Patterns to Look For

The comparison tool will highlight:
- ❌ **Formatting errors** unique to AWS
- 🔄 **Retry behaviors** in responses
- ⏱️ **Response time** differences
- 📍 **Coordinate mentions** in responses

## Next Investigation Steps

1. **Capture Tool Arguments**: With debug enabled, run queries and check CloudWatch
2. **Compare JSON Format**: Look for differences in how coordinates are serialized
3. **Check Library Versions**: Compare Strands/MCP versions between environments
4. **Test Simplified Queries**: Try queries with explicit coordinate formats
5. **Network Analysis**: Check if AWS networking modifies requests

## Cleanup

Once the issue is resolved:
1. Disable debug mode: `./newinfra/toggle_debug.sh disable`
2. Remove debug code as documented in `CLEANUP.md`
3. Optionally keep the test suite for regression testing
4. Delete the entire `newinfra/` directory if no longer needed

## Example Output

```
🧪 Running Debug Test Suite for aws
📝 Logging to: logs/debug_aws_20241206_143022.json
============================================================
✅ Health Check: PASSED
🔌 MCP Status: PASSED
   Connected: 3/3

📍 known_city_seattle: FAILED
   Query: What's the weather in Seattle?
   Duration: 13.45s
   ⚠️  Formatting error detected
   🔄 Retry pattern detected
```

## Other Testing Options

```bash
# Test only Docker
./newinfra/run_debug_tests.sh docker

# Test only AWS
./newinfra/run_debug_tests.sh aws

# Use custom AWS URL
./newinfra/run_debug_tests.sh aws http://custom-alb-url.com
```

## Troubleshooting the Debug Tools

If tests fail to run:
1. Check Python dependencies: `pip install aiohttp`
2. Verify service URLs are correct
3. Ensure AWS credentials are configured
4. Check network connectivity

## Contributing

When adding new tests:
1. Add test cases to `debug_test_suite.py`
2. Update comparison logic if new patterns emerge
3. Document findings in `newinfra-troubleshooting.md`

## Support

All debug tools and documentation are in the `newinfra/` directory:
- This file - Overview and quick start guide
- `newinfra-troubleshooting.md` - Detailed investigation notes
- `CLEANUP.md` - How to remove debug code
- `DEBUGGING_SUMMARY.md` - Original summary (merged into this file)