# Strands Metrics Guide

This directory contains comprehensive documentation and tools for implementing observability and debug logging in the AWS Strands Weather Agent project.

## Contents

### Documentation

1. **[LANGFUSE_INTEGRATION.md](./LANGFUSE_INTEGRATION.md)** - Complete guide for Langfuse observability integration
   - Implementation guide with critical updates
   - Integration success report
   - Debug scripts documentation
   - Troubleshooting and best practices
   - Reference implementation details

2. **[DEBUG_LOGGING.md](./DEBUG_LOGGING.md)** - Comprehensive debug logging guide
   - Local development debugging
   - Docker debug mode implementation
   - Telemetry debug scripts
   - Log analysis techniques
   - Best practices and troubleshooting

### Debug Scripts

All scripts are configured to run from the parent directory and automatically load the `.env` file:

1. **`debug_telemetry.py`** - Configuration checker
   ```bash
   python strands-metrics-guide/debug_telemetry.py
   ```

2. **`test_simple_telemetry.py`** - Quick telemetry test
   ```bash
   python strands-metrics-guide/test_simple_telemetry.py
   ```

3. **`run_and_validate_metrics.py`** - Full integration test
   ```bash
   python strands-metrics-guide/run_and_validate_metrics.py
   ```

4. **`inspect_traces.py`** - Analyze recent traces
   ```bash
   python strands-metrics-guide/inspect_traces.py --hours 24
   ```

5. **`monitor_performance.py`** - Measure telemetry overhead
   ```bash
   python strands-metrics-guide/monitor_performance.py
   ```

## Quick Start

### 1. Configure Environment

Ensure your `.env` file in the parent directory contains:
```env
# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000

# AWS Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_REGION=us-west-2
```

### 2. Test Configuration

```bash
# Check if everything is configured correctly
python strands-metrics-guide/debug_telemetry.py
```

### 3. Run a Simple Test

```bash
# Run a simple query with telemetry
python strands-metrics-guide/test_simple_telemetry.py
```

### 4. Validate Full Integration

```bash
# Run comprehensive validation
python strands-metrics-guide/run_and_validate_metrics.py --verbose
```

## Key Features

- **Langfuse Integration**: Complete OpenTelemetry-based observability
- **Debug Logging**: Detailed logging for development and troubleshooting
- **Performance Monitoring**: Tools to measure telemetry overhead
- **Trace Analysis**: Scripts to inspect and analyze traces
- **Docker Support**: Debug mode for containerized deployments

## Notes

- All scripts automatically load the `.env` file from the parent directory
- Scripts are designed to be run from the project root
- Debug logs are written to the `logs/` directory in the parent directory
- Langfuse UI is accessible at the URL configured in `LANGFUSE_HOST`