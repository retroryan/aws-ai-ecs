# Strands Weather Agent - Metrics Quick Start

This directory contains debugging and validation scripts for the Strands Weather Agent's metrics and telemetry integration with Langfuse.

## Prerequisites

- Strands Weather Agent project is set up and configured
- `.env` file in the parent directory with Langfuse credentials
- Python environment with required dependencies installed

## Available Scripts

### 1. Check Configuration
```bash
python strands-metrics-guide/debug_telemetry.py
```
Verifies your Langfuse configuration and environment setup.

### 2. Test Basic Telemetry
```bash
python strands-metrics-guide/test_simple_telemetry.py
```
Runs a simple weather query to test telemetry is working.

### 3. Full Validation
```bash
python strands-metrics-guide/run_and_validate_metrics.py
```
Comprehensive test that runs queries and validates metrics are captured in Langfuse.

### 4. Inspect Traces
```bash
python strands-metrics-guide/inspect_traces.py --hours 24
```
Reviews traces from the last 24 hours to debug issues.

### 5. Monitor Performance
```bash
python strands-metrics-guide/monitor_performance.py
```
Measures telemetry overhead and performance impact.

## Quick Debugging

If metrics aren't showing up:

1. Check configuration: `python strands-metrics-guide/debug_telemetry.py`
2. Run a test query: `python strands-metrics-guide/test_simple_telemetry.py`
3. Check Langfuse UI at the URL in your `LANGFUSE_HOST` setting
4. Review traces: `python strands-metrics-guide/inspect_traces.py --hours 1`

## Documentation

For detailed implementation guides and troubleshooting, see the parent [strands-metrics-guide](../../strands-metrics-guide/) directory:
- Complete Langfuse integration documentation
- Debug logging strategies
- Best practices and patterns