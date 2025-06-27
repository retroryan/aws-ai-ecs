# Context Management in Strands Agents

## Overview

This document explains how context management works in the Strands Weather Agent and establishes best practices based on AWS Strands SDK documentation.

## Key Findings

### 1. Agents are Stateless and Recreated Per Request

**Current Pattern (CORRECT):**
```python
def _process_with_clients_sync(self, message: str, clients: List[tuple[str, MCPClient]], 
                               session_messages: Optional[List[Dict[str, Any]]] = None):
    with ExitStack() as stack:
        # Enter all client contexts
        for name, client in clients:
            stack.enter_context(client)
        
        # Create agent within context with conversation history
        agent = Agent(
            model=self.bedrock_model,
            tools=all_tools,
            system_prompt=self._get_system_prompt(),
            messages=session_messages or [],  # Pass conversation history
            conversation_manager=self.conversation_manager
        )
        
        response = agent(message)
        return response_text, agent.messages
```

**This is a best practice because:**
- Agents in Strands are designed to be stateless
- Each conversation turn gets a fresh agent instance
- Conversation history is maintained externally and passed via the `messages` parameter
- This promotes clean separation of concerns and scalability

### 2. ExitStack Usage Explained

The `ExitStack` pattern is used specifically for managing MCP client contexts, NOT for agent lifecycle:

```python
with ExitStack() as stack:
    # 1. Enter all MCP client contexts
    for name, client in clients:
        stack.enter_context(client)
    
    # 2. Now all clients are active and available
    # 3. Create agent with access to all client tools
    agent = Agent(tools=all_tools)
    
    # 4. Process the request
    response = agent(message)
    
# 5. ExitStack automatically closes all client contexts on exit
```

**Why ExitStack?**
- Manages multiple context managers (MCP clients) dynamically
- Ensures all clients are properly closed even if errors occur
- Cleaner than nested `with` statements
- Allows dynamic number of contexts

### 3. Session/Conversation Management

The weather agent implements both in-memory and file-based session storage:

```python
class MCPWeatherAgent:
    def __init__(self, session_storage_dir: Optional[str] = None):
        if session_storage_dir:
            # File-based session storage
            self.sessions_path = Path(session_storage_dir)
            self.sessions_path.mkdir(exist_ok=True)
        else:
            # In-memory session storage
            self.sessions = {}
```

**Best Practices:**
1. **External State Management**: Conversation state is stored outside the agent
2. **Session IDs**: Each conversation has a unique session ID
3. **Message History**: Previous messages are loaded and passed to new agent instances
4. **Persistence Options**: Choose based on requirements (memory vs. file vs. database)

## Strands SDK Best Practices

Based on the official documentation:

### 1. Conversation Manager Integration

```python
from strands.agent.conversation_manager import SlidingWindowConversationManager

# Configure conversation management
conversation_manager = SlidingWindowConversationManager(
    window_size=20,  # Keep last 20 message pairs
    should_truncate_results=True
)

# Pass to agent on creation
agent = Agent(
    model=model,
    tools=tools,
    messages=session_messages,  # Previous conversation
    conversation_manager=conversation_manager
)
```

### 2. Multi-Agent Patterns

When implementing multi-agent systems:

```python
# Hierarchical Pattern (Manager-Worker)
research_agent = Agent(tools=[web_search], system_prompt="Research specialist")
writer_agent = Agent(tools=[editor], system_prompt="Content writer")

# Wrap agents as tools for orchestrator
@tool
def research_topic(topic: str) -> str:
    return research_agent(f"Research: {topic}")

orchestrator = Agent(tools=[research_topic, write_content])
```

### 3. Production Deployment Pattern

For production environments:

```python
class AgentService:
    def __init__(self):
        self.model = BedrockModel(...)
        self.tools = [...]
        self.conversation_manager = SlidingWindowConversationManager()
    
    async def handle_request(self, message: str, session_id: str):
        # Load session
        session_messages = await self.load_session(session_id)
        
        # Create fresh agent instance
        agent = Agent(
            model=self.model,
            tools=self.tools,
            messages=session_messages,
            conversation_manager=self.conversation_manager
        )
        
        # Process request
        response = agent(message)
        
        # Save updated session
        await self.save_session(session_id, agent.messages)
        
        return response
```

## Current Implementation Analysis

### Strengths

1. **Correct Agent Recreation**: The weather agent correctly creates a new agent instance for each request
2. **Proper Context Management**: ExitStack is used appropriately for MCP client management
3. **Flexible Session Storage**: Supports both in-memory and persistent storage
4. **Conversation Manager Integration**: Uses SlidingWindowConversationManager for context window management

### Areas for Improvement

1. **Session Cleanup**: Consider implementing session expiration/cleanup
2. **Concurrent Session Handling**: Add locking for file-based storage if supporting concurrent requests
3. **Error Recovery**: Enhanced error handling for session load/save operations
4. **Monitoring**: Add metrics for session management (active sessions, session duration, etc.)

## Recommended Improvements

### 1. Session Management Enhancement

```python
class EnhancedSessionManager:
    def __init__(self, storage_dir: Optional[str] = None, ttl_hours: int = 24):
        self.storage_dir = storage_dir
        self.ttl = timedelta(hours=ttl_hours)
        self.locks = {}  # For concurrent access
    
    async def get_session(self, session_id: str) -> List[Dict[str, Any]]:
        async with self._get_lock(session_id):
            messages = await self._load_messages(session_id)
            
            # Check expiration
            if self._is_expired(session_id):
                await self._cleanup_session(session_id)
                return []
            
            return messages
    
    async def save_session(self, session_id: str, messages: List[Dict[str, Any]]):
        async with self._get_lock(session_id):
            await self._save_messages(session_id, messages)
            await self._update_timestamp(session_id)
```

### 2. Metrics Integration

```python
from strands.telemetry import metrics

class MetricsAwareAgent:
    def __init__(self):
        self.session_counter = metrics.Counter("sessions_total")
        self.active_sessions = metrics.Gauge("sessions_active")
        self.session_duration = metrics.Histogram("session_duration_seconds")
    
    async def handle_request(self, message: str, session_id: str):
        self.session_counter.inc()
        
        with self.session_duration.time():
            # Process request
            response = await self._process(message, session_id)
        
        return response
```

### 3. Production-Ready Context Manager

```python
class ProductionAgentContext:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.mcp_clients = []
        self.resources = []
    
    async def __aenter__(self):
        # Initialize all resources
        for server_url in self.config.mcp_servers:
            client = MCPClient(lambda: streamablehttp_client(server_url))
            self.mcp_clients.append(client)
            client.__enter__()
        
        # Collect tools
        all_tools = []
        for client in self.mcp_clients:
            tools = client.list_tools_sync()
            all_tools.extend(tools)
        
        # Create agent
        self.agent = Agent(
            model=self.config.model,
            tools=all_tools,
            system_prompt=self.config.system_prompt,
            conversation_manager=self.config.conversation_manager
        )
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup all resources
        for client in self.mcp_clients:
            try:
                client.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass
```

## Conclusion

The current weather agent implementation follows Strands best practices by:
1. Creating stateless agents per request
2. Using ExitStack correctly for resource management
3. Maintaining conversation context externally
4. Integrating with conversation managers

The suggested improvements focus on production readiness, monitoring, and concurrent access handling while maintaining the correct architectural patterns.