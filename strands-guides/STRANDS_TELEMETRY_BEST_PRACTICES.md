# AWS Strands Telemetry & Metrics Best Practices

## Overview

This guide provides a comprehensive summary of best practices for implementing telemetry and metrics in AWS Strands applications, with a focus on Langfuse integration. It synthesizes learnings from the official Strands documentation and real-world implementation experience.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Implementation Pattern](#implementation-pattern)
3. [Key Learnings](#key-learnings)
4. [Best Practices](#best-practices)
5. [Common Pitfalls](#common-pitfalls)
6. [Reference Examples](#reference-examples)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## Core Principles

### 1. Native OpenTelemetry Integration
AWS Strands has built-in OpenTelemetry (OTEL) support. Always use the native integration rather than creating custom telemetry solutions.

### 2. Configuration Before Import
**Critical**: OTEL environment variables MUST be set before importing any Strands modules. This is the most common source of silent failures.

### 3. Explicit Initialization
Unlike some observability tools, Strands telemetry requires explicit initialization with `StrandsTelemetry().setup_otlp_exporter()`.

### 4. Signal-Specific Endpoints
Always use signal-specific endpoints (e.g., `/api/public/otel/v1/traces`) rather than generic OTEL endpoints.

---

## Implementation Pattern

### The Correct Pattern (20 Lines)

```python
# STEP 1: Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

# STEP 2: Configure OTEL environment variables BEFORE any Strands imports
import os
import base64

# Get Langfuse credentials
public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
secret_key = os.getenv("LANGFUSE_SECRET_KEY")
langfuse_host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

if public_key and secret_key:
    # Create auth token
    auth_token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    
    # CRITICAL: Use signal-specific endpoint
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{langfuse_host}/api/public/otel/v1/traces"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth_token}"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"

# STEP 3: NOW import Strands after OTEL configuration
from strands import Agent
from strands.telemetry import StrandsTelemetry

# STEP 4: Initialize telemetry (if credentials were provided)
if public_key and secret_key:
    telemetry = StrandsTelemetry()
    telemetry.setup_otlp_exporter()

# STEP 5: Create agent with trace attributes
agent = Agent(
    model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    trace_attributes={
        "session.id": "demo-session-123",
        "user.id": "demo@example.com",
        "langfuse.tags": ["weather-agent", "demo", "strands"]
    }
)
```

---

## Key Learnings

### 1. Order Matters
- Environment variables MUST be set before Strands imports
- This happens during module initialization, not at runtime
- Getting this wrong results in silent failures

### 2. Simplicity Wins
- The official Strands samples show a ~20 line implementation
- Avoid over-engineering with health checks and availability detection
- Trust OTEL's built-in retry and buffering mechanisms

### 3. MCP Integration is Automatic
- MCP (Model Context Protocol) server calls are automatically tracked
- No additional instrumentation needed
- Tool parameters and results are captured in traces

### 4. Session Management is Powerful
- Use consistent session IDs to track full conversations
- Enables journey analysis and debugging
- Critical for multi-turn interactions

---

## Best Practices

### 1. Use Environment Variables
```env
# .env file
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

### 2. Implement Trace Attributes
```python
trace_attributes = {
    # Required for Langfuse
    "session.id": session_id,
    "user.id": user_id,
    "langfuse.tags": ["tag1", "tag2"],
    
    # Additional context
    "environment": "production",
    "workflow.type": "customer-query",
    "deployment.region": "us-west-2"
}
```

### 3. Force Flush for Short Scripts
```python
# Ensure traces are sent before script exits
from opentelemetry import trace

tracer_provider = trace.get_tracer_provider()
if hasattr(tracer_provider, 'force_flush'):
    tracer_provider.force_flush()
```

### 4. Handle Missing Credentials Gracefully
```python
# Telemetry should be optional
if not (public_key and secret_key):
    logger.info("Telemetry disabled - no credentials provided")
    # Application continues normally without telemetry
```

### 5. Use Structured Output with Telemetry
```python
# Structured output works seamlessly with telemetry
from pydantic import BaseModel

class WeatherInfo(BaseModel):
    location: str
    temperature: float
    conditions: str

# This will be tracked in telemetry
result = agent.structured_output(
    WeatherInfo,
    "What's the weather in Seattle?"
)
```

---

## Common Pitfalls

### 1. ❌ Setting OTEL Config After Imports
```python
# WRONG - telemetry won't work
from strands import Agent
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "..."
```

### 2. ❌ Using Generic OTEL Endpoint
```python
# WRONG - returns 404
endpoint = f"{langfuse_host}/api/public/otel"

# CORRECT - signal-specific
endpoint = f"{langfuse_host}/api/public/otel/v1/traces"
```

### 3. ❌ Forgetting Explicit Initialization
```python
# WRONG - just setting env vars isn't enough
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "..."

# CORRECT - must explicitly initialize
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()
```

### 4. ❌ Over-Engineering the Solution
```python
# WRONG - unnecessary complexity
class CustomTelemetryWrapper:
    def __init__(self):
        self.check_availability()
        self.setup_health_monitoring()
        # 400+ lines of wrapper code...

# CORRECT - use native integration
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()
```

---

## Reference Examples

### FastAPI Integration
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Load env vars FIRST
from dotenv import load_dotenv
load_dotenv()

# Setup telemetry BEFORE Strands imports
import os
import base64

if os.getenv("LANGFUSE_PUBLIC_KEY"):
    # Configure OTEL...
    
from strands import Agent
from strands.telemetry import StrandsTelemetry

# Initialize telemetry once at startup
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()

app = FastAPI()

@app.post("/chat")
async def chat(message: str, session_id: str):
    agent = Agent(
        trace_attributes={
            "session.id": session_id,
            "user.id": "api-user",
            "langfuse.tags": ["api", "chat"]
        }
    )
    response = await agent.invoke_async(message)
    return {"response": response}
```

### AWS Lambda Pattern
```python
# lambda_function.py
import os
import base64

# Configure OTEL before imports
def setup_telemetry():
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sk = os.environ.get("LANGFUSE_SECRET_KEY")
    if pk and sk:
        auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{os.environ['LANGFUSE_HOST']}/api/public/otel/v1/traces"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"

# Setup before imports
setup_telemetry()

from strands import Agent
from strands.telemetry import StrandsTelemetry

# Initialize once during cold start
if os.environ.get("LANGFUSE_PUBLIC_KEY"):
    telemetry = StrandsTelemetry()
    telemetry.setup_otlp_exporter()

def lambda_handler(event, context):
    agent = Agent(
        trace_attributes={
            "session.id": event.get("session_id", "default"),
            "user.id": event.get("user_id", "lambda-user"),
            "langfuse.tags": ["lambda", "production"]
        }
    )
    
    response = agent(event["message"])
    return {"response": response}
```

---

## Troubleshooting Guide

### No Traces Appearing

1. **Check Import Order**
   - Ensure OTEL config is set BEFORE Strands imports
   - Look for "TracerProvider already set" warnings

2. **Verify Credentials**
   ```bash
   echo $LANGFUSE_PUBLIC_KEY
   echo $LANGFUSE_SECRET_KEY
   curl -X GET "$LANGFUSE_HOST/api/public/health" \
     -H "Authorization: Basic $(echo -n "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" | base64)"
   ```

3. **Check Initialization**
   - Look for telemetry initialization in logs
   - Ensure `StrandsTelemetry().setup_otlp_exporter()` is called

### Missing Attributes

1. **Session/User IDs**
   - Ensure values are not None/empty
   - Check trace_attributes are passed to Agent

2. **Tags Not Appearing**
   - Must be a list of strings
   - Check for proper JSON formatting

### Performance Issues

1. **Normal Overhead**
   - Expect 20-50ms additional latency
   - Most latency is from LLM calls, not telemetry

2. **Batch Processing**
   ```python
   # For high volume
   os.environ["OTEL_BSP_MAX_QUEUE_SIZE"] = "2048"
   os.environ["OTEL_BSP_MAX_EXPORT_BATCH_SIZE"] = "512"
   ```

---

## Additional Resources

- **Official Strands Samples**: See sample 08 (observability and evaluation) in the official repository
- **Langfuse Documentation**: Comprehensive guides on trace analysis and dashboards
- **OpenTelemetry Specification**: For advanced OTEL configuration options

## Summary

Implementing telemetry in AWS Strands applications is straightforward when following the native patterns:

1. **20 lines of code** for full telemetry integration
2. **Configuration before imports** is critical
3. **Explicit initialization** is required
4. **Signal-specific endpoints** must be used
5. **Keep it simple** - avoid over-engineering

The result is comprehensive observability with minimal code complexity, enabling powerful analytics and debugging capabilities for your Strands applications.