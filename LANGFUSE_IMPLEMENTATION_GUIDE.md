# Langfuse Implementation Guide for AWS Strands Agents

**⚠️ CRITICAL UPDATES (January 2025)**: This guide has been updated based on extensive real-world implementation experience. Key differences from previous documentation:
- **Signal-specific endpoint** is REQUIRED (not `/api/public/otel`, use `/api/public/otel/v1/traces`)
- **Explicit telemetry initialization** is REQUIRED (not automatic)
- **Environment variables MUST be set BEFORE imports** (critical for OTEL to work)
- **TracerProvider override warnings** are expected and can be mitigated
- **Force flush** is critical for short-lived scripts

This comprehensive guide provides step-by-step instructions for integrating Langfuse observability into AWS Strands Agents applications. Langfuse is an open-source LLM engineering platform that provides advanced tracing, monitoring, and evaluation capabilities for AI applications.

## Table of Contents

1. [Introduction to Langfuse](#introduction-to-langfuse)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Basic Implementation](#basic-implementation)
5. [Advanced Features](#advanced-features)
6. [Evaluation and Scoring](#evaluation-and-scoring)
7. [AWS Deployment Patterns](#aws-deployment-patterns)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Reference Examples](#reference-examples)

## Introduction to Langfuse

Langfuse is a comprehensive observability platform specifically designed for LLM applications. It provides:

- **Distributed Tracing**: Track complex multi-step agent workflows
- **Token Usage Monitoring**: Monitor costs and optimize token consumption
- **Performance Analytics**: Analyze latency, throughput, and error rates
- **Evaluation Integration**: Score outputs and track quality metrics
- **Prompt Management**: Version and manage prompts with performance tracking
- **User Analytics**: Track user interactions and session flows

### Why Langfuse for Strands Agents?

AWS Strands Agents natively supports OpenTelemetry (OTEL), making Langfuse integration seamless:

1. **Native OTEL Support**: Strands automatically exports traces in OTEL format
2. **Rich Semantic Conventions**: GenAI-specific attributes are captured automatically
3. **Tool Tracking**: Every tool execution is traced with inputs/outputs
4. **Multi-Turn Support**: Sessions and conversations are tracked coherently
5. **Cost Visibility**: Token usage and API costs are tracked per operation

## Quick Start

### Prerequisites

```bash
# Install Strands with OTEL support
pip install strands-agents>=0.2.0

# Install python-dotenv for environment management
pip install python-dotenv

# Install Langfuse SDK for evaluation (optional)
pip install langfuse
```

### ⚠️ CRITICAL: Correct Implementation Pattern

```python
import os
import base64
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Configure Langfuse authentication
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-...")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-...")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Create auth token for OTEL authentication
auth_token = base64.b64encode(f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()).decode()

# CRITICAL: Set OTEL environment variables BEFORE importing Strands
# Use signal-specific endpoint (NOT the generic /api/public/otel)
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{LANGFUSE_HOST}/api/public/otel/v1/traces"
os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth_token}"
os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"
os.environ["OTEL_SERVICE_NAME"] = "strands-agent"

# NOW import Strands after setting environment variables
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.telemetry import StrandsTelemetry

# CRITICAL: Initialize telemetry explicitly - this is NOT automatic!
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()

# Create agent with trace attributes
agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
    trace_attributes={
        "session.id": "session-123",
        "user.id": "user@example.com",
        "environment": "production",
        "langfuse.tags": ["strands", "demo"]
    }
)

# Execute agent - traces are sent to Langfuse
result = agent("What is 2+2?")
print(f"Response: {result}")
print(f"Tokens used: {result.metrics.accumulated_usage['totalTokens']}")

# CRITICAL: Force flush telemetry for short-lived scripts
if hasattr(telemetry, 'tracer_provider') and hasattr(telemetry.tracer_provider, 'force_flush'):
    telemetry.tracer_provider.force_flush()
```

## 🚨 Critical Implementation Details

### Common Mistakes and Their Solutions

Based on extensive real-world implementation experience, here are the most critical issues developers encounter:

#### 1. ❌ WRONG: Using Generic OTEL Endpoint
```python
# This will return 404 errors!
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = f"{LANGFUSE_HOST}/api/public/otel"
```

#### ✅ CORRECT: Use Signal-Specific Endpoint
```python
# Use the traces-specific endpoint
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{LANGFUSE_HOST}/api/public/otel/v1/traces"
```

#### 2. ❌ WRONG: Setting Environment Variables After Import
```python
from strands import Agent  # OTEL config is read during import!
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "..."  # Too late!
```

#### ✅ CORRECT: Set Environment Variables Before Import
```python
# Set all OTEL config FIRST
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "..."
os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = "..."

# THEN import Strands
from strands import Agent
```

#### 3. ❌ WRONG: Expecting Automatic Telemetry
```python
# Just creating an agent doesn't initialize telemetry
agent = Agent(model=BedrockModel(...))
```

#### ✅ CORRECT: Explicit Telemetry Initialization
```python
from strands.telemetry import StrandsTelemetry

# Must explicitly initialize
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()

# Now create agent
agent = Agent(model=BedrockModel(...))
```

#### 4. ❌ WRONG: Not Flushing Telemetry
```python
result = agent("query")
# Script ends - traces may not be sent!
```

#### ✅ CORRECT: Force Flush Before Exit
```python
result = agent("query")

# Ensure traces are sent
telemetry.tracer_provider.force_flush()
```

### Handling TracerProvider Warnings

You may see warnings like:
```
Overriding of current TracerProvider is not allowed
```

This happens when:
- Multiple agents are created in the same process
- Telemetry is re-initialized
- Running multiple scripts in sequence

**Solutions:**
1. **Initialize telemetry once** at the application level
2. **Reuse the telemetry instance** across agents
3. **Use a singleton pattern** for production applications

```python
# Singleton pattern for telemetry
class TelemetryManager:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self):
        if not self._initialized:
            self.telemetry = StrandsTelemetry()
            self.telemetry.setup_otlp_exporter()
            self._initialized = True
        return self.telemetry

# Use throughout your application
telemetry_manager = TelemetryManager()
telemetry = telemetry_manager.initialize()
```

## Core Concepts

### 1. Traces and Observations

Langfuse organizes telemetry data hierarchically:

```
Trace (top-level request)
├── Agent Span
│   ├── Cycle 1 Span
│   │   ├── Model Generation
│   │   └── Tool Execution
│   └── Cycle 2 Span
│       └── Model Generation
└── Metadata & Scores
```

### 2. Key Attributes

Strands automatically captures these attributes:

| Attribute | Description | Example |
|-----------|-------------|---------|
| `gen_ai.system` | System identifier | "strands-agents" |
| `gen_ai.agent.name` | Agent name | "MyAgent" |
| `gen_ai.request.model` | Model ID | "us.amazon.nova-premier-v1:0" |
| `gen_ai.prompt` | Input prompt | "What is 2+2?" |
| `gen_ai.completion` | Model response | "2+2 equals 4" |
| `gen_ai.usage.*` | Token counts | inputTokens, outputTokens |
| `tool.name` | Tool identifier | "calculator" |
| `tool.parameters` | Tool inputs | {"expression": "2+2"} |

### 3. Custom Attributes

Add business context through trace attributes:

```python
trace_attributes = {
    # Langfuse-specific
    "session.id": "abc-123",
    "user.id": "user@example.com",
    "langfuse.tags": ["production", "v2.0"],
    
    # Business context
    "customer.tier": "premium",
    "workflow.type": "data-analysis",
    "feature.flags": "advanced-tools"
}
```

## Basic Implementation

### Step 1: Environment Configuration (Corrected)

```python
import os
import base64
from dotenv import load_dotenv

# CRITICAL: Load .env file BEFORE any configuration
load_dotenv()

def configure_langfuse(public_key: str = None, secret_key: str = None, host: str = None):
    """Configure Langfuse OTEL export with proper patterns"""
    # Use environment variables with fallbacks
    public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
    host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    if not public_key or not secret_key:
        raise ValueError("Langfuse credentials not provided")
    
    # Create auth token
    auth_token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    
    # CRITICAL: Use signal-specific endpoint with /v1/traces
    endpoint = f"{host}/api/public/otel/v1/traces"
    
    # Configure OTEL - MUST use TRACES-specific variables
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = endpoint
    os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth_token}"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"
    
    # Optional but recommended
    os.environ["OTEL_SERVICE_NAME"] = os.getenv("OTEL_SERVICE_NAME", "strands-agent")
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = os.getenv(
        "OTEL_RESOURCE_ATTRIBUTES",
        "service.version=1.0.0,deployment.environment=production"
    )
    
    return endpoint

# CRITICAL: Configure BEFORE any Strands imports
endpoint = configure_langfuse()
print(f"Configured Langfuse endpoint: {endpoint}")

# NOW import Strands
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.telemetry import StrandsTelemetry
```

### Step 2: Agent Creation with Context (Corrected)

```python
# Assumes Step 1 has been completed (environment configured, imports done)
import uuid

# CRITICAL: Initialize telemetry explicitly - NOT automatic!
print("Initializing StrandsTelemetry...")
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()
print("✅ OTLP exporter configured")

# Create agent with rich context
agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
    system_prompt="You are a helpful AI assistant",
    tools=[calculator, web_search, data_analyzer] if 'calculator' in locals() else [],
    trace_attributes={
        # Session management
        "session.id": str(uuid.uuid4()),
        "user.id": "user@example.com",
        
        # Langfuse tags for filtering
        "langfuse.tags": ["production", "customer-support", "v2.1"],
        
        # Business context
        "customer.tier": "enterprise",
        "department": "sales",
        "region": "us-west-2"
    }
)

# IMPORTANT: Keep reference to telemetry for force flush later
agent._telemetry = telemetry
```

### Step 3: Conversation Tracking

```python
class ConversationManager:
    """Manage multi-turn conversations with Langfuse session tracking"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session_id = str(uuid.uuid4())
        self.conversation_history = []
        
        # Create agent with session context
        self.agent = Agent(
            model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
            trace_attributes={
                "session.id": self.session_id,
                "user.id": self.user_id,
                "langfuse.tags": ["conversation", "interactive"]
            }
        )
    
    def send_message(self, message: str) -> str:
        """Send message and track in session"""
        # Add to history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Get response
        response = self.agent(message)
        
        # Track response
        self.conversation_history.append({
            "role": "assistant", 
            "content": str(response),
            "metrics": {
                "tokens": response.metrics.accumulated_usage['totalTokens'],
                "latency_ms": response.metrics.accumulated_metrics['latencyMs']
            }
        })
        
        return str(response)

# Usage
conversation = ConversationManager("user@example.com")
response1 = conversation.send_message("What's the weather like?")
response2 = conversation.send_message("Should I bring an umbrella?")
```

## Advanced Features

### 1. Tool Usage Tracking

Strands automatically traces tool executions, but you can add custom metadata:

```python
from strands import tool

@tool
def analyze_data(query: str, dataset: str) -> str:
    """Analyze data with custom tracking"""
    # Tool execution is automatically traced
    # Add custom spans for detailed tracking
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("data_loading") as span:
        span.set_attribute("dataset.name", dataset)
        span.set_attribute("dataset.size", "1.2GB")
        # Load data...
    
    with tracer.start_as_current_span("analysis") as span:
        span.set_attribute("analysis.type", "statistical")
        # Perform analysis...
    
    return "Analysis complete"
```

### 2. Error Tracking and Debugging

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

def robust_agent_execution(agent, prompt):
    """Execute agent with enhanced error tracking"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("agent_execution") as span:
        span.set_attribute("prompt.length", len(prompt))
        
        try:
            result = agent(prompt)
            
            # Add success metrics
            span.set_attribute("execution.success", True)
            span.set_attribute("tokens.total", result.metrics.accumulated_usage['totalTokens'])
            span.set_attribute("cycles.count", result.metrics.cycle_count)
            
            return result
            
        except Exception as e:
            # Track error details
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("execution.success", False)
            span.set_attribute("error.type", type(e).__name__)
            
            # Log to Langfuse for debugging
            print(f"Error in agent execution: {e}")
            raise
```

### 3. Custom Metrics Export

```python
class LangfuseMetricsExporter:
    """Export custom metrics to Langfuse"""
    
    def __init__(self):
        self.metrics_buffer = []
    
    def track_custom_metric(self, name: str, value: float, attributes: dict = None):
        """Track custom business metrics"""
        from opentelemetry import trace
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span(f"metric.{name}") as span:
            span.set_attribute("metric.name", name)
            span.set_attribute("metric.value", value)
            
            if attributes:
                for key, val in attributes.items():
                    span.set_attribute(f"metric.{key}", val)
    
    def track_business_outcome(self, agent_result, outcome: str, value: float):
        """Track business outcomes from agent interactions"""
        self.track_custom_metric(
            "business_outcome",
            value,
            {
                "outcome_type": outcome,
                "tokens_used": agent_result.metrics.accumulated_usage['totalTokens'],
                "latency_ms": agent_result.metrics.accumulated_metrics['latencyMs'],
                "tool_calls": sum(m.call_count for m in agent_result.metrics.tool_metrics.values())
            }
        )

# Usage
exporter = LangfuseMetricsExporter()
result = agent("Generate a sales proposal for ACME Corp")
exporter.track_business_outcome(result, "proposal_generated", 1000.0)  # $1000 value
```

## Evaluation and Scoring

### 1. Using Langfuse SDK for Evaluation

```python
from langfuse import Langfuse
import time

class LangfuseEvaluator:
    """Evaluate agent outputs using Langfuse"""
    
    def __init__(self, public_key: str, secret_key: str):
        self.langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key
        )
    
    def evaluate_agent_response(self, trace_id: str, response: str, expected: str = None):
        """Score agent response quality"""
        # Wait for trace to be indexed
        time.sleep(2)
        
        # Retrieve trace
        trace = self.langfuse.get_trace(trace_id)
        
        # Calculate scores
        scores = []
        
        # Accuracy score (if expected output provided)
        if expected:
            accuracy = 1.0 if response.strip() == expected.strip() else 0.0
            scores.append({
                "name": "accuracy",
                "value": accuracy,
                "comment": f"Expected: {expected[:50]}..."
            })
        
        # Response quality score (can use LLM-as-judge)
        quality_score = self._calculate_quality_score(response)
        scores.append({
            "name": "quality",
            "value": quality_score,
            "comment": "Based on coherence, completeness, and relevance"
        })
        
        # Submit scores
        for score in scores:
            self.langfuse.score(
                trace_id=trace_id,
                name=score["name"],
                value=score["value"],
                comment=score["comment"]
            )
        
        return scores
    
    def _calculate_quality_score(self, response: str) -> float:
        """Calculate response quality (simplified)"""
        # In practice, use LLM-as-judge or more sophisticated metrics
        score = 1.0
        
        # Penalize very short responses
        if len(response) < 10:
            score *= 0.5
        
        # Penalize responses without punctuation
        if not any(p in response for p in ['.', '!', '?']):
            score *= 0.8
        
        return score
```

### 2. RAGAS Integration Example

```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
import pandas as pd

class RAGASLangfuseIntegration:
    """Integrate RAGAS evaluation with Langfuse"""
    
    def __init__(self, langfuse_client):
        self.langfuse = langfuse_client
    
    def evaluate_rag_pipeline(self, agent, test_questions: list):
        """Evaluate RAG pipeline using RAGAS"""
        results = []
        
        for question in test_questions:
            # Execute agent
            response = agent(question)
            
            # Prepare data for RAGAS
            data = {
                'question': [question],
                'answer': [str(response)],
                'contexts': [[]]  # Extract from agent if using RAG
            }
            
            # Run RAGAS evaluation
            dataset = pd.DataFrame(data)
            scores = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy]
            )
            
            # Push scores to Langfuse
            trace_id = self._get_trace_id_from_context()
            
            for metric, value in scores.items():
                self.langfuse.score(
                    trace_id=trace_id,
                    name=f"ragas_{metric}",
                    value=value,
                    comment=f"RAGAS {metric} score"
                )
            
            results.append({
                'question': question,
                'response': str(response),
                'scores': scores
            })
        
        return results
```

## AWS Deployment Patterns

### 1. Lambda Deployment with Langfuse

```python
# lambda_function.py
import os
import json
import base64
from strands import Agent
from strands.models.bedrock import BedrockModel
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Configure Langfuse on cold start
def configure_langfuse_from_secrets():
    """Load Langfuse config from AWS Secrets Manager"""
    import boto3
    
    secrets_client = boto3.client('secretsmanager')
    secret = secrets_client.get_secret_value(SecretId='langfuse-credentials')
    creds = json.loads(secret['SecretString'])
    
    auth_token = base64.b64encode(
        f"{creds['public_key']}:{creds['secret_key']}".encode()
    ).decode()
    
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = creds['endpoint']
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_token}"

# Configure on cold start
configure_langfuse_from_secrets()

# Initialize agent
agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
    trace_attributes={
        "deployment.type": "lambda",
        "aws.lambda.function_name": os.environ.get("AWS_LAMBDA_FUNCTION_NAME"),
        "aws.region": os.environ.get("AWS_REGION")
    }
)

@tracer.capture_lambda_handler
@logger.inject_lambda_context
@metrics.log_metrics
def lambda_handler(event, context):
    """Lambda handler with Langfuse tracing"""
    try:
        body = json.loads(event['body'])
        prompt = body['prompt']
        user_id = body.get('user_id', 'anonymous')
        session_id = body.get('session_id')
        
        # Update trace attributes for this request
        agent.trace_attributes.update({
            "user.id": user_id,
            "session.id": session_id,
            "lambda.request_id": context.request_id
        })
        
        # Execute agent
        result = agent(prompt)
        
        # Log metrics
        metrics.add_metric(
            name="TokensUsed",
            value=result.metrics.accumulated_usage['totalTokens'],
            unit=MetricUnit.Count
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response': str(result),
                'usage': result.metrics.accumulated_usage,
                'trace_id': context.request_id
            })
        }
        
    except Exception as e:
        logger.exception("Error in agent execution")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### 2. ECS/Fargate Deployment

```yaml
# task-definition.json
{
  "family": "strands-langfuse",
  "taskRoleArn": "arn:aws:iam::123456789012:role/strands-task-role",
  "executionRoleArn": "arn:aws:iam::123456789012:role/strands-execution-role",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "strands-agent",
      "image": "your-ecr-repo/strands-agent:latest",
      "environment": [
        {
          "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
          "value": "https://cloud.langfuse.com/api/public/otel/v1/traces"
        },
        {
          "name": "OTEL_SERVICE_NAME",
          "value": "strands-agent-ecs"
        },
        {
          "name": "OTEL_RESOURCE_ATTRIBUTES",
          "value": "deployment.environment=production,service.version=1.0.0"
        }
      ],
      "secrets": [
        {
          "name": "OTEL_EXPORTER_OTLP_HEADERS",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:langfuse-auth-header"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/strands-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 3. Multi-Region Setup

```python
class MultiRegionLangfuseConfig:
    """Configure Langfuse for multi-region deployments"""
    
    ENDPOINTS = {
        "us-east-1": "https://us.cloud.langfuse.com/api/public/otel/v1/traces",
        "eu-west-1": "https://cloud.langfuse.com/api/public/otel/v1/traces",
        "ap-southeast-1": "https://us.cloud.langfuse.com/api/public/otel/v1/traces"
    }
    
    @classmethod
    def configure_for_region(cls, aws_region: str, public_key: str, secret_key: str):
        """Configure Langfuse endpoint based on AWS region"""
        # Map AWS region to nearest Langfuse endpoint
        if aws_region.startswith("us-"):
            endpoint = cls.ENDPOINTS["us-east-1"]
        elif aws_region.startswith("eu-"):
            endpoint = cls.ENDPOINTS["eu-west-1"]
        elif aws_region.startswith("ap-"):
            endpoint = cls.ENDPOINTS["ap-southeast-1"]
        else:
            # Default to US endpoint
            endpoint = cls.ENDPOINTS["us-east-1"]
        
        # Configure OTEL
        auth_token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
        os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = endpoint
        os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_token}"
        
        # Add region to resource attributes
        os.environ["OTEL_RESOURCE_ATTRIBUTES"] = f"aws.region={aws_region}"
        
        return endpoint

# Usage
MultiRegionLangfuseConfig.configure_for_region(
    aws_region="us-west-2",
    public_key="pk-lf-...",
    secret_key="sk-lf-..."
)
```

## Production Implementation Patterns

### Proper Initialization for Web Applications

```python
# app.py or main.py
import os
import base64
from dotenv import load_dotenv

# Load environment FIRST
load_dotenv()

# Configure OTEL BEFORE imports
def setup_langfuse():
    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    
    os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{host}/api/public/otel/v1/traces"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"
    os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"

# Configure before imports
setup_langfuse()

# NOW import your application
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.telemetry import StrandsTelemetry

# Initialize telemetry ONCE
_telemetry = None

def get_telemetry():
    global _telemetry
    if _telemetry is None:
        _telemetry = StrandsTelemetry()
        _telemetry.setup_otlp_exporter()
    return _telemetry

# Initialize on startup
telemetry = get_telemetry()

# Create agents as needed
def create_agent(session_id: str, user_id: str):
    return Agent(
        model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
        trace_attributes={
            "session.id": session_id,
            "user.id": user_id,
            "langfuse.tags": ["production"]
        }
    )
```

### MCP Server Integration Pattern

When using MCP servers with Langfuse:

```python
# Initialize everything in the correct order
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

# 1. Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path, override=True)

# 2. Configure OTEL
auth = base64.b64encode(
    f"{os.getenv('LANGFUSE_PUBLIC_KEY')}:{os.getenv('LANGFUSE_SECRET_KEY')}".encode()
).decode()

os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{os.getenv('LANGFUSE_HOST')}/api/public/otel/v1/traces"
os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"

# 3. Import after configuration
from strands import Agent
from strands.telemetry import StrandsTelemetry
from strands.tools.registry import ToolRegistry

# 4. Initialize telemetry
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()

# 5. MCP servers will be traced automatically
```

## Best Practices

### 1. Trace Attribute Standards

```python
# Recommended trace attribute schema
TRACE_ATTRIBUTES = {
    # Required for Langfuse
    "session.id": "unique-session-id",
    "user.id": "user-identifier",
    
    # Recommended tags
    "langfuse.tags": ["environment", "version", "feature"],
    
    # Business context
    "customer.tier": "enterprise|pro|free",
    "workflow.type": "chat|analysis|generation",
    "deployment.environment": "production|staging|development",
    
    # Feature flags
    "features.enabled": "feature1,feature2",
    
    # Cost tracking
    "cost.center": "department-name",
    "cost.category": "customer-support|internal"
}
```

### 2. Performance Optimization

```python
class OptimizedLangfuseAgent:
    """Agent with optimized Langfuse integration"""
    
    def __init__(self):
        # Use batch span processor for better performance
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        
        # Configure batch processor
        span_processor = BatchSpanProcessor(
            OTLPSpanExporter(),
            max_queue_size=2048,
            max_export_batch_size=512,
            max_export_interval_millis=5000
        )
        
        # Set custom tracer provider
        provider = TracerProvider()
        provider.add_span_processor(span_processor)
        trace.set_tracer_provider(provider)
        
        # Initialize agent
        self.agent = Agent(
            model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
            trace_attributes={"optimized": True}
        )
```

### 3. Privacy and Security

```python
class SecureLangfuseAgent:
    """Agent with privacy-preserving Langfuse integration"""
    
    def __init__(self):
        self.agent = Agent(
            model=BedrockModel(model_id="us.amazon.nova-premier-v1:0")
        )
    
    def execute_with_privacy(self, prompt: str, user_id: str):
        """Execute agent with PII protection"""
        # Hash user ID for privacy
        import hashlib
        hashed_user_id = hashlib.sha256(user_id.encode()).hexdigest()[:16]
        
        # Update trace attributes
        self.agent.trace_attributes.update({
            "user.id": hashed_user_id,
            "privacy.mode": "enabled"
        })
        
        # Sanitize prompt (remove potential PII)
        sanitized_prompt = self._sanitize_prompt(prompt)
        
        # Execute with sanitized data
        return self.agent(sanitized_prompt)
    
    def _sanitize_prompt(self, prompt: str) -> str:
        """Remove potential PII from prompts"""
        import re
        
        # Remove email addresses
        prompt = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', prompt)
        
        # Remove phone numbers
        prompt = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', prompt)
        
        # Remove SSN-like patterns
        prompt = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', prompt)
        
        return prompt
```

## Troubleshooting

### 1. No Traces in Langfuse - Common Causes

```python
def debug_langfuse_connection():
    """Debug Langfuse connectivity issues - CORRECTED VERSION"""
    import requests
    import os
    from base64 import b64encode
    
    print("🔍 Langfuse Debug Tool")
    print("=" * 50)
    
    # Check CRITICAL environment variables
    traces_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    traces_headers = os.environ.get("OTEL_EXPORTER_OTLP_TRACES_HEADERS")
    
    # Common mistake - check generic endpoint
    generic_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    print("✅ Checking endpoints:")
    print(f"  TRACES endpoint: {traces_endpoint or '❌ NOT SET (REQUIRED!)'}")
    print(f"  Generic endpoint: {generic_endpoint or '✓ Not set (correct)'}")
    
    if generic_endpoint and not traces_endpoint:
        print("\n❌ ERROR: Using generic endpoint instead of traces-specific!")
        print("   Fix: Use OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    
    print(f"\n✅ Headers configured: {'Yes' if traces_headers else '❌ No'}")
    
    # Check if imports were done before config
    try:
        import strands
        print("\n⚠️  WARNING: Strands already imported!")
        print("   If you set OTEL env vars after import, they won't work!")
    except ImportError:
        print("\n✓ Good: Strands not imported yet")
    
    # Test Langfuse connectivity
    if traces_endpoint and traces_headers:
        try:
            # Extract auth from headers
            auth_value = traces_headers.split("=", 1)[1]
            
            # Get base URL
            base_url = traces_endpoint.replace("/api/public/otel/v1/traces", "")
            health_url = f"{base_url}/api/public/health"
            
            response = requests.get(
                health_url,
                headers={"Authorization": auth_value},
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"\n✅ Langfuse reachable: {response.json()}")
            else:
                print(f"\n❌ Langfuse returned: {response.status_code}")
        except Exception as e:
            print(f"\n❌ Connection failed: {e}")
    
    # Check telemetry initialization
    try:
        from strands.telemetry import StrandsTelemetry
        telemetry = StrandsTelemetry()
        if hasattr(telemetry, 'tracer_provider'):
            print("\n✅ StrandsTelemetry can be initialized")
        else:
            print("\n❌ StrandsTelemetry missing tracer_provider")
    except Exception as e:
        print(f"\n❌ Cannot initialize StrandsTelemetry: {e}")

# Run diagnostics
debug_langfuse_connection()
```

### Common Issues and Solutions

#### Issue: "Failed to export batch code: 404"
```
Failed to export batch code: 404, reason: <!DOCTYPE html>...
```

**Cause**: Using the wrong endpoint
**Solution**: Use `/api/public/otel/v1/traces` NOT `/api/public/otel`

#### Issue: "Overriding of current TracerProvider is not allowed"
**Cause**: Multiple telemetry initializations
**Solution**: Initialize telemetry once at application startup

#### Issue: No traces despite successful execution
**Causes**:
1. Environment variables set after importing Strands
2. Not calling `telemetry.setup_otlp_exporter()`
3. Not flushing telemetry before script ends

**Solution**:
```python
# Correct order
import os
os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = "..."  # 1. Config first

from strands import Agent  # 2. Import second
from strands.telemetry import StrandsTelemetry

telemetry = StrandsTelemetry()  # 3. Initialize
telemetry.setup_otlp_exporter()

# ... use agent ...

telemetry.tracer_provider.force_flush()  # 4. Flush before exit
```

### 2. Missing Tool Traces

```python
# Ensure tools are properly registered
from strands.tools.registry import ToolRegistry

def verify_tool_tracing():
    """Verify tools are being traced"""
    registry = ToolRegistry()
    
    print("Registered tools:")
    for tool_name, tool_info in registry._tools.items():
        print(f"  - {tool_name}: {tool_info}")
    
    # Test tool execution with explicit tracing
    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("tool_test") as span:
        # Tool execution happens here
        result = agent("Use the calculator to compute 2+2")
        
        # Check if tool was called
        tool_metrics = result.metrics.tool_metrics
        print(f"Tools used: {list(tool_metrics.keys())}")
```

### 3. Performance Issues

```python
class PerformanceMonitor:
    """Monitor Langfuse export performance"""
    
    def __init__(self):
        self.export_times = []
    
    def measure_export_latency(self, agent, prompt):
        """Measure trace export latency"""
        import time
        
        # Execute with timing
        start = time.time()
        result = agent(prompt)
        execution_time = time.time() - start
        
        # Wait for export (batch processor default is 5s)
        time.sleep(6)
        
        # Check Langfuse for trace
        # In practice, use Langfuse API to verify trace arrival
        
        print(f"Execution time: {execution_time:.2f}s")
        print(f"Tokens: {result.metrics.accumulated_usage['totalTokens']}")
        
        # Recommendations
        if execution_time > 10:
            print("Consider using batch processing for better performance")
        if result.metrics.accumulated_usage['totalTokens'] > 4000:
            print("High token usage may impact export size")
```

## Reference Examples

### Complete Working Example (Corrected)

```python
#!/usr/bin/env python3
"""
Complete Langfuse + Strands implementation example
Shows the CORRECT order and patterns
"""

import os
import base64
import uuid
from datetime import datetime
from dotenv import load_dotenv

# STEP 1: Load environment variables FIRST
load_dotenv()

# STEP 2: Configure Langfuse BEFORE any Strands imports
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "pk-lf-...")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "sk-lf-...")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Create auth token
auth_token = base64.b64encode(
    f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()
).decode()

# CRITICAL: Use TRACES-specific endpoint and environment variables
os.environ.update({
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": f"{LANGFUSE_HOST}/api/public/otel/v1/traces",
    "OTEL_EXPORTER_OTLP_TRACES_HEADERS": f"Authorization=Basic {auth_token}",
    "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/protobuf",
    "OTEL_SERVICE_NAME": "strands-demo",
    "OTEL_RESOURCE_ATTRIBUTES": "service.version=1.0.0,deployment.environment=demo"
})

print("✅ Langfuse OTEL configured")

# STEP 3: NOW import Strands (after configuration)
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.telemetry import StrandsTelemetry

# STEP 4: Initialize telemetry explicitly
print("🔧 Initializing StrandsTelemetry...")
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()
print("✅ OTLP exporter configured")

# STEP 5: Define tools
@tool
def get_current_time() -> str:
    """Get the current time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression"""
    try:
        result = eval(expression)
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"

# STEP 6: Create agent with full context
agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
    system_prompt="You are a helpful AI assistant with calculation and time capabilities.",
    tools=[get_current_time, calculate],
    trace_attributes={
        "session.id": str(uuid.uuid4()),
        "user.id": "demo-user@example.com",
        "langfuse.tags": ["demo", "complete-example"],
        "demo.type": "full-integration"
    }
)

# STEP 7: Execute agent
print("\n🚀 Executing agent...")
result = agent("What time is it? Also, calculate 42 * 17 for me.")

print(f"\n📝 Response: {result}")
print(f"\n📊 Metrics:")
print(f"  Total tokens: {result.metrics.accumulated_usage['totalTokens']}")
print(f"  Latency: {result.metrics.accumulated_metrics['latencyMs']}ms")
print(f"  Cycles: {result.metrics.cycle_count}")
print(f"  Tools used: {list(result.metrics.tool_metrics.keys())}")

# STEP 8: CRITICAL - Force flush telemetry
print("\n🔄 Flushing telemetry...")
if hasattr(telemetry, 'tracer_provider') and hasattr(telemetry.tracer_provider, 'force_flush'):
    telemetry.tracer_provider.force_flush()
    print("✅ Telemetry flushed")

# STEP 9: Add evaluation (optional)
# Import Langfuse SDK only if needed for scoring
from langfuse import Langfuse

langfuse_client = Langfuse(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST
)

# Wait for trace to be indexed
import time
print("\n⏳ Waiting for trace indexing...")
time.sleep(3)

# Find and score the trace
traces = langfuse_client.get_traces(limit=1)
if traces:
    latest_trace = traces[0]
    
    # Add quality score
    langfuse_client.score(
        trace_id=latest_trace.id,
        name="demo_quality",
        value=0.95,
        comment="High quality response with correct tool usage"
    )
    
    # Add performance score
    performance_score = 1.0 if result.metrics.accumulated_metrics['latencyMs'] < 5000 else 0.5
    langfuse_client.score(
        trace_id=latest_trace.id,
        name="demo_performance",
        value=performance_score,
        comment=f"Latency: {result.metrics.accumulated_metrics['latencyMs']}ms"
    )
    
    print(f"\n✅ Scores added to trace: {latest_trace.id}")
    print(f"🔗 View in Langfuse: {LANGFUSE_HOST}/trace/{latest_trace.id}")
else:
    print("\n⚠️  No traces found yet. They may still be processing.")

print("\n🎉 Demo complete!")
```

## Project References and Resources

### Documentation (docs/)

1. **Observability Guide**: 
   - Location: `docs/docs/user-guide/observability.md`
   - Content: Core concepts and setup instructions for OpenTelemetry integration
   - Key Topics: OTEL configuration, trace attributes, telemetry setup

2. **API Reference - Telemetry**:
   - Location: `docs/docs/api-reference/telemetry.md`
   - Content: StrandsTelemetry class documentation
   - Key Classes: StrandsTelemetry, setup_otlp_exporter()

3. **Deployment Examples**:
   - Location: `docs/docs/examples/` (CDK examples)
   - Content: Production deployment patterns with observability

### Sample Code (samples/)

1. **Observability and Evaluation Tutorial**: 
   - Location: `samples/01-tutorials/01-fundamentals/08-observability-and-evaluation/`
   - Files:
     - `01-observability.py`: Basic Langfuse setup and OTEL configuration
     - `02-evaluation.py`: Complete evaluation pipeline with RAGAS
     - `03-evaluation-langfuse.py`: Langfuse SDK integration for scoring
   - Features: Step-by-step Langfuse integration, RAGAS evaluation, custom scoring

2. **HVAC Analytics Agent (Production Example)**:
   - Location: `samples/04-UX-demos/03-hvac-data-analytics-agent/`
   - Files:
     - `lambda_function.py`: AWS Lambda handler with Langfuse configuration
     - `environment.json`: Environment variable template
   - Features: Production Lambda deployment, environment-based configuration, real-world use case

3. **Restaurant Assistant**:
   - Location: `samples/02-samples/02-restaurant-agent-with-memory/`
   - Features: Conversation tracking, session management, tool usage monitoring

4. **Personal Assistant Multi-Agent**:
   - Location: `samples/02-samples/05-personal-assistant/`
   - Features: Multi-agent coordination with observability, session tracking

### SDK Code (sdk-python/)

1. **Telemetry Module**:
   - Location: `sdk-python/src/strands/telemetry/`
   - Key Files:
     - `telemetry.py`: StrandsTelemetry class implementation
     - `span_builder.py`: Span creation and attribute management
     - `semconv.py`: Semantic conventions for GenAI traces
   - Features: OTEL setup, span creation, attribute handling

2. **Agent Module**:
   - Location: `sdk-python/src/strands/agent/`
   - Key Files:
     - `agent.py`: Agent class with trace_attributes support
     - `event_loop.py`: Event loop with automatic span creation
   - Features: Automatic instrumentation, cycle tracking, tool execution tracing

3. **Tool System**:
   - Location: `sdk-python/src/strands/tools/`
   - Features: Automatic tool execution tracing, parameter capture

### Key Integration Points in the SDK

1. **Trace Attributes** (sdk-python/src/strands/agent/agent.py:L58-L65):
   ```python
   trace_attributes: Optional[dict[str, Any]] = None
   ```
   Pass custom attributes that will be added to all spans

2. **Telemetry Setup** (sdk-python/src/strands/telemetry/telemetry.py:L45-L70):
   ```python
   def setup_otlp_exporter(self) -> None:
       """Setup OTLP exporter for sending traces to Langfuse"""
   ```

3. **Span Creation** (sdk-python/src/strands/agent/event_loop.py:L120-L150):
   - Automatic span creation for agent execution
   - Cycle tracking with detailed attributes
   - Tool execution instrumentation

### Environment Variables for Langfuse

As documented in the SDK and samples:

```bash
# Required for Langfuse
OTEL_EXPORTER_OTLP_ENDPOINT="https://cloud.langfuse.com/api/public/otel/v1/traces"
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64_encoded_keys>"

# Optional but recommended
OTEL_SERVICE_NAME="your-service-name"
OTEL_RESOURCE_ATTRIBUTES="service.version=1.0.0,deployment.environment=production"

# Alternative: Direct Langfuse SDK configuration
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com"  # or https://us.cloud.langfuse.com

## Testing Your Integration

### Quick Test Script

Create a test script to verify your Langfuse integration:

```python
#!/usr/bin/env python3
"""Test Langfuse integration with Strands Agents"""

import os
import base64
import time
from strands import Agent
from strands.models.bedrock import BedrockModel

# 1. Set your Langfuse credentials
LANGFUSE_PUBLIC_KEY = input("Enter Langfuse Public Key: ")
LANGFUSE_SECRET_KEY = input("Enter Langfuse Secret Key: ")

# 2. Configure OTEL
auth_token = base64.b64encode(f"{LANGFUSE_PUBLIC_KEY}:{LANGFUSE_SECRET_KEY}".encode()).decode()
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://cloud.langfuse.com/api/public/otel/v1/traces"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth_token}"

# 3. Create and test agent
agent = Agent(
    model=BedrockModel(model_id="us.amazon.nova-premier-v1:0"),
    trace_attributes={
        "test": True,
        "user.id": "test-user",
        "langfuse.tags": ["integration-test"]
    }
)

print("Sending test request...")
result = agent("What is 2+2?")
print(f"Response: {result}")
print(f"Tokens used: {result.metrics.accumulated_usage['totalTokens']}")

print("\nCheck your Langfuse dashboard for the trace!")
print("https://cloud.langfuse.com")
```

## Critical Lessons Learned (January 2025)

Based on extensive real-world implementation experience, here are the key lessons that differ from standard documentation:

### 1. **Order of Operations is CRITICAL**
```
1. Load environment variables (.env)
2. Configure OTEL environment variables
3. Import Strands modules
4. Initialize StrandsTelemetry explicitly
5. Create agents
6. Execute queries
7. Force flush telemetry
```

Any deviation from this order will likely result in no traces being sent.

### 2. **Signal-Specific Endpoints are REQUIRED**
- ❌ `/api/public/otel` - Returns 404
- ✅ `/api/public/otel/v1/traces` - Works correctly

The generic endpoint suggested in some documentation does NOT work with Langfuse.

### 3. **Explicit Initialization is REQUIRED**
Despite documentation suggesting automatic initialization:
```python
# This is REQUIRED, not optional
telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()
```

### 4. **Force Flush is CRITICAL for Scripts**
Without force flush, traces may never be sent:
```python
telemetry.tracer_provider.force_flush()
```

### 5. **TracerProvider Warnings are Expected**
The warning "Overriding of current TracerProvider is not allowed" is common and can be mitigated by:
- Initializing telemetry once per application
- Using singleton patterns in production
- Accepting the warning in development/testing

### 6. **Environment Variables Must Use TRACES Prefix**
- ❌ `OTEL_EXPORTER_OTLP_ENDPOINT`
- ❌ `OTEL_EXPORTER_OTLP_HEADERS`
- ✅ `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`
- ✅ `OTEL_EXPORTER_OTLP_TRACES_HEADERS`

### 7. **Local Development Best Practice**
Always use `.env` files with python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv(override=True)  # Override system env vars
```

## Recommendations for Future Implementations

### For Development Teams
1. **Create a standard initialization module** that handles the correct order
2. **Use debug scripts** to verify configuration before deploying
3. **Test with local Langfuse** (localhost:3000) before cloud deployment
4. **Monitor for 404 errors** in logs - indicates endpoint issues

### For Production Deployments
1. **Initialize telemetry at application startup**, not per-request
2. **Use environment-specific configurations** via AWS Secrets Manager
3. **Implement health checks** that verify Langfuse connectivity
4. **Set up alerts** for failed trace exports

### Debug Script Template
Save this as `test_langfuse.py` in your projects:

```python
#!/usr/bin/env python3
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"✅ Loaded {env_path}")

# Configure OTEL
pk = os.getenv("LANGFUSE_PUBLIC_KEY")
sk = os.getenv("LANGFUSE_SECRET_KEY")
host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

if not pk or not sk:
    print("❌ Missing Langfuse credentials in .env")
    exit(1)

auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()

os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{host}/api/public/otel/v1/traces"
os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"
os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"

print(f"✅ Configured for {host}")

# Now import and test
from strands import Agent
from strands.models.bedrock import BedrockModel
from strands.telemetry import StrandsTelemetry

telemetry = StrandsTelemetry()
telemetry.setup_otlp_exporter()
print("✅ Telemetry initialized")

agent = Agent(
    model=BedrockModel(model_id=os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-premier-v1:0")),
    trace_attributes={
        "session.id": "test-session",
        "user.id": "test-user",
        "langfuse.tags": ["test"]
    }
)

result = agent("What is 2+2?")
print(f"✅ Agent responded: {result}")

telemetry.tracer_provider.force_flush()
print(f"✅ Check traces at: {host}")
```

## Conclusion

Langfuse provides powerful observability capabilities for AWS Strands Agents applications. By following this UPDATED guide that incorporates real-world lessons learned, you can avoid common pitfalls and successfully implement comprehensive tracing.

The native OpenTelemetry support in Strands is powerful but requires careful attention to:
- Configuration order
- Endpoint specificity
- Explicit initialization
- Proper flushing

With these corrections, you'll achieve full visibility into your AI applications with minimal friction.

## Additional Resources

### Strands Agents Resources
- **Documentation**: https://strandsagents.com
- **Observability Guide**: `docs/docs/user-guide/observability.md`
- **Tutorial Code**: `samples/01-tutorials/01-fundamentals/08-observability-and-evaluation/`
- **Production Examples**: `samples/04-UX-demos/03-hvac-data-analytics-agent/`

### External Resources
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse OpenTelemetry Guide](https://langfuse.com/docs/integrations/opentelemetry)
- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)
- [AWS Bedrock Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html)

### Reference Implementation
For a complete working example with MCP servers, see:
- Repository: `aws-ai-ecs/strands-weather-agent`
- Key Files:
  - `weather_agent/langfuse_telemetry.py`
  - `run_and_validate_metrics.py`
  - `debug_telemetry.py`