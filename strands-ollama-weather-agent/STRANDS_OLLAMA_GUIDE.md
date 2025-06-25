# AWS Strands + Ollama Integration Guide

This guide documents how to integrate Ollama (local LLM inference) with AWS Strands agents, enabling model-agnostic AI applications that can run either with cloud-based models (AWS Bedrock) or completely offline with local models.

## Quick Troubleshooting Checklist

Before diving into the full guide, here's a quick checklist for common issues:

- [ ] **MCP Servers Running?** Check with `lsof -ti:8081,8082,8083`
- [ ] **Ollama Model Pulled?** Verify with `ollama list`
- [ ] **Using Right Model Size?** Use 7B+ for tool calling
- [ ] **Environment Variable Set?** Check `MODEL_PROVIDER=ollama` in `.env`
- [ ] **Ports Clear?** Kill stale processes: `./scripts/stop_servers.sh`
- [ ] **Ollama Running?** Start with `ollama serve`

## Table of Contents
- [Overview](#overview)
- [Architecture Pattern](#architecture-pattern)
- [Implementation Steps](#implementation-steps)
- [Testing Strategy](#testing-strategy)
- [Docker Integration](#docker-integration)
- [Mock Mode](#mock-mode)
- [Lessons Learned](#lessons-learned)
- [Remaining Challenges](#remaining-challenges)
- [Production Recommendations](#production-recommendations)

## Overview

### What We Built
A weather agent system that seamlessly switches between:
- **AWS Bedrock**: Cloud-based models (Claude, Llama, Nova)
- **Ollama**: Local models (Llama, Mistral, Gemma, etc.)

### Key Benefits
- **True Model Agnosticism**: Switch providers via environment variable
- **Privacy & Cost**: Run completely offline with no API costs
- **Development Flexibility**: Test locally without cloud dependencies
- **Same Codebase**: Zero code changes required when switching providers

## Architecture Pattern

### Model Provider Abstraction

```python
# Abstract base class
class ModelProvider(ABC):
    @abstractmethod
    def create_model(self) -> Any:
        """Create and return the model instance."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get provider information."""
        pass

# Concrete implementations
class BedrockProvider(ModelProvider):
    # AWS Bedrock implementation
    
class OllamaProvider(ModelProvider):
    # Ollama implementation
```

### Provider Selection
```python
# Environment-based selection
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "bedrock")

def create_model_provider() -> ModelProvider:
    if MODEL_PROVIDER == "ollama":
        return OllamaProvider()
    else:
        return BedrockProvider()
```

## Implementation Steps

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve

# Pull a model
ollama pull llama3.2
```

### 2. Install Dependencies

```bash
# Install AWS Strands with Ollama support
pip install strands-agents[ollama]
```

### 3. Create Model Providers

**weather_agent/model_providers.py:**
```python
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ModelProvider(ABC):
    """Abstract base class for model providers."""
    
    @abstractmethod
    def create_model(self) -> Any:
        """Create and return the model instance."""
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get provider information."""
        pass
    
    @abstractmethod
    def get_model_id(self) -> str:
        """Get the model ID string."""
        pass

class OllamaProvider(ModelProvider):
    """Ollama model provider for local inference."""
    
    def __init__(self):
        self.model_id = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        self.max_tokens = int(os.getenv("OLLAMA_MAX_TOKENS", "4096"))
        logger.info(f"Initialized OllamaProvider with model: {self.model_id}")
        logger.info(f"Ollama host: {self.host}")
    
    def create_model(self) -> Any:
        from strands.models.ollama import OllamaModel
        
        return OllamaModel(
            model_id=self.model_id,
            api_base=self.host,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "ollama",
            "model_id": self.model_id,
            "host": self.host,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "local": True
        }
    
    def get_model_id(self) -> str:
        return self.model_id

class BedrockProvider(ModelProvider):
    """AWS Bedrock model provider."""
    
    def __init__(self):
        self.model_id = os.getenv(
            "BEDROCK_MODEL_ID",
            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
        )
        self.region = os.getenv("BEDROCK_REGION", "us-west-2")
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        logger.info(f"Initialized BedrockProvider with model: {self.model_id}")
    
    def create_model(self) -> Any:
        from strands.models.bedrock import BedrockModel
        
        return BedrockModel(
            model_id=self.model_id,
            region=self.region,
            temperature=self.temperature
        )
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "bedrock",
            "model_id": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "local": False
        }
    
    def get_model_id(self) -> str:
        return self.model_id

def create_model_provider() -> ModelProvider:
    """Factory function to create the appropriate model provider."""
    provider_type = os.getenv("MODEL_PROVIDER", "bedrock").lower()
    
    logger.info(f"Creating {provider_type} model provider")
    
    if provider_type == "ollama":
        return OllamaProvider()
    else:
        return BedrockProvider()

def test_provider_connectivity(provider: ModelProvider) -> bool:
    """Test if the provider is accessible."""
    try:
        if isinstance(provider, OllamaProvider):
            import httpx
            response = httpx.get(f"{provider.host}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                if provider.model_id in model_names:
                    logger.info(f"✅ Ollama model {provider.model_id} is available")
                    return True
                else:
                    logger.warning(f"❌ Ollama model {provider.model_id} not found. Available: {model_names}")
                    return False
        return True  # Assume Bedrock is available
    except Exception as e:
        logger.error(f"Provider connectivity test failed: {e}")
        return False
```

### 4. Update Agent to Use Providers

```python
class MCPWeatherAgent:
    def __init__(self, ...):
        # Create model provider
        self.model_provider = create_model_provider()
        self.model = self.model_provider.create_model()
        self.model_id = self.model_provider.get_model_id()
        
        # Test connectivity
        if not test_provider_connectivity(self.model_provider):
            logger.warning(f"Model provider connectivity test failed")
```

## Testing Strategy

### 1. Basic Ollama Testing

**test_ollama/test_ollama_simple.py:**
```python
"""
Basic test to verify Ollama connectivity and agent functionality.
This is the simplest way to test if Ollama is working correctly.
"""

import asyncio
import os

# Set Ollama as the provider
os.environ['MODEL_PROVIDER'] = 'ollama'
os.environ['OLLAMA_MODEL'] = 'llama3.2:1b'  # Small, fast model for testing

from strands import Agent
from strands.models.ollama import OllamaModel

async def test_basic_ollama():
    """Test basic Ollama functionality."""
    print("🧪 Testing Ollama connectivity...")
    
    # Create Ollama model
    model = OllamaModel(
        model_id="llama3.2:1b",
        api_base="http://localhost:11434"
    )
    
    # Create simple agent
    agent = Agent(
        model=model,
        system_prompt="You are a helpful weather assistant."
    )
    
    # Test query
    response = agent("What's the weather typically like in summer?")
    print(f"✅ Response: {response}")

if __name__ == "__main__":
    asyncio.run(test_basic_ollama())
```

This basic test is useful for:
- Verifying Ollama is installed and running
- Testing model connectivity
- Quick sanity checks during development
- Debugging model-specific issues

### 2. Mock Mode Testing

Mock mode allows testing the full agent without MCP servers:

**weather_agent/mock_tools.py:**
```python
"""Mock tools for testing without MCP servers."""

class MockTool:
    """Base class for mock tools."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.input_schema = {"type": "object", "properties": {}}
    
    def __call__(self, **kwargs):
        raise NotImplementedError

class MockCurrentWeatherTool(MockTool):
    """Mock current weather tool."""
    def __init__(self):
        super().__init__(
            name="get_current_weather",
            description="Get current weather for a location"
        )
    
    def __call__(self, latitude: float, longitude: float):
        # Return mock weather data
        return {
            "temperature": 22.5,
            "conditions": "Partly cloudy",
            "humidity": 65
        }
```

**Using Mock Mode:**
```python
# Create agent with mock mode
agent = MCPWeatherAgent(mock_mode=True)

# Test without MCP servers
response = await agent.query("What's the weather in Seattle?")
```

### 3. Full Integration Testing

**test_ollama_mock.py:**
```python
async def test_full_agent():
    """Test the complete agent with mock tools."""
    # Create agent with mock mode
    agent = MCPWeatherAgent(debug_logging=True, mock_mode=True)
    
    # Test various queries
    queries = [
        "What's the weather in Chicago?",
        "Give me a 3-day forecast for Seattle",
        "Are conditions good for planting corn?"
    ]
    
    for query in queries:
        response = await agent.query(query)
        print(f"Query: {query}")
        print(f"Response: {response}\n")
```

## Docker Integration

### 1. Docker Compose with Ollama Profile

**docker-compose.yml:**
```yaml
services:
  # Ollama Service (optional - use with --profile ollama)
  ollama:
    image: ollama/ollama
    container_name: ollama
    profiles:
      - ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama:/root/.ollama
    networks:
      - weather-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/"]
      interval: 30s
      timeout: 3s
      retries: 3

  weather-agent:
    build:
      context: .
      dockerfile: docker/Dockerfile.main
    environment:
      # Model Provider Configuration
      - MODEL_PROVIDER=${MODEL_PROVIDER:-bedrock}
      # Ollama Configuration (when using Ollama profile)
      - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2}
      - OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}
    depends_on:
      - forecast-server
      - historical-server
      - agricultural-server
    networks:
      - weather-network

volumes:
  ollama:
    driver: local

networks:
  weather-network:
    driver: bridge
```

### 2. Start Script with Ollama

**scripts/start_docker_ollama.sh:**
```bash
#!/bin/bash
set -e

echo "🚀 Starting Weather Agent with Ollama..."

# Set environment variables for Ollama
export MODEL_PROVIDER=ollama
export OLLAMA_HOST=http://ollama:11434

# Build images
docker-compose build

# Start services with ollama profile
docker-compose --profile ollama up -d

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
sleep 10

# Pull model if needed
MODEL=${OLLAMA_MODEL:-llama3.2}
if ! docker exec ollama ollama list | grep -q "$MODEL"; then
    echo "📥 Pulling model '$MODEL'..."
    docker exec ollama ollama pull "$MODEL"
fi

echo "✅ Services started successfully!"
```

### 3. Container Networking

Key points for Docker networking:
- Ollama runs as a separate container
- Services communicate via Docker network
- Use service name `ollama` as hostname
- URL becomes `http://ollama:11434` inside containers

## Mock Mode

### Purpose
Mock mode enables testing without MCP server dependencies:
- Faster development cycles
- CI/CD pipeline testing
- Ollama integration testing
- Debugging agent logic

### Implementation
```python
class MCPWeatherAgent:
    def __init__(self, ..., mock_mode: bool = False):
        self.mock_mode = mock_mode
        
    def _process_with_clients_sync(self, ...):
        if self.mock_mode:
            # Use mock tools
            all_tools = create_mock_tools()
        else:
            # Use real MCP clients
            # ... existing code ...
```

### Benefits
1. **Isolation**: Test Ollama without MCP complexity
2. **Speed**: No network calls to MCP servers
3. **Reliability**: Consistent test results
4. **Simplicity**: Easy to set up and use

## Lessons Learned

### 1. Model Size Matters
- Small models (3B parameters) struggle with tool calling
- Recommend 7B+ parameters for reliable tool usage
- Larger models provide better structured output
- **Finding**: llama3.2 (3B) returns Python code instead of calling tools

### 2. Tool Calling Differences
- Ollama models may need different prompting strategies
- Some models interpret tool calling as code generation
- Mock mode helps identify model-specific issues
- **Critical**: Smaller models often fail to follow the tool calling format

### 3. Docker Networking
- Use Docker Compose profiles for optional services
- Service names as hostnames simplify configuration
- Health checks ensure proper startup order
- Host networking varies by platform (host.docker.internal vs 172.17.0.1)

### 4. Testing Strategy
- Start with basic connectivity tests
- Use mock mode for complex integration testing
- Test with multiple model sizes
- Always verify tool calling capability before production use

### 5. Common Pitfalls and Solutions
- **MCP Connection Errors**: Often caused by stale processes on ports
  - Solution: Kill processes with `lsof -ti:8081,8082,8083 | xargs kill -9`
- **Model Not Found**: Ollama models must be pulled before use
  - Solution: `ollama pull <model-name>`
- **Poor Tool Performance**: Model size directly impacts tool calling ability
  - Solution: Use 7B+ parameter models for production

### 6. Latest Testing Results (December 2024)
During our latest testing session, we encountered and resolved several issues:

**Issues Encountered**:
1. **MCP Server Stale Processes**: Previous server instances were blocking ports
   - Fixed by killing processes and restarting servers
2. **Missing Ollama Model**: llama3.2 wasn't pulled on the system
   - Fixed by running `ollama pull llama3.2`
3. **Tool Calling Failures**: llama3.2 returned Python code instead of tool calls
   - This confirms the model size limitation for tool calling

**Test Output Analysis**:
- llama3.2 interpreted tool calling as a code generation task
- Instead of calling `get_weather_forecast` tool, it generated Python parsing code
- This behavior was consistent across all three demo queries

**Recommendations Based on Testing**:
1. Always verify MCP servers are cleanly started
2. Pre-pull all required Ollama models before testing
3. Use 7B+ models for any production tool-calling scenarios
4. Consider implementing a model capability detection system

## Production Recommendations

### 1. Model Selection
```bash
# Development/Testing Only
OLLAMA_MODEL=llama3.2      # 3B - Fast but poor tool calling

# Production Recommended
OLLAMA_MODEL=llama3.1:8b   # Good tool calling support
OLLAMA_MODEL=mistral:7b    # Excellent performance
OLLAMA_MODEL=gemma2:9b     # Strong reasoning
OLLAMA_MODEL=qwen2.5:7b    # Reliable tool usage
```

### 2. Environment Configuration
```env
# .env file
MODEL_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434
OLLAMA_TEMPERATURE=0.7
OLLAMA_TIMEOUT=60
```

### 3. Error Handling
```python
# Add retry logic for model calls
# Implement fallback to Bedrock if Ollama fails
# Log model performance metrics
```

### 4. Deployment Options

**Local Development:**
```bash
# Use mock mode for rapid iteration
python test_ollama_mock.py
```

**Staging:**
```bash
# Real MCP servers + Ollama
./scripts/start_servers.sh
MODEL_PROVIDER=ollama python main.py
```

**Production:**
```bash
# Docker with Ollama profile
./scripts/start_docker_ollama.sh
```

## Quick Reference

### Switch to Ollama
```bash
export MODEL_PROVIDER=ollama
export OLLAMA_MODEL=llama3.2
```

### Test Connectivity
```bash
curl http://localhost:11434/api/tags
```

### Run with Mock Mode
```python
agent = MCPWeatherAgent(mock_mode=True)
```

### Docker with Ollama
```bash
docker-compose --profile ollama up -d
```

## Remaining Challenges

### 1. Tool Calling Format Issues
**Challenge**: Smaller Ollama models (≤3B) struggle with AWS Strands' tool calling format
- Models return Python code or unstructured text instead of tool calls
- Tool parameters are often malformed or missing
- JSON formatting is inconsistent

**Mitigation**: 
- Use 7B+ parameter models for production
- Consider fine-tuning models specifically for tool calling
- Implement response parsing fallbacks

### 2. Performance vs. Capability Trade-off
**Challenge**: Balancing model size, speed, and functionality
- Smaller models (3B) are fast but unreliable for tools
- Larger models (7B+) work well but require more resources
- Memory constraints on edge devices

**Mitigation**:
- Use mock mode for development with small models
- Deploy larger models only for production
- Consider model quantization (e.g., Q4_K_M variants)

### 3. Prompt Engineering Requirements
**Challenge**: Different models require different prompting strategies
- Ollama models may interpret instructions differently than Claude/GPT
- Tool calling instructions need model-specific tuning
- System prompts that work for Bedrock may fail with Ollama

**Future Work**:
- Create model-specific prompt templates
- Build a prompt testing framework
- Document optimal prompts per model

### 4. Observability Gaps
**Challenge**: Limited visibility into Ollama's decision-making
- No token-level debugging like with cloud providers
- Difficult to diagnose why tool calls fail
- Limited metrics on model performance

**Future Work**:
- Implement custom logging for tool call attempts
- Add metrics collection for success rates
- Build debugging tools for prompt analysis

## Conclusion

This integration demonstrates true model agnosticism in AI applications. By abstracting the model provider layer, we can seamlessly switch between cloud-based and local models without changing application code. The mock mode feature further enhances development velocity by removing external dependencies during testing.

Key achievements:
- ✅ Zero code changes when switching providers
- ✅ Full offline capability with Ollama
- ✅ Simplified testing with mock mode
- ✅ Docker integration with profiles
- ✅ Production-ready architecture
- ✅ Comprehensive troubleshooting documentation

Areas for improvement:
- 🔄 Better support for smaller models
- 🔄 Model-specific prompt optimization
- 🔄 Enhanced debugging capabilities
- 🔄 Performance benchmarking tools