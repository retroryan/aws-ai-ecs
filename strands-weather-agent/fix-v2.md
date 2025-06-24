# Fix Proposal: Session Context Not Persisting in Multi-Turn Conversations

## Problem Analysis

Based on the test output and code review, there are two critical issues preventing proper session context persistence:

### Issue 1: Session ID Not Being Returned in API Response
The test output shows:
```
Session: No sessi... | New: false | Turn: 0
Session: null... | New: false | Turn: 0
```

This indicates the API is not properly returning session information in the response.

### Issue 2: Agent Not Maintaining Context Between Turns
The follow-up queries don't have context from previous queries:
- Query 1: "What's the weather like in Seattle?"
- Query 2: "How about tomorrow?" → Agent asks for location again
- Query 3: "Will it rain this weekend?" → Agent asks for location again

## Root Cause

After reviewing the Strands documentation and the `multi_turn_conversation_solution.md`, the core issue is that **the Agent is not being re-initialized with the conversation history on each turn**.

According to the Strands documentation:
> "You can initialize an agent with existing messages to continue a conversation"

The current implementation passes `session_id` to the agent's query method, but the agent itself needs to be re-initialized with the full message history.

## Solution

### Phase 1: Fix Session ID Return (Immediate Fix)

The current implementation might have an issue with how the agent is initialized or how sessions are created. Let's verify:

1. **Check Agent Initialization**: Ensure the agent is properly initialized with session support
2. **Debug Response Format**: Log the actual response to see what's being returned

### Phase 2: Implement Proper Message History Management

Based on the Strands patterns, we need to:

1. **Store message history** after each query
2. **Re-initialize the agent** with message history on each query
3. **Use the built-in conversation manager** properly

## Implementation Plan

### Step 1: Debug Current Implementation

Add logging to understand what's happening:

```python
# In weather_agent/main.py - process_query endpoint
logger.info(f"Session ID before query: {session_id}")
response = await agent.query(
    message=request.query,
    session_id=session_id
)
logger.info(f"Response type: {type(response)}")
logger.info(f"Session after query: {session.session_id if session else 'No session'}")
```

### Step 2: Fix MCPWeatherAgent to Properly Manage Sessions

The issue is in `mcp_agent.py`. The agent needs to be re-initialized with message history on each query:

```python
# In weather_agent/mcp_agent.py - _process_with_clients_sync method

def _process_with_clients_sync(self, message: str, clients: List[tuple[str, MCPClient]], 
                               session_messages: Optional[List[Dict[str, Any]]] = None) -> tuple[str, List[Dict[str, Any]]]:
    """
    Process query synchronously within MCP client contexts with conversation history.
    """
    with ExitStack() as stack:
        # Enter all client contexts
        for name, client in clients:
            stack.enter_context(client)
        
        # Collect all tools
        all_tools = []
        for name, client in clients:
            tools = client.list_tools_sync()
            all_tools.extend(tools)
            logger.info(f"Using {len(tools)} tools from {name}")
        
        # CRITICAL FIX: Pass session_messages to Agent initialization
        agent = Agent(
            model=self.bedrock_model,
            tools=all_tools,
            system_prompt=self._get_system_prompt(),
            max_parallel_tools=2,
            messages=session_messages or [],  # This is already correct!
            conversation_manager=self.conversation_manager
        )
        
        # Process query
        response = agent(message)
        
        # Return both response and updated messages
        return response_text, agent.messages  # This is also correct!
```

Wait, the code already does this correctly! Let me check why it's not working...

### Step 3: Verify Session Storage and Retrieval

The issue might be in how sessions are stored and retrieved. Let's check:

1. **Session Storage**: The `_save_session_messages` method saves messages
2. **Session Retrieval**: The `_get_session_messages` method loads messages
3. **Message Format**: Ensure messages are in the correct Strands format

### Step 4: Fix the API Response Issue

The real issue appears to be that the session information is not being returned properly. Looking at the test script output:

```javascript
session_id=$(echo "$response1" | jq -r '.session_id')
```

But it's showing "No sessi..." which suggests the response doesn't contain a valid session_id.

## Proposed Fix

### 1. Add Debug Logging

First, add debug logging to understand what's happening:

```python
# In weather_agent/main.py
@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    # ... existing code ...
    
    # Add debug logging
    logger.debug(f"Creating response with session_id: {session_id}, new: {session_new}, turn: {session.conversation_turns}")
    
    response_obj = QueryResponse(
        response=response,
        session_id=session_id,
        session_new=session_new,
        conversation_turn=session.conversation_turns if session else 1
    )
    
    logger.debug(f"Response object: {response_obj.model_dump()}")
    
    return response_obj
```

### 2. Fix Message Format

Ensure messages are stored in the correct Strands format:

```python
# The correct format according to Strands docs:
{"role": "user", "content": [{"text": "message"}]}
{"role": "assistant", "content": [{"text": "response"}]}
```

### 3. Verify Session Persistence

The current implementation stores sessions correctly, but we need to ensure the messages are in the right format when saved and loaded.

## Testing Plan

1. **Add logging** to track session creation and retrieval
2. **Verify message format** matches Strands requirements
3. **Test with simplified scenario** to isolate the issue
4. **Monitor agent.messages** to ensure history is maintained

## Quick Fix to Test

As an immediate test, let's verify if the issue is with the response format or the session handling:

```bash
# Test the API directly
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}' | jq

# Check if session_id is in the response
```

## Investigation Progress

### Initial Docker Testing (2025-06-24)

**Step 1: Started Docker containers**
```bash
./scripts/start_docker.sh
```
- All services started successfully
- Noticed AWS credential warnings in logs (may not be related)

**Step 2: Raw API Response Test**
```bash
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}' | jq
```

**Result:**
```json
{
  "response": "Based on the weather data...",
  "session_id": null
}
```

**Finding:** The API is returning `"session_id": null`, confirming the session is not being created or returned.

**Step 3: Check Docker Container Files**
```bash
docker exec weather-agent-app ls -la /app/weather_agent/
```

**Critical Finding:** The `session_manager.py` file is NOT present in the Docker container! The container is using old code without the session management implementation.

**Root Cause Identified:** Docker images need to be rebuilt to include the new session management code.

**Step 4: Rebuild Docker Images**
```bash
docker compose build --no-cache
./scripts/start_docker.sh
```

**Success:** session_manager.py is now in the container.

**Step 5: Test API After Rebuild**
```bash
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}' | jq
```

**New Issue Found:** Server crashed with import error. The issue is that uvicorn.run in main.py uses "main:app" but when running as a module it needs "weather_agent.main:app".

**Step 6: Fix uvicorn Module Path**
Fixed main.py line 320:
```python
uvicorn.run(
    "weather_agent.main:app",  # Changed from "main:app"
    host="0.0.0.0",
    port=port,
    reload=True,
    log_level="info"
)
```

**Step 7: Rebuild and Test Again**
```bash
./scripts/stop_docker.sh && docker compose build weather-agent && ./scripts/start_docker.sh
sleep 5
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}' | jq
```

**Success!** Response now includes valid session_id:
```json
{
  "response": "Based on the weather data...",
  "session_id": "dc2f9d41-323c-46fa-884f-7f8094903fdf",
  "session_new": true,
  "conversation_turn": 1
}
```

**Step 8: Test Context Persistence**
```bash
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How about tomorrow?", "session_id": "dc2f9d41-323c-46fa-884f-7f8094903fdf"}' | jq
```

**Success!** The agent remembers we're talking about Seattle:
- Response provides tomorrow's forecast for Seattle without needing location
- `session_new` is false
- `conversation_turn` is 2

**Step 9: Run Full Multi-Turn Test**
```bash
./scripts/multi-turn-test.sh
```

**Complete Success!** All tests pass:
- Basic multi-turn conversation ✓
- Location context persistence ✓
- Agricultural context ✓
- Session management ✓
- Structured output with sessions ✓

## Root Cause Summary

The issue was that the Docker containers were using outdated code without the session management implementation. The fix required:

1. Rebuilding Docker images to include session_manager.py
2. Fixing the uvicorn module path in main.py for Docker execution
3. Ensuring all files were properly copied to the container

## Solution Verified

The session context persistence is now fully functional. The multi-turn conversation test confirms:
- Sessions are created and tracked properly
- Message history is maintained between API calls
- The agent remembers context from previous queries
- Follow-up questions work without repeating information

## Recommended Immediate Actions

1. **Check Docker logs** to see if there are any errors during session creation ✓
2. **Add debug logging** to the session manager and API endpoints
3. **Verify the response model** is correctly serializing the session information
4. **Test with a simple endpoint** that just creates and returns a session

## Long-term Solution

If the current architecture continues to have issues, consider:

1. **Simplifying session management** by storing messages directly in the SessionManager
2. **Using a single source of truth** for sessions instead of dual storage (SessionManager + Agent)
3. **Implementing session middleware** to handle session management transparently
4. **Adding comprehensive logging** for session lifecycle events

## Critical Discovery

After reviewing the code more carefully, I noticed that the `query` method in `MCPWeatherAgent` is correctly implemented to handle sessions. However, the issue might be that:

1. **The session is created but the ID might not be properly passed through the response chain**
2. **The test script might be failing to parse the response correctly**

Looking at the test output more carefully:
- "Session: No sessi..." is likely "No session" being truncated
- This suggests `session_id` is being parsed as the string "No session" from the jq command

The issue is likely in the test script's jq parsing:
```bash
session_id=$(echo "$response" | jq -r '.session_id // "No session"')
```

If the response doesn't have a session_id field or it's null, it defaults to "No session".

## Immediate Fix

1. **Verify the actual API response**:
```bash
# Run this to see the raw response
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}'
```

2. **Check if the Weather Agent is running in a mode that doesn't support sessions** - perhaps it needs to be initialized with session support enabled.

3. **The real issue might be that the agent is not initialized with a session storage directory**, so sessions are not being persisted properly.

## Most Likely Root Cause

Looking at the implementation again, I suspect the issue is in how the Weather Agent main.py is importing and running:

```python
# The main.py might be running from weather_agent/ directory
# But it's importing from relative imports
from .mcp_agent import create_weather_agent, MCPWeatherAgent
```

If the Docker container or test environment is not finding the updated code with session support, it might be falling back to an older version or failing silently.

## Recommended Debug Steps

1. **Add a simple debug endpoint** to verify session creation:
```python
@app.get("/debug/session-test")
async def session_test():
    if not session_manager:
        return {"error": "Session manager not initialized"}
    
    # Create a test session
    session = await session_manager.create_session()
    return {
        "session_id": session.session_id,
        "session_manager_active": True,
        "session_count": await session_manager.get_session_count()
    }
```

2. **Verify the import paths** are correct and the updated code is being used.

3. **Check Docker logs** for any import errors or initialization failures:
```bash
docker compose logs weather-agent | grep -i error
docker compose logs weather-agent | grep -i session
```

## Next Steps

1. Add debug logging to identify where session information is lost
2. Verify the API response format matches what the test expects
3. Ensure message history is properly formatted for Strands
4. Test with minimal example to isolate the issue
5. Implement fixes based on findings
6. Check if the agent needs to be initialized with session storage enabled