#!/usr/bin/env python3
"""
FastAPI server for the AWS Strands Weather Agent
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import uvicorn
import os
from .mcp_agent import create_weather_agent, MCPWeatherAgent
from .models.structured_responses import WeatherQueryResponse, ValidationResult
from .session_manager import SessionManager, SessionData
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.getLogger("strands").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
agent: Optional[MCPWeatherAgent] = None
session_manager: Optional[SessionManager] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent and session manager on startup and cleanup on shutdown."""
    global agent, session_manager
    print("🚀 Starting AWS Strands Weather Agent API...")
    
    # Add retry logic for MCP server connectivity
    max_retries = 5
    retry_delay = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            # Initialize agent
            agent = await create_weather_agent()
            
            # Initialize session manager
            default_ttl = int(os.getenv("SESSION_DEFAULT_TTL_MINUTES", "60"))
            session_manager = SessionManager(default_ttl_minutes=default_ttl)
            
            print("✅ AWS Strands Weather Agent API ready!")
            yield
            break
        except RuntimeError as e:
            if "No MCP servers are available" in str(e) and attempt < max_retries - 1:
                logger.warning(f"MCP servers not ready, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to initialize after {attempt + 1} attempts: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    # Cleanup (Strands handles this automatically)
    print("🧹 Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="AWS Strands Weather Agent API",
    description="Weather Agent powered by AWS Strands + FastMCP",
    version="2.0.0",
    lifespan=lifespan
)

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    create_session: bool = True  # Auto-create if not provided

class QueryResponse(BaseModel):
    response: str
    session_id: str  # Always included
    session_new: bool  # True if newly created
    conversation_turn: int

class AgentInfo(BaseModel):
    model: str
    region: str
    temperature: float
    mcp_servers: list[str]
    debug_logging: bool

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None
    }

@app.get("/info", response_model=AgentInfo)
async def get_agent_info():
    """Get information about the agent configuration."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return agent.get_agent_info()

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a weather query using the Strands agent with session support.
    
    Args:
        request: Query request with the user's question and optional session_id
        
    Returns:
        Agent's response with session information
    """
    if not agent or not session_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Handle session creation/retrieval
        session_new = False
        session_id = request.session_id
        
        if not session_id and request.create_session:
            # Create new session
            session = await session_manager.create_session()
            session_id = session.session_id
            session_new = True
        elif session_id:
            # Verify existing session
            session = await session_manager.get_session(session_id)
            if not session:
                if request.create_session:
                    # Session expired or not found, create new one
                    session = await session_manager.create_session()
                    session_id = session.session_id
                    session_new = True
                else:
                    raise HTTPException(status_code=404, detail="Session not found or expired")
        else:
            # No session_id and create_session is False
            raise HTTPException(status_code=400, detail="Session ID required when create_session is False")
        
        # Process query with agent
        response = await agent.query(
            message=request.query,
            session_id=session_id
        )
        
        # Update session activity
        await session_manager.update_activity(session_id)
        session = await session_manager.get_session(session_id)
        
        return QueryResponse(
            response=response,
            session_id=session_id,
            session_new=session_new,
            conversation_turn=session.conversation_turns if session else 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/structured", response_model=WeatherQueryResponse)
async def process_query_structured(request: QueryRequest):
    """
    Process a weather query and return structured output with session support.
    
    This endpoint uses AWS Strands native structured output to:
    - Extract location information using LLM geographic knowledge
    - Call weather tools with precise coordinates
    - Return validated, structured response with session information
    
    Args:
        request: Query request with the user's question and optional session_id
        
    Returns:
        Structured WeatherQueryResponse with locations, weather data, and session metadata
    """
    if not agent or not session_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        # Handle session creation/retrieval (same logic as /query)
        session_new = False
        session_id = request.session_id
        
        if not session_id and request.create_session:
            # Create new session
            session = await session_manager.create_session()
            session_id = session.session_id
            session_new = True
        elif session_id:
            # Verify existing session
            session = await session_manager.get_session(session_id)
            if not session:
                if request.create_session:
                    # Session expired or not found, create new one
                    session = await session_manager.create_session()
                    session_id = session.session_id
                    session_new = True
                else:
                    raise HTTPException(status_code=404, detail="Session not found or expired")
        else:
            # No session_id and create_session is False
            raise HTTPException(status_code=400, detail="Session ID required when create_session is False")
        
        # Process structured query with agent
        response = await agent.query_structured(
            message=request.query,
            session_id=session_id
        )
        
        # Update session activity
        await session_manager.update_activity(session_id)
        session = await session_manager.get_session(session_id)
        
        # Add session information to response
        response.session_id = session_id
        response.session_new = session_new
        response.conversation_turn = session.conversation_turns if session else 1
        
        # Validate the response
        validation = agent.validate_response(response)
        if not validation.valid:
            logger.warning(f"Response validation issues: {validation.errors}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing structured query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/validate")
async def validate_query_response(response: WeatherQueryResponse):
    """
    Validate a structured weather response.
    
    Args:
        response: WeatherQueryResponse to validate
        
    Returns:
        ValidationResult with any errors, warnings, or suggestions
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        validation = agent.validate_response(response)
        return validation
        
    except Exception as e:
        logger.error(f"Error validating response: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/status")
async def get_mcp_status():
    """Check the status of MCP server connections."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        connectivity = await agent.test_connectivity()
        return {
            "servers": connectivity,
            "connected_count": sum(1 for v in connectivity.values() if v),
            "total_count": len(connectivity)
        }
    except Exception as e:
        logger.error(f"Error checking MCP status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a conversation session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    try:
        session = await session_manager.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found or expired")
        
        # Get additional info from agent if available
        agent_session_info = None
        if agent:
            agent_session_info = agent.get_session_info(session_id)
        
        # Combine session manager and agent info
        session_info = session_manager.get_session_info(session)
        if agent_session_info:
            session_info['message_count'] = agent_session_info.get('total_messages', 0)
        
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a conversation session."""
    if not session_manager:
        raise HTTPException(status_code=503, detail="Session manager not initialized")
    
    try:
        # Clear from session manager
        cleared = await session_manager.delete_session(session_id)
        
        # Also clear from agent if available
        if agent and cleared:
            agent.clear_session(session_id)
        
        if not cleared:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": f"Session {session_id} cleared successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("API_PORT", "8090"))
    uvicorn.run(
        "weather_agent.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )