# Proposal: Stateful Conversations for Weather Agent FastAPI Server

## Executive Summary

The weather agent already has comprehensive session management capabilities built into the `MCPWeatherAgent` class. The FastAPI server currently exposes these features but doesn't fully leverage them. This proposal outlines enhancements to make stateful conversations a first-class feature with improved API design and client experience.

## Current State Analysis

### Existing Capabilities
- `MCPWeatherAgent` already supports session management (lines 106-123 in mcp_agent.py)
- Sessions can be stored in-memory or file-based
- Conversation history is maintained via `SlidingWindowConversationManager`
- Session endpoints exist but need enhancement:
  - `GET /session/{session_id}` - Get session info
  - `DELETE /session/{session_id}` - Clear session
  - Query endpoints accept optional `session_id`

### Current Limitations
- No session creation endpoint - sessions are created implicitly
- Session ID generation happens in the agent, not the API layer
- No session listing or management features
- Limited session metadata (no TTL, user info, etc.)

## Proposed Architecture

### 1. Session Lifecycle Flow

```
Client                    FastAPI Server              MCPWeatherAgent
  |                           |                             |
  |--POST /sessions/create--->|                             |
  |                           |--Create Session------------>|
  |<--{session_id, ttl}-------|                             |
  |                           |                             |
  |--POST /query------------->|                             |
  |  {session_id, query}      |--Query with context------->|
  |                           |<--Response with history-----|
  |<--{response, session_id}--|                             |
  |                           |                             |
  |--GET /sessions/{id}------>|                             |
  |<--{history, metadata}-----|                             |
```

### 2. Enhanced API Contract

#### New Endpoints

```python
# Session Management
POST   /sessions/create       # Create new session
GET    /sessions             # List active sessions
GET    /sessions/{id}        # Get session details (enhanced)
DELETE /sessions/{id}        # Delete session
POST   /sessions/{id}/clear  # Clear history but keep session

# Query Endpoints (enhanced)
POST   /query                # Now returns session_id in response
POST   /query/structured     # Now returns session_id in response
```

#### Data Models

```python
class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    ttl_minutes: Optional[int] = 60  # Default 1 hour
    storage_type: Optional[str] = "memory"  # or "file"

class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: datetime
    expires_at: Optional[datetime]
    storage_type: str

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    create_session: bool = True  # Auto-create if not provided

class QueryResponse(BaseModel):
    response: str
    session_id: str  # Always included
    session_new: bool  # True if newly created
    conversation_turn: int

class SessionInfo(BaseModel):
    session_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: Optional[datetime]
    conversation_turns: int
    total_messages: int
    user_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    storage_type: str

class ConversationHistory(BaseModel):
    session_id: str
    messages: List[ConversationMessage]
    summary: Optional[str]  # AI-generated summary
```

### 3. Implementation Details

#### Key Implementation Changes

1. **Session Manager Layer** (new module: `session_manager.py`):
   ```python
   from dataclasses import dataclass
   from datetime import datetime
   from typing import Dict, List, Any, Optional
   
   @dataclass
   class SessionData:
       session_id: str
       created_at: datetime
       last_activity: datetime
       expires_at: Optional[datetime]
       conversation_turns: int = 0
       user_id: Optional[str] = None
       metadata: Dict[str, Any] = None
       storage_type: str = "memory"
   
   class SessionManager:
       def __init__(self, storage_dir: Optional[str] = None):
           self.sessions: Dict[str, SessionData] = {}
           self.storage_dir = storage_dir
           
       async def create_session(self, request: SessionCreateRequest) -> SessionData:
           # Generate ID, set TTL, initialize metadata
           
       async def get_session(self, session_id: str) -> Optional[SessionData]:
           # Return session if exists and not expired
   ```

2. **Enhanced Agent Integration**:
   - Session ID generation stays in API layer (FastAPI server)
   - The MCPWeatherAgent continues to accept session_id as parameter
   - **Note**: The command-line chatbot doesn't need updates as it doesn't use sessions by default
   - Session metadata support added to API layer only

3. **Query Flow Enhancement**:
   ```python
   @app.post("/query", response_model=QueryResponse)
   async def process_query(request: QueryRequest):
       # 1. Check/create session
       if not request.session_id and request.create_session:
           session = await session_manager.create_session(...)
           session_id = session.session_id
           session_new = True
       else:
           session_id = request.session_id
           session_new = False
       
       # 2. Process with agent
       response = await agent.query(request.query, session_id)
       
       # 3. Update session activity timestamp
       await session_manager.update_activity(session_id)
       
       # 4. Return enhanced response
       return QueryResponse(
           response=response,
           session_id=session_id,
           session_new=session_new,
           conversation_turn=session.conversation_turns
       )
   ```

### 4. Client Usage Examples

#### Python Client Example
```python
import httpx

async def weather_conversation():
    async with httpx.AsyncClient() as client:
        # First query - auto-creates session
        resp1 = await client.post("http://localhost:8090/query", 
            json={"query": "What's the weather in Seattle?"})
        data1 = resp1.json()
        session_id = data1["session_id"]
        
        # Follow-up using session context
        resp2 = await client.post("http://localhost:8090/query",
            json={
                "query": "How about tomorrow?",  # Knows we mean Seattle
                "session_id": session_id
            })
        
        # Get conversation history
        history = await client.get(f"http://localhost:8090/sessions/{session_id}")
```

