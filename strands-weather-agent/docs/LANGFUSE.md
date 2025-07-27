# Langfuse Integration Guide

## Overview

This project includes **production-grade observability** using Langfuse that showcases:
- **AWS Strands agents** with AWS Bedrock integration
- **Langfuse observability** via OpenTelemetry for comprehensive monitoring
- **Real-time performance metrics** after every query
- **Zero-configuration auto-detection** - telemetry "just works" when Langfuse is available

## Performance Metrics Display

Every query shows actual performance data:
```
📊 Performance Metrics:
   ├─ Tokens: 17051 total (16588 input, 463 output)
   ├─ Latency: 13.35 seconds
   ├─ Throughput: 1277 tokens/second
   ├─ Model: claude-3-5-sonnet-20241022
   └─ Cycles: 2
```

## Auto-Detection

The system automatically detects if Langfuse is configured and running:
- ✅ If Langfuse credentials are configured → Telemetry is automatically enabled
- ✅ If Langfuse is not configured → Continues normally without telemetry
- ✅ No errors, no delays, graceful fallback

## Running with Langfuse

### Local Development

1. **Start Langfuse Locally**:
   ```bash
   git clone https://github.com/langfuse/langfuse
   cd langfuse
   docker-compose up -d
   ```
   Langfuse will be available at http://localhost:3000

2. **Configure API Keys**:
   - Login to Langfuse and create a new project
   - Generate API keys from the project settings
   - Configure your environment:
   ```bash
   cp .env.example .env
   # Edit .env and add your Langfuse API keys
   ```

### AWS Deployment

For observability in AWS production environments:

1. **Deploy Langfuse to AWS**:
   - See https://github.com/retroryan/langfuse-samples/tree/main/langfuse-aws for an easy deployment guide
   - After deployment, login to Langfuse and create a new project
   - Generate API keys from the project settings

2. **Configure Cloud Environment**:
   ```bash
   # Copy and configure cloud environment
   cp cloud.env.example cloud.env
   
   # Edit cloud.env to add:
   # - Your Langfuse API keys (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST)
   ```

## Langfuse Features

When Langfuse credentials are configured:
1. Automatic OpenTelemetry instrumentation
2. Distributed tracing across all components
3. Token usage and cost tracking
4. Session and user attribution
5. Performance monitoring and analysis

## Environment Variables

Configure these in your `.env` file:
- `LANGFUSE_PUBLIC_KEY`: Public key for Langfuse API
- `LANGFUSE_SECRET_KEY`: Secret key for Langfuse API
- `LANGFUSE_HOST`: Langfuse API host (default: https://us.cloud.langfuse.com)
- `ENABLE_TELEMETRY`: Enable/disable telemetry (true/false, default: false)
- `TELEMETRY_USER_ID`: Default user ID for telemetry
- `TELEMETRY_SESSION_ID`: Default session ID for telemetry
- `TELEMETRY_TAGS`: Comma-separated tags for filtering

## Testing Telemetry

### Enable Telemetry for a Session
```bash
# Set up Langfuse credentials
export LANGFUSE_PUBLIC_KEY=your_public_key
export LANGFUSE_SECRET_KEY=your_secret_key
export LANGFUSE_HOST=https://us.cloud.langfuse.com

# Run with telemetry enabled
python -c "
import asyncio
from weather_agent.mcp_agent import MCPWeatherAgent

async def test_with_telemetry():
    agent = MCPWeatherAgent(
        enable_telemetry=True,
        telemetry_user_id='test-user-123',
        telemetry_session_id='test-session-456',
        telemetry_tags=['test', 'development']
    )
    
    response = await agent.query('What is the weather in Chicago?')
    print('Response received')
    print('Check Langfuse dashboard for traces')

asyncio.run(test_with_telemetry())
"
```

### Validate Metrics Collection
```bash
# Run comprehensive validation
cd strands-metrics-guide
python run_and_validate_metrics.py

# Debug telemetry configuration
python debug_telemetry.py

# Inspect collected traces
python inspect_traces.py

# Monitor performance impact
python monitor_performance.py
```

## Langfuse v3 Features

The system uses Langfuse v3.1.2 with full feature support:
- **Native v3 Support**: Full compatibility with latest Langfuse features
- **Deterministic Trace IDs**: Use `Langfuse.create_trace_id(seed)` for predictable traces
- **Direct Scoring API**: Score traces with `agent.score_trace()` method
- **Enhanced Client**: Langfuse client with `tracing_enabled=True` parameter
- **Hybrid Approach**: Combines OTEL telemetry with direct Langfuse API operations
- **v3 Demo Script**: `demo_langfuse_v3.py` showcases all new features