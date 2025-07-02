# Agent Metrics and Observability Proposal

## 1. Introduction

This document proposes a standardized framework for implementing comprehensive metrics and observability within the Strands Weather Agent. The goal is to provide deep insights into the agent's performance, reliability, and operational health. Adopting this framework will enable us to:

-   Proactively identify and diagnose issues.
-   Monitor performance and latency in real-time.
-   Understand tool usage and LLM interactions.
-   Make data-driven decisions for improvements and scaling.

## 2. Current State

The project currently has some observability features, but they are fragmented:

-   **Structured Logging:** The agent uses Python's `logging` module with a `debug_logging` flag for verbose output. Logs are sent to CloudWatch, but lack consistent correlation with specific requests or traces.
-   **ECS Metrics:** The service relies on basic AWS ECS metrics like CPU utilization for auto-scaling, as defined in `infra/services.cfn`.
-   **Fragmented Mentions:** Documents like `STRANDS_DEFINITIVE_GUIDE.md` and `context.md` mention **OpenTelemetry** and custom metric counters (`Counter`, `Gauge`), indicating an intent to adopt a more robust system, but a unified implementation is missing.

This proposal aims to unify these efforts under a single, industry-standard framework.

## 3. Proposed Solution: OpenTelemetry

We propose adopting **OpenTelemetry (OTel)** as the standard for instrumenting the agent to collect metrics, traces, and logs.

**Why OpenTelemetry?**

-   **Industry Standard:** It is a CNCF-backed open standard, ensuring vendor-neutrality and long-term viability.
-   **Unified Observability:** It provides a single set of APIs and libraries for all three pillars of observability:
    1.  **Metrics:** Quantitative data about processes (e.g., request counts, latency).
    2.  **Traces:** A record of the entire lifecycle of a request as it flows through the system.
    3.  **Logs:** Text records of events, enriched with trace and span IDs for correlation.
-   **AWS Integration:** It integrates seamlessly with AWS services via the **AWS Distro for OpenTelemetry**, which can export data directly to **Amazon CloudWatch** and **AWS X-Ray**.

### 3.1. Key Metrics to Implement

We will start with a core set of metrics to provide immediate value:

| Metric Name                  | Type      | Description                                                                 | Dimensions/Attributes        |
| ---------------------------- | --------- | --------------------------------------------------------------------------- | ---------------------------- |
| `agent.invocations.count`    | Counter   | Total number of times the agent is invoked.                                 | `model_id`, `prompt_template`  |
| `agent.invocations.duration` | Histogram | The end-to-end latency of agent invocations, in milliseconds.               | `model_id`                   |
| `agent.errors.count`         | Counter   | The number of failed agent invocations.                                     | `error_type`                 |
| `tool.calls.count`           | Counter   | The number of times a specific tool is called by the agent.                 | `tool_name`                  |
| `tool.calls.duration`        | Histogram | The latency of individual tool calls, in milliseconds.                      | `tool_name`                  |
| `tool.errors.count`          | Counter   | The number of failed tool calls.                                            | `tool_name`, `error_type`    |
| `llm.tokens.total`           | Counter   | The total number of tokens processed by the LLM.                            | `model_id`, `token_type` (input/output) |
| `cache.hits.count`           | Counter   | The number of times a valid response was found in the cache.                | `cache_name`                 |
| `cache.misses.count`         | Counter   | The number of times a response was not found in the cache.                  | `cache_name`                 |

### 3.2. Distributed Tracing

We will use OpenTelemetry Tracing to capture the entire journey of a request. A single trace will connect the initial API call to the agent, the LLM invocation, and all subsequent tool calls. This is invaluable for debugging complex chains and identifying performance bottlenecks.

## 4. Implementation Plan

We will create a centralized telemetry module (`weather_agent/telemetry.py`) to initialize and configure OpenTelemetry.

**`weather_agent/telemetry.py`:**
```python
import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# ... similar setup for Metrics and Logs

def initialize_telemetry():
    """
    Initializes OpenTelemetry tracing, metrics, and logging.
    Configured to export to AWS CloudWatch and X-Ray.
    """
    # Setup based on environment variables
    # (OTEL_EXPORTER_OTLP_ENDPOINT, etc.)
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # ... setup for metrics provider

    print("Telemetry initialized.")

def get_tracer(name: str):
    return trace.get_tracer(name)
```

**`weather_agent/mcp_agent.py` modifications:**
```python
# ... other imports
from . import telemetry

tracer = telemetry.get_tracer(__name__)

class MCPWeatherAgent:
    def __init__(self, ...):
        # ...
        # OTel meter for metrics
        # self.meter = telemetry.get_meter(__name__)
        # self.invocation_counter = self.meter.create_counter(...)

    @tracer.start_as_current_span("mcp_agent.invoke")
    async def invoke(self, query: str):
        # self.invocation_counter.add(1)
        span = trace.get_current_span()
        span.set_attribute("agent.query", query)

        # ... existing logic ...

        # Instrument tool calls
        with tracer.start_as_current_span("mcp_agent.tool_call") as tool_span:
            tool_span.set_attribute("tool.name", tool_name)
            # ... call tool ...
```

### 4.1. Backend Configuration

-   **Collector:** We will use the AWS Distro for OpenTelemetry Collector, configured to run as a sidecar container in the ECS task definition.
-   **Exporters:** The collector will be configured to export:
    -   Traces to **AWS X-Ray**.
    -   Metrics and Logs to **Amazon CloudWatch**.
-   **Configuration:** All configuration will be managed via environment variables set in `bedrock.env` and the ECS task definition.

## 5. Dashboarding and Alerting

-   **CloudWatch Dashboard:** A new dashboard named `StrandsWeatherAgent-Health` will be created to visualize the key metrics defined above.
-   **CloudWatch Alarms:** We will configure alarms for critical conditions, such as:
    -   High P95 `agent.invocations.duration`.
    -   Spike in `agent.errors.count`.
    -   Anomalous `tool.errors.count` for a specific tool.

## 6. Phased Rollout

1.  **Phase 1 (Core Metrics & Tracing Setup):**
    -   Implement `weather_agent/telemetry.py`.
    -   Add basic instrumentation for agent invocation count, duration, and errors.
    -   Set up the OTel collector and export pipeline to CloudWatch/X-Ray.
    -   Create the initial CloudWatch dashboard.

2.  **Phase 2 (Tool & LLM Metrics):**
    -   Instrument all tool calls to capture duration, counts, and errors.
    -   Add metrics for LLM token usage.
    -   Enhance the dashboard with tool-specific visualizations.

3.  **Phase 3 (Log Correlation & Advanced Features):**
    -   Configure the logging instrumentation to inject `trace_id` and `span_id` into all logs.
    -   Implement cache metrics as proposed in `realistic-caching-improvements.md`.
    -   Set up automated alerting based on the new metrics.

## 7. Conclusion

This proposal outlines a clear path to establishing robust observability for the Strands Weather Agent. By adopting OpenTelemetry and integrating tightly with AWS monitoring services, we can significantly improve the reliability, performance, and maintainability of the system. We seek approval to begin with Phase 1 of the implementation.
