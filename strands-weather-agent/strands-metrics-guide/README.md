# Weather Agent Demo and Metrics Tools

This directory contains the consolidated tools for demonstrating and validating the Weather Agent system with AWS Strands and Langfuse observability.

## 🛠️ Available Scripts

### 1. `demo_showcase.py` - Professional Demo Showcase
The main demonstration script that showcases all Weather Agent capabilities with optional debug logging and metrics validation.

**Features:**
- Multi-category weather queries (current, forecast, historical, agricultural)
- Debug logging to file with `--debug` flag
- Metrics validation with `--verbose` flag
- Quick demo mode with `--quick` flag
- Telemetry tracking with Langfuse (when enabled)

**Usage:**
```bash
# Quick demo (2-3 minutes)
python demo_showcase.py --quick

# Full demo with debug logging
python demo_showcase.py --debug

# Demo with metrics validation
python demo_showcase.py --verbose

# All options combined
python demo_showcase.py --debug --verbose
```

### 2. `run_and_validate_metrics.py` - Telemetry Validator
Validates that Langfuse telemetry integration is working correctly.

**Features:**
- Checks service connectivity (Langfuse, AWS, MCP servers)
- Runs minimal test query with telemetry
- Validates traces were created in Langfuse
- Provides detailed diagnostics

**Usage:**
```bash
# Basic validation
python run_and_validate_metrics.py

# Detailed trace analysis
python run_and_validate_metrics.py --verbose

# Skip prerequisite checks
python run_and_validate_metrics.py --skip-checks
```

### 3. `cleanup_project.py` - Project Maintenance
Helps maintain the project by cleaning up old files and checking for issues.

**Features:**
- Removes old log files (customizable age threshold)
- Cleans up temporary files and caches
- Checks for code issues (hardcoded values, old model IDs)
- Validates environment configuration

**Usage:**
```bash
# Dry run (see what would be cleaned)
python cleanup_project.py

# Actually clean files
python cleanup_project.py --execute

# Clean logs older than 3 days
python cleanup_project.py --days 3 --execute
```

## 📋 Prerequisites

1. **Environment Setup:**
   ```bash
   # Copy and configure .env
   cp ../.env.example ../.env
   # Edit ../.env and set:
   # - BEDROCK_MODEL_ID (required)
   # - ENABLE_TELEMETRY=true (for metrics)
   # - LANGFUSE_* credentials (for observability)
   ```

2. **Start MCP Servers:**
   ```bash
   ../scripts/start_servers.sh
   ```

3. **AWS Credentials:**
   Ensure AWS credentials are configured with Bedrock access.

## 🚀 Quick Start

```bash
# 1. Start the MCP servers
../scripts/start_servers.sh

# 2. Run the demo showcase
python demo_showcase.py --quick

# 3. Validate metrics (if using Langfuse)
python run_and_validate_metrics.py

# 4. Clean up when done
../scripts/stop_servers.sh
python cleanup_project.py --execute
```

## 🔍 Debug Mode

When running with `--debug`, detailed logs are saved to:
```
../logs/demo_showcase_debug_YYYYMMDD_HHMMSS.log
```

These logs include:
- Strands framework debug output
- MCP tool discovery and execution
- Full agent reasoning traces
- Performance metrics

## 📊 Metrics and Observability

When telemetry is enabled (`ENABLE_TELEMETRY=true`), the system tracks:
- Token usage per query
- Response latencies
- Tool calls to MCP servers
- Session and user tracking
- Cost estimates

View metrics in your Langfuse dashboard or use the `--verbose` flag with `demo_showcase.py` to see inline metrics summaries.

## 🎯 Quick Debugging

If metrics aren't showing up:

1. **Check configuration:**
   ```bash
   python run_and_validate_metrics.py
   ```

2. **Enable telemetry in .env:**
   ```
   ENABLE_TELEMETRY=true
   LANGFUSE_PUBLIC_KEY=your_key
   LANGFUSE_SECRET_KEY=your_secret
   ```

3. **Run with verbose output:**
   ```bash
   python demo_showcase.py --verbose
   ```

4. **Check Langfuse dashboard:**
   Visit the URL in your `LANGFUSE_HOST` setting (default: https://us.cloud.langfuse.com)

## 📚 Additional Resources

- Parent project documentation: [../CLAUDE.md](../CLAUDE.md)
- Demo guide: [../DEMO_SCRIPT.md](../DEMO_SCRIPT.md)
- Main README: [../README.md](../README.md)