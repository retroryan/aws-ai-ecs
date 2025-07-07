# AWS Strands General Best Practices

## Overview

This guide provides a curated summary of best practices for building applications with AWS Strands, synthesized from the official documentation and real-world implementation experience. For detailed examples and complete code, refer to the official Strands samples repository.

## Table of Contents

1. [Agent Lifecycle Management](#agent-lifecycle-management)
2. [Structured Input/Output](#structured-inputoutput)
3. [Tool Development](#tool-development)
4. [MCP Integration](#mcp-integration)
5. [Error Handling](#error-handling)
6. [Performance Optimization](#performance-optimization)
7. [Production Deployment](#production-deployment)

---

## Agent Lifecycle Management

### Key Decision: Create New vs Reuse Agents

The choice depends on your application's statefulness:

#### Pattern 1: Create Once, Reuse (Stateful Apps)
**Use for**: Chat apps, CLI tools, interactive sessions

```python
# Web app example (Streamlit)
if "agent" not in st.session_state:
    st.session_state.agent = Agent(...)  # Create once per session

# CLI example
agent = Agent(...)  # Global instance
while True:
    response = agent(input("> "))
```

#### Pattern 2: Create Per Request (Stateless Apps)
**Use for**: APIs, Lambda functions, microservices

```python
@app.post("/chat")
async def chat(session_id: str, prompt: str):
    # Restore state from external storage
    history = await get_history(session_id)
    
    # Create new agent with state
    agent = Agent(messages=history)
    response = await agent.invoke_async(prompt)
    
    # Save state
    await save_history(session_id, agent.messages)
    return response
```

#### Pattern 3: Agent Pool (High Concurrency)
**Use for**: High-traffic applications

```python
class AgentPool:
    def __init__(self, size=10):
        self.pool = Queue()
        for _ in range(size):
            self.pool.put(Agent(...))
    
    def acquire(self):
        return self.pool.get()
    
    def release(self, agent):
        agent.messages = []  # Reset state
        self.pool.put(agent)
```

### Best Practices
- Agent creation is lightweight (milliseconds)
- No persistent model connections
- Main resource is thread pool for parallel tools
- Use `load_tools_from_directory=False` in production

---

## Structured Input/Output

### Why Use Structured I/O?
- **Type Safety**: Catch errors at development time
- **Validation**: Automatic data validation
- **Documentation**: Self-documenting APIs
- **Consistency**: Standardized formats

### Basic Pattern
```python
from pydantic import BaseModel, Field
from strands import Agent

class PersonInfo(BaseModel):
    """Person information model."""
    name: str = Field(description="Full name")
    age: int = Field(ge=0, le=150, description="Age in years")
    occupation: str = Field(description="Current occupation")

agent = Agent()
result = agent.structured_output(
    PersonInfo, 
    "John Smith is a 30-year-old software engineer"
)

# Async version
result = await agent.structured_output_async(PersonInfo, prompt)
```

### Advanced Patterns
```python
# Nested models with validation
class Address(BaseModel):
    street: str
    city: str
    country: str
    postal_code: Optional[str] = Field(
        default=None, 
        pattern=r'^\d{5}(-\d{4})?$'
    )

class Contact(BaseModel):
    email: EmailStr
    phone: str = Field(pattern=r'^\+?[\d\s-]+$')

class Person(BaseModel):
    name: str
    age: int = Field(ge=18, le=100)
    address: Address
    contacts: List[Contact]
```

### Best Practices
- Use descriptive field names and descriptions
- Add validation constraints
- Handle optional fields with sensible defaults
- Keep models focused and single-purpose
- Use type hints extensively

---

## Tool Development

### Three Approaches to Tools

#### 1. @tool Decorator (Recommended)
```python
from strands import tool

@tool
def weather_forecast(
    city: str, 
    days: int = 3,
    units: Literal["celsius", "fahrenheit"] = "celsius"
) -> Dict[str, Any]:
    """Get weather forecast for a city.
    
    Args:
        city: The name of the city
        days: Number of days to forecast (1-7)
        units: Temperature units
    """
    # Validate inputs
    if not 1 <= days <= 7:
        return {
            "status": "error",
            "content": [{"text": "Days must be between 1 and 7"}]
        }
    
    # Implementation
    result = fetch_weather(city, days, units)
    
    return {
        "status": "success",
        "content": [
            {"text": f"Forecast for {city}:"},
            {"json": result}
        ]
    }
```

#### 2. Module-Based Tools
For complex tools or when you need more control:
```python
TOOL_SPEC = {
    "name": "weather_forecast",
    "description": "Get weather forecast",
    "inputSchema": {...}
}

def weather_forecast(tool: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    tool_use_id = tool["toolUseId"]
    tool_input = tool["input"]
    # Implementation...
```

#### 3. MCP Tools
For external tool servers - see MCP Integration section.

### Tool Response Formats
```python
# Text response
{"status": "success", "content": [{"text": "Result"}]}

# JSON response
{"status": "success", "content": [{"json": {"data": [1, 2, 3]}}]}

# Mixed content
{
    "status": "success",
    "content": [
        {"text": "Analysis:"},
        {"json": {"confidence": 0.95}},
        {"image": {"format": "png", "source": {"bytes": data}}}
    ]
}
```

### Best Practices
- Single responsibility per tool
- Comprehensive docstrings
- Input validation
- Return structured errors, not exceptions
- Make tools idempotent
- Consider timeouts

---

## MCP Integration

### Connection Types

#### Standard I/O (Most Common)
```python
from mcp import stdio_client, StdioServerParameters
from strands.tools.mcp import MCPClient

mcp_client = MCPClient(
    lambda: stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["my-mcp-server@latest"]
        )
    )
)
```

#### HTTP/SSE Connections
```python
# Server-Sent Events
from mcp.client.sse import sse_client
sse_client = MCPClient(
    lambda: sse_client("http://localhost:8000/sse")
)

# Streamable HTTP
from mcp.client.streamable_http import streamablehttp_client
http_client = MCPClient(
    lambda: streamablehttp_client("http://localhost:8000/mcp")
)
```

### Critical: Context Manager Usage
```python
# ✅ CORRECT - Always use context manager
with mcp_client:
    tools = mcp_client.list_tools_sync()
    agent = Agent(tools=tools)
    response = agent("Query")  # Works

# ❌ WRONG - Will fail with MCPClientInitializationError
tools = mcp_client.list_tools_sync()  # Outside context
```

### Best Practices
- Always use context managers
- Handle connection failures gracefully
- Verify tools are available
- Set appropriate timeouts
- Validate MCP server sources

---

## Error Handling

### Comprehensive Error Handling Pattern
```python
from strands.exceptions import (
    ToolExecutionError,
    ModelError,
    ContextLengthExceededError
)

class RobustAgentHandler:
    async def safe_agent_call(self, prompt: str, tools: list = None):
        for attempt in range(self.max_retries):
            try:
                agent = Agent(
                    model=self.primary_model if attempt == 0 else self.fallback_model,
                    tools=tools or []
                )
                return await agent.invoke_async(prompt)
                
            except ContextLengthExceededError:
                # Reduce context window
                agent.conversation_manager.window_size //= 2
                
            except ToolExecutionError as e:
                # Retry without failing tool
                if tools and e.tool_name:
                    tools = [t for t in tools if t.__name__ != e.tool_name]
                    
            except ModelError:
                # Switch to fallback model
                continue
```

### Tool Error Handling
```python
@tool
def safe_database_query(query: str) -> dict:
    """Execute database query with error handling."""
    try:
        # Validate input
        if not query.strip():
            return {"status": "error", "content": [{"text": "Empty query"}]}
        
        # Execute
        result = execute_query(query)
        return {"status": "success", "content": [{"json": result}]}
        
    except DatabaseConnectionError:
        return {"status": "error", "content": [{"text": "Connection failed"}]}
    except Exception as e:
        return {"status": "error", "content": [{"text": str(e)}]}
```

---

## Performance Optimization

### 1. Tool Loading
```python
# Lazy load tools only when needed
class LazyToolLoader:
    def get_tools(self, tool_names: List[str]):
        tools = []
        for name in tool_names:
            if name not in self._tools:
                # Dynamic import
                module = importlib.import_module(f'tools.{name}')
                self._tools[name] = module.tool
            tools.append(self._tools[name])
        return tools
```

### 2. Context Management
```python
# Use sliding window for long conversations
from strands.conversation import SlidingWindowConversationManager

agent = Agent(
    conversation_manager=SlidingWindowConversationManager(
        window_size=10  # Keep last 10 exchanges
    )
)
```

### 3. Response Caching
```python
import hashlib
from functools import lru_cache

class CachedAgent:
    @lru_cache(maxsize=100)
    def cached_query(self, prompt_hash: str):
        return self.agent(prompt)
    
    def query(self, prompt: str):
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        return self.cached_query(prompt_hash)
```

### Best Practices
- Choose appropriate model sizes
- Implement caching for common queries
- Use async for I/O operations
- Monitor token usage
- Batch similar requests

---

## Production Deployment

### AWS Lambda Pattern
```python
import os
from aws_lambda_powertools import Logger, Tracer, Metrics

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Pre-load resources during cold start
AGENT = None

def get_agent():
    global AGENT
    if AGENT is None:
        AGENT = Agent(
            model=os.environ['MODEL_ID'],
            load_tools_from_directory=False,
            max_parallel_tools=1  # Limit for Lambda
        )
    return AGENT

@tracer.capture_lambda_handler
def lambda_handler(event, context):
    agent = get_agent()
    # Reset conversation for each request
    agent.messages = []
    
    response = agent(event['prompt'])
    return {'response': response}
```

### Container Deployment (ECS/EKS)
```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.agent_pool = AgentPool(size=20)
    yield
    # Shutdown
    await app.state.agent_pool.close()

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(request: ChatRequest):
    agent = app.state.agent_pool.acquire()
    try:
        response = await agent.invoke_async(request.prompt)
        return {"response": response}
    finally:
        app.state.agent_pool.release(agent)
```

### Best Practices
- Use environment variables for configuration
- Implement health checks
- Monitor resource usage
- Use structured logging
- Handle graceful shutdowns
- Implement request timeouts

---

## Summary

Building production-ready Strands applications requires understanding:

1. **Agent Lifecycle**: Choose patterns based on statefulness
2. **Structured I/O**: Use Pydantic for type safety
3. **Tool Design**: Keep tools focused and well-documented
4. **Error Handling**: Implement comprehensive retry logic
5. **Performance**: Optimize for your use case
6. **Deployment**: Follow cloud-native patterns

For complete examples and detailed implementations, refer to:
- Official Strands samples (especially samples 01-08)
- SDK source code for advanced patterns
- Community examples and tutorials

Remember: Start simple, measure performance, and optimize based on actual usage patterns.