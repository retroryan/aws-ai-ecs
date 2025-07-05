# Langfuse Integration Guide for AWS Strands Weather Agent

**⚠️ CRITICAL UPDATES (January 2025)**: This guide has been updated based on extensive real-world implementation experience. Key differences from previous documentation:
- **Signal-specific endpoint** is REQUIRED (not `/api/public/otel`, use `/api/public/otel/v1/traces`)
- **Explicit telemetry initialization** is REQUIRED (not automatic)
- **Environment variables MUST be set BEFORE imports** (critical for OTEL to work)
- **TracerProvider override warnings** are expected and can be mitigated
- **Force flush** is critical for short-lived scripts

This comprehensive guide provides step-by-step instructions for integrating Langfuse observability into the AWS Strands Weather Agent, including both local and Docker deployments. Langfuse is an open-source LLM engineering platform that provides advanced tracing, monitoring, and evaluation capabilities for AI applications.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Critical Implementation Details](#critical-implementation-details)
- [Local Development Setup](#local-development-setup)
- [Docker Deployment Setup](#docker-deployment-setup)
- [Docker Network Configuration](#docker-network-configuration)
- [Validation and Testing](#validation-and-testing)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Additional Resources](#additional-resources)

## Overview

Langfuse provides observability for LLM applications through OpenTelemetry (OTEL) integration. The AWS Strands Weather Agent uses Langfuse to track:
- Agent invocations and tool calls
- Token usage and costs
- Response latencies
- Session and user tracking
- Custom metadata and tags
- Distributed tracing for complex multi-step workflows
- Performance analytics and error rates
- Evaluation integration for quality metrics

### Why Langfuse for Strands Agents?

AWS Strands Agents natively supports OpenTelemetry (OTEL), making Langfuse integration seamless:

1. **Native OTEL Support**: Strands automatically exports traces in OTEL format
2. **Rich Semantic Conventions**: GenAI-specific attributes are captured automatically
3. **Tool Tracking**: Every tool execution is traced with inputs/outputs
4. **Multi-Turn Support**: Sessions and conversations are tracked coherently
5. **Cost Visibility**: Token usage and API costs are tracked per operation

## Prerequisites

1. **Langfuse Instance**: Either cloud-hosted or self-hosted
2. **Langfuse API Credentials**: Public and secret keys
3. **Docker and Docker Compose** (for containerized deployments)
4. **AWS Credentials** configured for Bedrock access
5. **Python 3.11+** with required packages:
   ```bash
   pip install strands-agents>=0.2.0
   pip install python-dotenv
   pip install langfuse  # Optional, for evaluation
   ```

## Quick Start

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

## Critical Implementation Details

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

## Local Development Setup

### 1. Environment Variables

Add the following to your `.env` file:

```bash
# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=http://localhost:3000  # For local Langfuse
# LANGFUSE_HOST=https://us.cloud.langfuse.com  # For cloud Langfuse

# Optional Telemetry Configuration
ENABLE_TELEMETRY=true
TELEMETRY_USER_ID=local-dev-user
TELEMETRY_SESSION_ID=  # Leave empty for auto-generated
TELEMETRY_TAGS=weather-agent,development
ENVIRONMENT=development
```

### 2. Running Locally

```bash
# Start MCP servers
./scripts/start_servers.sh

# Run with telemetry enabled
ENABLE_TELEMETRY=true python main.py

# Or use the environment variable from .env
python main.py
```

### 3. Local Testing Script

Create a test script to verify your Langfuse integration:

```python
#!/usr/bin/env python3
"""test_langfuse.py - Test Langfuse integration"""

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

## Docker Deployment Setup

Docker deployments require additional configuration to handle networking between containers.

### 1. Environment Variables for Docker

Add Docker-specific configuration to your `.env` file:

```bash
# Standard Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=http://localhost:3000  # For local access

# Docker-specific Langfuse Host
# This uses the Docker service name instead of localhost
LANGFUSE_HOST_DOCKER=http://langfuse-web:3000
```

### 2. Docker Compose Configuration

Update your `docker-compose.yml` to include Langfuse environment variables:

```yaml
services:
  weather-agent:
    # ... other configuration ...
    environment:
      # Langfuse Telemetry Configuration
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}
      - LANGFUSE_HOST=${LANGFUSE_HOST_DOCKER:-http://langfuse-web:3000}
      - ENABLE_TELEMETRY=${ENABLE_TELEMETRY:-false}
      - TELEMETRY_USER_ID=${TELEMETRY_USER_ID:-docker-user}
      - TELEMETRY_SESSION_ID=${TELEMETRY_SESSION_ID}
      - TELEMETRY_TAGS=${TELEMETRY_TAGS:-weather-agent,docker}
      - ENVIRONMENT=${ENVIRONMENT:-production}
    networks:
      - weather-network
      - langfuse_default  # Connect to Langfuse network
```

### 3. Application Code Updates

Ensure your application initialization includes telemetry parameters:

```python
# In main.py or your app initialization
enable_telemetry = os.getenv("ENABLE_TELEMETRY", "false").lower() == "true"
telemetry_user_id = os.getenv("TELEMETRY_USER_ID", "api-user")
telemetry_tags = os.getenv("TELEMETRY_TAGS", "weather-agent,api").split(",")

agent = await create_weather_agent(
    debug_logging=debug_mode,
    enable_telemetry=enable_telemetry,
    telemetry_user_id=telemetry_user_id,
    telemetry_tags=telemetry_tags
)
```

### 4. Dockerfile Best Practices

```dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app
WORKDIR /app

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Set entrypoint
CMD ["python", "main.py"]
```

## Docker Network Configuration

### Understanding Docker Networks

When running Langfuse and your application in separate Docker Compose projects, they need to share a network for communication.

### 1. Finding the Langfuse Network

If you don't know the Langfuse network name:

```bash
# List all Docker networks
docker network ls

# Find networks containing "langfuse"
docker network ls | grep langfuse

# Example output:
# d54c9f1147b6   langfuse_default   bridge    local
```

Common Langfuse network names:
- `langfuse_default` (if project name is "langfuse")
- `{project_name}_default` (where project_name is the directory name)

### 2. Inspecting Network Details

To get more information about a network:

```bash
# Inspect the network
docker network inspect langfuse_default

# Find which containers are connected
docker network inspect langfuse_default | grep -A 5 "Containers"
```

### 3. Configuring Shared Networks

Add the external network to your `docker-compose.yml`:

```yaml
networks:
  weather-network:
    driver: bridge
  langfuse_default:
    external: true  # Reference to existing Langfuse network
```

### 4. Alternative: Create a Dedicated Network

If you prefer explicit network management:

```bash
# Create a shared network
docker network create shared-telemetry-network

# Update both docker-compose files to use it
```

In Langfuse's `docker-compose.yml`:
```yaml
networks:
  default:
  shared-telemetry-network:
    external: true

services:
  langfuse-web:
    networks:
      - default
      - shared-telemetry-network
```

In Weather Agent's `docker-compose.yml`:
```yaml
networks:
  weather-network:
    driver: bridge
  shared-telemetry-network:
    external: true

services:
  weather-agent:
    networks:
      - weather-network
      - shared-telemetry-network
```

## Starting Services with Telemetry

### Using the Enhanced start_docker.sh Script

The script now supports a `--telemetry` flag:

```bash
# Start with telemetry enabled
./scripts/start_docker.sh --telemetry

# Start with both debug and telemetry
./scripts/start_docker.sh --debug --telemetry

# The script will:
# 1. Load .env variables
# 2. Export AWS credentials
# 3. Set ENABLE_TELEMETRY=true
# 4. Build and start services
```

### Manual Docker Commands

```bash
# Set telemetry environment variable
export ENABLE_TELEMETRY=true

# Start services
docker compose up -d

# Or in one command
ENABLE_TELEMETRY=true docker compose up -d
```

## Validation and Testing

### 1. Test Connectivity

From within the weather-agent container:

```bash
# Test Langfuse connectivity
docker compose exec weather-agent curl -s http://langfuse-web:3000/api/public/health

# Expected output:
# {"status":"OK","version":"3.78.1"}
```

### 2. Check Environment Variables

```bash
# Verify environment variables are set
docker compose exec weather-agent env | grep -E "LANGFUSE|TELEMETRY|ENABLE"
```

### 3. Run Validation Script

```bash
# From strands-metrics-guide directory
python run_and_validate_metrics.py

# This will:
# - Test Langfuse connectivity
# - Run sample queries
# - Validate traces are created
# - Check all attributes are working
```

### 4. Monitor Logs

```bash
# Check for Langfuse initialization
docker compose logs weather-agent | grep -i langfuse

# Watch logs in real-time
docker compose logs -f weather-agent
```

### 5. Debug Telemetry Configuration

```bash
# Run debug script
python strands-metrics-guide/debug_telemetry.py

# This will check:
# - Environment variable configuration
# - Endpoint connectivity
# - Telemetry initialization
# - Common configuration errors
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "Langfuse credentials not configured"
- **Cause**: Environment variables not passed to container
- **Solution**: 
  - Verify variables in `.env` file
  - Check docker-compose.yml includes the variables
  - Rebuild container: `docker compose build weather-agent`

#### 2. "Failed to connect to Langfuse"
- **Cause**: Network connectivity issues
- **Solution**:
  - Verify Langfuse is running: `docker ps | grep langfuse`
  - Check network configuration
  - Test connectivity from container (see above)

#### 3. "No traces appearing in Langfuse"
- **Cause**: Telemetry not enabled or misconfigured
- **Solution**:
  - Verify `ENABLE_TELEMETRY=true`
  - Check agent initialization includes telemetry parameters
  - Ensure `LANGFUSE_HOST` uses correct Docker service name
  - Run debug script to diagnose

#### 4. Container can't resolve "langfuse-web"
- **Cause**: Networks not properly connected
- **Solution**:
  - Verify both containers are on same network
  - Check service names match exactly
  - Restart services after network changes

#### 5. "Failed to export batch code: 404"
- **Cause**: Using wrong endpoint
- **Solution**:
  - Use `/api/public/otel/v1/traces` NOT `/api/public/otel`
  - Check OTEL_EXPORTER_OTLP_TRACES_ENDPOINT is set correctly

#### 6. "Overriding of current TracerProvider is not allowed"
- **Cause**: Multiple telemetry initializations
- **Solution**:
  - Initialize telemetry once at application startup
  - Use singleton pattern for production

### Debug Commands

```bash
# Check container networks
docker inspect weather-agent-app | grep -A 10 "Networks"

# Test DNS resolution
docker compose exec weather-agent nslookup langfuse-web

# Check exposed ports
docker compose port langfuse-web 3000

# View container logs
docker compose logs --tail=50 weather-agent

# Debug environment variables
docker compose exec weather-agent python -c "
import os
print('OTEL Endpoint:', os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT'))
print('OTEL Headers:', 'SET' if os.getenv('OTEL_EXPORTER_OTLP_TRACES_HEADERS') else 'NOT SET')
print('Langfuse Host:', os.getenv('LANGFUSE_HOST'))
"
```

### Debug Script for Common Issues

```python
def debug_langfuse_connection():
    """Debug Langfuse connectivity issues"""
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

## Best Practices

### 1. Security
- Never commit credentials to version control
- Use AWS Secrets Manager or Parameter Store for production
- Rotate API keys regularly
- Use least-privilege IAM roles

### 2. Environment Separation
- Use different Langfuse projects for dev/staging/prod
- Tag traces with environment metadata
- Separate API keys per environment
- Monitor costs per environment

### 3. Resource Management
- Monitor token usage to control costs
- Set up alerts for high token consumption
- Use batch processing for better performance
- Implement retry logic with exponential backoff

### 4. Tagging Strategy
- Use meaningful tags for filtering traces
- Include version numbers in tags
- Tag by feature or workflow type
- Add customer/tenant tags for multi-tenant apps

### 5. Session Management
- Group related queries with session IDs
- Track user journeys across sessions
- Implement session timeout logic
- Clean up old session data

### 6. Error Handling
- Gracefully handle telemetry failures
- Don't let tracing errors affect application
- Log telemetry errors separately
- Implement circuit breaker pattern

### 7. Performance Optimization

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

### 8. Privacy and Security

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

## Complete Working Example

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

## Additional Resources

### Langfuse Documentation
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse OpenTelemetry Guide](https://langfuse.com/docs/integrations/opentelemetry)
- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)

### AWS Strands Documentation
- [AWS Strands Documentation](https://github.com/awslabs/strands-agents)
- [AWS Bedrock Models](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html)
- [Docker Networking Guide](https://docs.docker.com/network/)

### Reference Implementation
For a complete working example with MCP servers, see:
- Repository: `aws-ai-ecs/strands-weather-agent`
- Key Files:
  - `weather_agent/langfuse_telemetry.py`
  - `strands-metrics-guide/run_and_validate_metrics.py`
  - `strands-metrics-guide/debug_telemetry.py`
  - `strands-metrics-guide/inspect_traces.py`
  - `strands-metrics-guide/monitor_performance.py`

## Conclusion

Langfuse provides powerful observability capabilities for AWS Strands Agents applications. By following this UPDATED guide that incorporates real-world lessons learned, you can avoid common pitfalls and successfully implement comprehensive tracing.

The native OpenTelemetry support in Strands is powerful but requires careful attention to:
- Configuration order
- Endpoint specificity
- Explicit initialization
- Proper flushing

With these corrections, you'll achieve full visibility into your AI applications with minimal friction.