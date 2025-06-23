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
from weather_agent.mcp_agent import create_weather_agent, MCPWeatherAgent
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
    structured_output: bool

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

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8090,
        reload=True,
        log_level="info"
    )