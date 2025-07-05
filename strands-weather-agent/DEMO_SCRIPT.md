# AWS Strands Weather Agent Demo Script

This guide provides a complete walkthrough for demonstrating the AWS Strands Weather Agent with Langfuse observability.

## 🎯 Demo Overview

The Weather Agent demonstrates:
- **AI-powered weather intelligence** using AWS Bedrock and Strands
- **Distributed tool architecture** with MCP (Model Context Protocol) servers
- **Production-ready observability** with Langfuse telemetry
- **Multiple deployment options** (local and Docker)
- **Real-time metrics and tracing** for debugging and monitoring

## 📋 Pre-Demo Setup

### 1. Environment Check
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock access
aws bedrock list-foundation-models --region us-east-1 | grep "claude-3-5-sonnet"
```

### 2. Clean Previous Runs
```bash
# Clean up old logs and test artifacts
python strands-metrics-guide/cleanup_project.py --execute

# Stop any running servers
./scripts/stop_servers.sh
./scripts/stop_docker.sh
```

### 3. Verify Configuration
```bash
# Check environment configuration
python strands-metrics-guide/debug_telemetry.py
```

## 🚀 Demo Flow

### Option A: Local Development Demo

#### Step 1: Start MCP Servers
```bash
# Start all three MCP servers
./scripts/start_servers.sh

# Verify servers are healthy
curl http://localhost:7778/health  # Forecast server
curl http://localhost:7779/health  # Historical server
curl http://localhost:7780/health  # Agricultural server
```

#### Step 2: Run the Showcase Demo
```bash
# Full demonstration with all features
python strands-metrics-guide/demo_showcase.py

# Or quick demo (fewer queries)
python strands-metrics-guide/demo_showcase.py --quick
```

#### Step 3: Interactive Chatbot
```bash
# Start interactive mode
python weather_agent/chatbot.py

# Example queries to try:
# > What's the weather in Seattle?
# > Give me a 5-day forecast for New York
# > Compare weather between London and Tokyo
# > Are conditions good for planting tomatoes in Iowa?
# > What was the temperature in Chicago last week?
```

#### Step 4: View Telemetry
Open http://localhost:3000 in your browser to see:
- Real-time traces of all queries
- Token usage and costs
- Latency metrics
- Tool call details

#### Step 5: Analyze Metrics
```bash
# Inspect recent traces
python strands-metrics-guide/inspect_traces.py

# Monitor performance impact
python strands-metrics-guide/monitor_performance.py
```

### Option B: Docker Deployment Demo

#### Step 1: Start All Services
```bash
# Start with AWS credentials injection
./scripts/start_docker.sh

# Monitor startup
docker compose logs -f
```

#### Step 2: Test the API
```bash
# Health check
curl http://localhost:7777/health

# Submit a query
curl -X POST http://localhost:7777/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather forecast for Seattle?",
    "session_id": "demo-session",
    "user_id": "demo-user"
  }'
