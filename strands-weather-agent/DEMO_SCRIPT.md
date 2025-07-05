# Weather Agent Demo Guide

A comprehensive guide to demonstrate the AWS Strands Weather Agent with debug logging and Langfuse observability.

## 🚀 Quick Start Demo

### Prerequisites
Ensure you've completed the setup from the README:
- ✅ AWS credentials configured
- ✅ `.env` file configured with your Bedrock model
- ✅ Dependencies installed (`pip install -r requirements.txt`)

### Step 1: Start the Services

```bash
# Start the MCP servers
./scripts/start_servers.sh
```

### Step 2: Run the Demo Showcase

```bash
# Quick demo (2-3 minutes)
python strands-metrics-guide/demo_showcase.py --quick

# Full demo with all categories
python strands-metrics-guide/demo_showcase.py

# Demo with debug logging
python strands-metrics-guide/demo_showcase.py --debug

# Demo with metrics validation
python strands-metrics-guide/demo_showcase.py --verbose
```

**Demo Options:**
- `--quick`: Run abbreviated demo with fewer queries
- `--debug`: Enable debug logging to file (logs saved to `logs/`)
- `--verbose`: Show detailed information and validate metrics
- `--no-telemetry`: Disable Langfuse telemetry

This will demonstrate:
- 🌤️ Current weather queries
- 📊 Multi-location comparisons  
- 🌾 Agricultural recommendations
- 📈 Historical weather data
- 📋 Structured output capabilities (with --verbose)
- 🔍 Metrics validation (with --verbose)

### Step 3: Validate Telemetry Setup (Optional)

If you're using Langfuse for observability:

```bash
# Ensure ENABLE_TELEMETRY=true in .env, then:
python strands-metrics-guide/run_and_validate_metrics.py

# For detailed trace analysis:
python strands-metrics-guide/run_and_validate_metrics.py --verbose
```

### Step 4: Try Interactive Mode

```bash
# Start the chatbot
python weather_agent/chatbot.py

# With debug logging:
python weather_agent/chatbot.py --debug

# Example queries:
> What's the weather in Seattle?
> Compare weather between London and Tokyo
> Are conditions good for planting tomatoes in Iowa?
```

## 🐳 Docker Demo (Alternative)

```bash
# Start everything with Docker
./scripts/start_docker.sh

# Test the API
curl http://localhost:7777/health

# Submit a query
curl -X POST http://localhost:7777/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Seattle?"}'
```

## 📝 What You'll See

1. **MCP Tool Discovery**: The agent automatically finds weather tools
2. **Smart Responses**: Natural language answers with real data
3. **Multiple Tools**: Different servers handle forecast, historical, and agricultural data
4. **Fast Performance**: Responses in 2-4 seconds
5. **Debug Insights**: With `--debug`, see detailed agent reasoning
6. **Metrics Tracking**: With telemetry enabled, track token usage and costs

## 🎯 Key Features to Highlight

- **No Code Changes for Observability**: Telemetry works automatically
- **Model Flexibility**: Switch between Claude, Llama, or other Bedrock models
- **Production Ready**: Same code runs locally and on AWS ECS
- **Comprehensive Logging**: Debug mode provides deep insights
- **Cost Tracking**: Monitor token usage and estimated costs

## 🛠️ Utilities

### Metrics and Debugging Scripts

```bash
# Main demo showcase (combines all features)
python strands-metrics-guide/demo_showcase.py

# Validate telemetry is working
python strands-metrics-guide/run_and_validate_metrics.py

# Clean up old logs and temp files
python strands-metrics-guide/cleanup_project.py
```

### Quick Troubleshooting

**Servers not starting?**
```bash
./scripts/stop_servers.sh
./scripts/start_servers.sh
```

**Want to see debug logs?**
```bash
# For demo showcase
python strands-metrics-guide/demo_showcase.py --debug

# For chatbot
python weather_agent/chatbot.py --debug
```

**Test individual components?**
```bash
# Test structured output
python weather_agent/structured_output_demo.py
```

## 🏁 Cleanup

```bash
# Stop the servers
./scripts/stop_servers.sh

# Clean up project files (logs, temp files)
python strands-metrics-guide/cleanup_project.py

# Or stop Docker
./scripts/stop_docker.sh
```

That's it! The demo showcases a complete AI agent system with distributed tools, debug logging, and observability in just a few commands.