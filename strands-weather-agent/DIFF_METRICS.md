# Telemetry Implementation Differences: Weather Agent vs Strands-Langfuse Samples

This document compares the telemetry/metrics implementations between the weather_agent project and the strands-langfuse samples repository.

## Overview

Both implementations use AWS Strands' native OpenTelemetry (OTEL) integration with Langfuse, but they differ significantly in complexity and purpose:

- **Weather Agent**: Minimalist demo implementation (24 lines of telemetry code)
- **Strands-Langfuse**: Comprehensive showcase repository (2,372 lines total)
  - Core telemetry setup: 350 lines
  - Three different demos: 959 lines
  - Validation/testing tools: 1,063 lines

## Key Differences

### 1. Initialization Approach

#### Weather Agent (Simplified)
```python
# telemetry.py - Module-level initialization
TELEMETRY_ENABLED = setup_telemetry()  # Simple boolean return

# mcp_agent.py - Silent operation if not configured
trace_attributes = {...} if TELEMETRY_ENABLED else None
```

#### Strands-Langfuse (Comprehensive)
```python
# Explicit validation and initialization
langfuse_pk, langfuse_sk, langfuse_host = initialize_langfuse_telemetry()
telemetry = setup_telemetry("service-name", "environment", "version")
```

### 2. Configuration Philosophy

| Aspect | Weather Agent | Strands-Langfuse |
|--------|--------------|------------------|
| Error Handling | Silent failure | Explicit validation |
| Configuration | Environment vars only | Service-level metadata |
| Setup Location | Module import | Function calls |
| Return Value | Boolean | Telemetry instance |

### 3. Telemetry Features

#### Weather Agent
- ✅ Basic OTEL trace collection
- ✅ Session and user tracking
- ✅ Simple tag support
- ❌ No scoring capabilities
- ❌ No trace URL tracking
- ❌ No evaluation framework

#### Strands-Langfuse
- ✅ Full OTEL trace collection
- ✅ Rich session metadata
- ✅ Extensive tagging system
- ✅ Automated scoring (exact_match, keyword_match)
- ✅ Batch evaluation workflows
- ✅ Trace discovery via API
- ✅ Multiple score types per trace

### 4. Code Complexity

#### Weather Agent: 24 Lines (telemetry.py)
```python
def setup_telemetry() -> bool:
    # Get credentials
    # Configure OTEL environment
    # Setup exporter
    # Return success/failure
```

#### Strands-Langfuse: 2,372 Lines Total
- **Core Setup**: 350 lines
  - `core/setup.py`: 96 lines (OTEL config, Langfuse client)
  - `core/agent_factory.py`: 116 lines (Agent creation)
  - `core/metrics_formatter.py`: 138 lines (Metrics & costs)
- **Demos**: 959 lines
  - `demos/examples.py`: 230 lines (Basic examples)
  - `demos/monty_python.py`: 218 lines (Themed demo)
  - `demos/scoring.py`: 511 lines (Scoring system)
- **Validation**: 1,063 lines
  - Test runners and validation scripts

### 5. Integration Patterns

Both use the **same underlying pattern**:
1. Set OTEL environment variables BEFORE importing Strands
2. Use signal-specific endpoint: `/api/public/otel/v1/traces`
3. Basic Auth with base64 encoded credentials
4. `http/protobuf` protocol

### 6. Use Case Optimization

#### Weather Agent
- **Goal**: Demonstrate telemetry with minimal code
- **Audience**: Developers learning Strands + Langfuse
- **Priority**: Simplicity and clarity
- **Philosophy**: "Less is more"

#### Strands-Langfuse
- **Goal**: Production-ready evaluation system
- **Audience**: Teams building agent evaluation pipelines
- **Priority**: Comprehensive scoring and analysis
- **Philosophy**: "Complete solution"

### 7. Notable Implementation Details

#### Common Patterns
- Neither uses Langfuse v3 decorators (`@observe`)
- Both rely on Strands' automatic OTEL integration
- Neither directly controls trace IDs
- Both emphasize correct import order

#### Differences in Trace Attributes

Weather Agent:
```python
{
    "session.id": session_id,
    "user.id": "weather-demo-user",
    "langfuse.tags": ["weather", "mcp", "strands-demo"]
}
```

Strands-Langfuse:
```python
{
    "session.id": session_id,
    "user.id": user_id,
    "test.case": test_name,
    "test.category": category,
    "test.expected": expected_value,
    "langfuse.tags": [test_name, category, "strands-demo"]
}
```

### 8. Scoring Implementation

The most significant difference is the scoring capability:

#### Weather Agent
- No scoring implementation
- Pure observability focus
- Removed during simplification

#### Strands-Langfuse
```python
# Comprehensive scoring system
def score_trace(trace_id: str, test_result: dict):
    # Automated score (0-1)
    langfuse_client.create_score(
        trace_id=trace_id,
        name=f"automated_{result['method']}",
        value=result["score"],
        data_type="NUMERIC"
    )
    
    # Test result (categorical)
    langfuse_client.create_score(
        trace_id=trace_id,
        name="test_result",
        value="passed",  # or "partial", "failed"
        data_type="CATEGORICAL"
    )
```

## Lessons Learned

1. **Both approaches are valid** for their intended use cases
2. **The weather_agent shows the minimum viable integration** - perfect for demos
3. **The strands-langfuse shows the complete pattern** - ideal for production evaluation
4. **OTEL configuration before Strands import is critical** in both
5. **Signal-specific endpoints are required** (`/traces` not `/otel`)
6. **Basic Auth pattern is consistent** across implementations

## What Each Strands-Langfuse Demo Shows

### demos/examples.py (230 lines)
- **Simple Chat**: Basic single-turn conversations
- **Multi-turn Conversation**: Context preservation across turns
- **Tool Usage**: Demonstrating tool calling with telemetry
- **Token Aggregation**: Tracking costs across multiple queries

### demos/monty_python.py (218 lines)
- **Themed Interactions**: Fun Monty Python-themed conversations
- **Rich Context**: Using system prompts for personality
- **Session Management**: Tracking related queries
- **Entertainment Value**: Making demos more engaging

### demos/scoring.py (511 lines)
- **Automated Evaluation**: Tests with expected answers
- **Multiple Scoring Methods**: exact_match, keyword_match
- **Intentional Failures**: Testing wrong answers for scoring
- **Batch Processing**: Running multiple test cases
- **Score Types**: Numeric scores, categorical results
- **Trace Discovery**: Finding traces via Langfuse API

## The Real Difference

The strands-langfuse repository isn't just "400+ lines for scoring" - it's a **complete demonstration suite** showing:

1. **How to properly set up telemetry** (core/setup.py)
2. **How to create agents with telemetry** (core/agent_factory.py)
3. **How to track costs and metrics** (core/metrics_formatter.py)
4. **Multiple usage patterns** (demos/)
5. **How to build evaluation systems** (scoring.py)
6. **How to validate everything works** (validation scripts)

The weather agent, by contrast, shows the **absolute minimum** needed to get telemetry working - which is exactly what you want for understanding the core concept.

## Recommendation

- **For demos and learning**: Use the weather_agent pattern
- **For production evaluation**: Adapt the strands-langfuse pattern
- **For custom needs**: Start with weather_agent and add features as needed

Both implementations follow Strands + Langfuse best practices and demonstrate the flexibility of the integration approach.