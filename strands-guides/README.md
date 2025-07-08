# AWS Strands Guides

This directory contains comprehensive guides and best practices for building applications with AWS Strands, with a focus on observability, telemetry, and production deployment patterns.

## Available Guides

### 1. [STRANDS_TELEMETRY_BEST_PRACTICES.md](./STRANDS_TELEMETRY_BEST_PRACTICES.md)
**Focus**: Telemetry and metrics implementation with Langfuse

Key topics:
- Native OpenTelemetry integration patterns
- The critical 20-line implementation pattern
- Common pitfalls and how to avoid them
- Production deployment strategies
- Troubleshooting guide

**When to use**: When implementing observability and metrics in your Strands applications.

### 2. [STRANDS_GENERAL_BEST_PRACTICES.md](./STRANDS_GENERAL_BEST_PRACTICES.md)
**Focus**: General Strands development patterns and best practices

Key topics:
- Agent lifecycle management (when to create vs reuse)
- Structured input/output with Pydantic
- Tool development patterns
- MCP (Model Context Protocol) integration
- Error handling strategies
- Performance optimization
- Production deployment patterns

**When to use**: As a general reference for building Strands applications.

## Quick Reference

### Telemetry Setup (20 Lines)
```python
# 1. Load env vars FIRST
from dotenv import load_dotenv
load_dotenv()

# 2. Configure OTEL BEFORE imports
import os
import base64

if os.getenv("LANGFUSE_PUBLIC_KEY"):
    auth = base64.b64encode(
        f"{os.getenv('LANGFUSE_PUBLIC_KEY')}:{os.getenv('LANGFUSE_SECRET_KEY')}".encode()
    ).decode()
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{os.getenv('LANGFUSE_HOST')}/api/public/otel/v1/traces"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"

# 3. Import Strands AFTER configuration
from strands import Agent
from strands.telemetry import StrandsTelemetry

# 4. Initialize telemetry
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()

# 5. Create agents with trace attributes
agent = Agent(
    trace_attributes={
        "session.id": "abc-123",
        "user.id": "user@example.com",
        "langfuse.tags": ["demo", "strands"]
    }
)
```

### Agent Lifecycle Decision Tree
```
Is your application stateful?
├─ YES → Create Once, Reuse Pattern
│   ├─ Web App → Store in session state
│   ├─ CLI Tool → Global instance
│   └─ Long-running → Agent pool
└─ NO → Create Per Request Pattern
    ├─ API/Lambda → New agent with restored state
    ├─ Batch → New agent per item
    └─ High concurrency → Request-scoped agents
```

## Key Principles

1. **Configuration Before Import**: Always set OTEL environment variables before importing Strands
2. **Keep It Simple**: The best implementations are often the simplest (20 lines vs 400+)
3. **Use Native Features**: Leverage Strands' built-in capabilities rather than creating wrappers
4. **Fail Gracefully**: Telemetry should be optional and not impact core functionality
5. **Monitor Performance**: Track token usage, latency, and costs in production

## Additional Resources

- **Official Strands Repository**: See the official samples, especially:
  - Sample 01: Fundamentals
  - Sample 08: Observability and evaluation
  - Sample 03: AWS assistant with MCP
  
- **Langfuse Documentation**: For trace analysis and dashboard creation

- **OpenTelemetry Specification**: For advanced OTEL configuration

## Contributing

These guides are based on real-world implementation experience. If you discover new patterns or best practices, please contribute by:
1. Testing your approach thoroughly
2. Documenting clear examples
3. Including troubleshooting tips
4. Referencing official documentation

## Version History

- **v1.0** (January 2025): Initial guides based on Weather Agent implementation
  - Comprehensive telemetry integration
  - General best practices from official docs
  - Production deployment patterns