```

#### Step 3: Run Validation
```bash
# Comprehensive validation
python strands-metrics-guide/run_and_validate_metrics.py --verbose
```

## 📊 Key Demo Points

### 1. Architecture Highlights
- **MCP Servers**: Show how each server handles specific domains (forecast, historical, agricultural)
- **Tool Discovery**: Agent automatically discovers available tools from MCP servers
- **Streaming**: Real-time response streaming for better UX

### 2. Observability Features
- **Automatic Tracing**: Every query is traced without code changes
- **Cost Tracking**: Show token usage and estimated costs in Langfuse
- **Performance Metrics**: Demonstrate latency tracking and bottleneck identification
- **Session Management**: Show how conversations are grouped by session ID

### 3. Model Flexibility
```bash
# Show model switching capability
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-haiku-20241022-v1:0 python weather_agent/chatbot.py
```

### 4. Structured Output
```bash
# Demonstrate structured output parsing
python weather_agent/structured_output_demo.py
```

## 🎭 Demo Scenarios

### Scenario 1: Weather Intelligence
1. Ask about current weather in multiple cities
2. Request a weekly forecast
3. Compare weather between locations
4. Show how the agent uses multiple tools to answer complex queries

### Scenario 2: Agricultural Advisory
1. Ask about planting conditions for specific crops
2. Request frost warnings
3. Query soil moisture recommendations
4. Demonstrate domain-specific knowledge

### Scenario 3: Historical Analysis
1. Query past weather patterns
2. Ask about temperature trends
3. Compare this year to historical averages
4. Show data aggregation capabilities

### Scenario 4: Error Handling
1. Ask about a non-existent location
2. Request data beyond available range
3. Show graceful error handling and user guidance

## 🛠️ Troubleshooting

### Common Issues

#### MCP Servers Not Starting
```bash
# Check if ports are in use
lsof -i :7778,7779,7780

# Force stop and restart
./scripts/stop_servers.sh
./scripts/start_servers.sh
```

#### No Traces in Langfuse
```bash
# Verify telemetry is enabled
grep ENABLE_TELEMETRY .env  # Should be "true"

# Test telemetry
python strands-metrics-guide/test_simple_telemetry.py
```

#### Docker Issues
```bash
# Clean restart
docker compose down -v
./scripts/start_docker.sh

# Check logs
docker compose logs weather-agent
```

## 📈 Metrics to Highlight

### Performance Metrics
- **Response Time**: Typically 2-4 seconds for complex queries
- **Token Efficiency**: Show optimized prompts and responses
- **Concurrent Handling**: Multiple MCP servers working in parallel

### Cost Analysis
- **Token Usage**: ~500-1500 tokens per query
- **Model Costs**: Show cost comparison between models
- **Optimization**: Demonstrate prompt optimization impact

### Quality Metrics
- **Accuracy**: Structured output validation
- **Completeness**: All requested information provided
- **Relevance**: Focused responses without hallucination

## 🎬 Demo Script

### Opening (2 minutes)
"Today I'll demonstrate our Weather Intelligence Agent built with AWS Strands and Langfuse observability. This showcases how to build production-ready AI agents with distributed tools and comprehensive monitoring."

### Architecture Overview (3 minutes)
- Show the architecture diagram
- Explain MCP servers and tool distribution
- Highlight AWS Bedrock integration
- Introduce Langfuse observability

### Live Demo (10 minutes)
1. Start with simple weather query
2. Progress to complex multi-location comparison
3. Show agricultural use case
4. Demonstrate historical analysis
5. Open Langfuse to show traces

### Observability Deep Dive (5 minutes)
- Navigate Langfuse dashboard
- Show trace details and tool calls
- Highlight token usage and costs
- Demonstrate session tracking

### Deployment Options (3 minutes)
- Show local development setup
- Demonstrate Docker deployment
- Discuss production considerations

### Q&A (7 minutes)
- Address questions
- Show additional features as needed
- Discuss extension possibilities

## 🎯 Key Takeaways

1. **Production-Ready Architecture**: MCP servers provide scalable tool distribution
2. **Comprehensive Observability**: Every interaction is tracked and analyzable
3. **Cost Optimization**: Full visibility into LLM usage and costs
4. **Developer Experience**: Easy local development and debugging
5. **Deployment Flexibility**: Works locally, in Docker, or on AWS ECS

## 📚 Additional Resources

- [AWS Strands Documentation](https://github.com/aws/strands)
- [Langfuse Documentation](https://langfuse.com/docs)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Project README](./README.md)

## 🏁 Demo Cleanup

```bash
# Stop all services
./scripts/stop_servers.sh
./scripts/stop_docker.sh

# Clean up logs (optional)
python strands-metrics-guide/cleanup_project.py --execute
```

Remember to save interesting traces in Langfuse for future reference!