#### JavaScript Client Example
```javascript
class WeatherClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }
    
    async query(text) {
        const response = await fetch(`${this.baseUrl}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: text,
                session_id: this.sessionId
            })
        });
        
        const data = await response.json();
        this.sessionId = data.session_id;  // Store for next query
        return data;
    }
}
```

### 5. Edge Cases and Error Handling

#### Session Management
- **Expired session handling**: Return 410 Gone with helpful message
- **Session not found**: Auto-create new session or return 404
- **Storage full**: Implement LRU eviction for in-memory storage
- **Concurrent access**: Use asyncio locks for session updates

#### Conversation Context
- **Context overflow**: Handled by `SlidingWindowConversationManager`
- **Invalid session data**: Validate and sanitize on load
- **Corrupted files**: Graceful fallback to new session

#### API Resilience
- Rate limiting per session
- Maximum sessions per user/IP
- Graceful degradation when MCP servers unavailable
- Circuit breaker for failing sessions

### 6. Configuration Options

```python
# Environment variables
SESSION_STORAGE_TYPE=file|memory
SESSION_STORAGE_DIR=/var/lib/weather-agent/sessions
SESSION_DEFAULT_TTL_MINUTES=60
SESSION_MAX_PER_USER=10
SESSION_CLEANUP_INTERVAL_SECONDS=300
SESSION_ENABLE_PERSISTENCE=true
```

### 7. Benefits

1. **Better User Experience**: Natural multi-turn conversations
2. **Context Awareness**: Follow-up questions work intuitively
3. **Efficiency**: Reduced token usage by leveraging context
4. **Analytics**: Track usage patterns and conversation flows
5. **Scalability**: File-based storage for horizontal scaling

### 8. Implementation Plan

#### Phase 1: Core Session Management (Initial Release) ✅ COMPLETED
**Goal**: Basic stateful conversations with minimal changes

- ✅ Implement `SessionManager` class with in-memory storage
- ✅ Add `SessionData` dataclass  
- ✅ Update `/query` and `/query/structured` to return session_id
- ✅ Implement basic session creation (auto-create on first query)
- ✅ Add `/sessions/{id}` GET endpoint for session info
- ✅ Add `/sessions/{id}` DELETE endpoint for clearing sessions
- ✅ Basic TTL support (sessions expire after inactivity)
- ✅ Update test_docker.sh to handle new response format

**Key Points**:
- No breaking changes to existing API
- Command-line chatbot continues to work unchanged
- Focus on core functionality only

**Implementation Details**:
- Created `weather_agent/session_manager.py` with `SessionManager` and `SessionData`
- Updated `QueryResponse` model to include `session_id`, `session_new`, and `conversation_turn`
- Enhanced `WeatherQueryResponse` with optional session fields
- Both `/query` and `/query/structured` endpoints now support sessions
- Session TTL defaults to 60 minutes (configurable via `SESSION_DEFAULT_TTL_MINUTES`)
- Sessions are auto-created on first query unless `create_session=false`

#### Phase 2: Enhanced Session Management
**Goal**: Explicit session control and management

- Add `POST /sessions/create` endpoint
- Add `GET /sessions` to list active sessions
- Add file-based storage option for persistence
- Implement session metadata support
- Add user_id tracking capability
- Enhanced error handling for expired sessions

#### Phase 3: Background Tasks & Cleanup
**Goal**: Production-ready session management

- Implement session cleanup background task
- Add automatic session persistence (for file-based storage)
- Implement LRU eviction for memory storage
- Add session count limits per user/IP
- Implement concurrent access controls

#### Phase 4: Advanced Features
**Goal**: Enhanced user experience and analytics

- Track conversation metrics (tokens, turns, response times)
- Add conversation summarization
- Implement session export functionality
- Add session search and filtering
- Implement session templates/presets
- Add webhook support for session events

#### Phase 5: Analytics & Monitoring
**Goal**: Operational insights

- Comprehensive metrics collection
- Session analytics dashboard
- Usage patterns analysis
- Cost tracking per session
- Performance monitoring

## Summary

This proposal builds upon the existing session capabilities in the weather agent to create a robust, scalable stateful conversation system. The key improvements include:

1. Explicit session lifecycle management
2. Enhanced API responses with session metadata
3. Better client developer experience
4. Proper error handling and edge cases
5. Configuration flexibility for different deployment scenarios

The implementation maintains backward compatibility while adding powerful new features for conversational AI applications.

## Phase 1 Implementation Summary

Phase 1 has been successfully completed with the following changes:

### New Files
- `weather_agent/session_manager.py` - Core session management functionality

### Modified Files
- `weather_agent/main.py` - Integrated SessionManager and updated endpoints
- `weather_agent/models/structured_responses.py` - Added session fields to WeatherQueryResponse
- `scripts/test_docker.sh` - Updated to handle new response format with session info

### API Changes (Backward Compatible)
- `/query` now returns: `{response, session_id, session_new, conversation_turn}`
- `/query/structured` includes optional session fields in response
- Session auto-creation is enabled by default (can be disabled with `create_session=false`)
- Sessions expire after 60 minutes of inactivity (configurable)

### Testing
The implementation can be tested using:
```bash
# Start services
./scripts/start_docker.sh

# Run tests (includes session info display)
./scripts/test_docker.sh

# Test session endpoints manually
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Seattle?"}'

# Use the returned session_id for follow-up queries
curl -X POST http://localhost:8090/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How about tomorrow?", "session_id": "<session_id>"}'
```