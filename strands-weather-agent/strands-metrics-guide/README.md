# Strands Weather Agent - Metrics Quick Start

This directory contains debugging, validation, and demo scripts for the Strands Weather Agent's metrics and telemetry integration with Langfuse.

## Prerequisites

- Strands Weather Agent project is set up and configured
- `.env` file in the parent directory with Langfuse credentials
- Python environment with required dependencies installed
- MCP servers running (use `../scripts/start_servers.sh`)

## Available Scripts

### Core Validation Scripts

#### 1. Check Configuration
```bash
python debug_telemetry.py
```
Verifies your Langfuse configuration and environment setup.

#### 2. Test Basic Telemetry
```bash
python test_simple_telemetry.py
```
Runs a simple weather query to test telemetry is working.

#### 3. Full Validation
```bash
python run_and_validate_metrics.py
```
Comprehensive test that runs queries and validates metrics are captured in Langfuse.

#### 4. Inspect Traces
```bash
python inspect_traces.py --hours 24
```
Reviews traces from the last 24 hours to debug issues.

#### 5. Monitor Performance
```bash
python monitor_performance.py
```
Measures telemetry overhead and performance impact.

### Demo and Maintenance Scripts

#### 6. Professional Demo Showcase
```bash
python demo_showcase.py
# Options:
#   --no-telemetry    Disable Langfuse telemetry
#   --verbose         Show detailed information
#   --quick           Run a quick demo with fewer queries
```
Professional demonstration of all Weather Agent capabilities with telemetry tracking.

#### 7. Project Cleanup Utility
```bash
python cleanup_project.py
# Options:
#   --execute         Actually delete files (default is dry run)
#   --days N          Delete logs older than N days (default: 7)
```
Maintains project cleanliness by removing old logs, test results, and checking for common issues.

## Quick Debugging

If metrics aren't showing up:

1. Check configuration: `python strands-metrics-guide/debug_telemetry.py`
2. Run a test query: `python strands-metrics-guide/test_simple_telemetry.py`
3. Check Langfuse UI at the URL in your `LANGFUSE_HOST` setting
4. Review traces: `python strands-metrics-guide/inspect_traces.py --hours 1`

## Documentation

### Langfuse Integration Guide
For comprehensive setup instructions, including Docker deployment, see [LANGFUSE_INTEGRATION.md](./LANGFUSE_INTEGRATION.md).

### Docker-Specific Setup
When running with Docker, additional configuration is required:
- Network configuration to connect to Langfuse
- Environment variable mapping for container communication
- Special host configuration for Docker networking

See the [Docker Deployment Setup](./LANGFUSE_INTEGRATION.md#docker-deployment-setup) section in the integration guide.

### Additional Resources
For detailed implementation guides and troubleshooting, see the parent [strands-metrics-guide](../../strands-metrics-guide/) directory:
- Complete Langfuse integration documentation
- Debug logging strategies
- Best practices and patterns