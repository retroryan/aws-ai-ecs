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
from contextlib import asynccontextmanager
import logging

# Configure logging
logging.getLogger("strands").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: Optional[MCPWeatherAgent] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent on startup and cleanup on shutdown."""
    global agent
    print("🚀 Starting AWS Strands Weather Agent API...")
    try:
        agent = await create_weather_agent()
        print("✅ AWS Strands Weather Agent API ready!")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise
    finally:
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

class QueryResponse(BaseModel):
    response: str
    session_id: Optional[str] = None

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
    Process a weather query using the Strands agent.
    
    Args:
        request: Query request with the user's question
        
    Returns:
        Agent's response
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        response = await agent.query(
            message=request.query,
            session_id=request.session_id
        )
        
        return QueryResponse(
            response=response,
            session_id=request.session_id
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query/structured", response_model=WeatherQueryResponse)
async def process_query_structured(request: QueryRequest):
    """
    Process a weather query and return structured output.
    
    This endpoint uses AWS Strands native structured output to:
    - Extract location information using LLM geographic knowledge
    - Call weather tools with precise coordinates
    - Return validated, structured response
    
    Args:
        request: Query request with the user's question
        
    Returns:
        Structured WeatherQueryResponse with locations, weather data, and metadata
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        response = await agent.query_structured(
            message=request.query,
            session_id=request.session_id
        )
        
        # Validate the response
        validation = agent.validate_response(response)
        if not validation.valid:
            logger.warning(f"Response validation issues: {validation.errors}")
        
        return response
        
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
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        session_info = agent.get_session_info(session_id)
        if session_info is None:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a conversation session."""
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        cleared = agent.clear_session(session_id)
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
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )