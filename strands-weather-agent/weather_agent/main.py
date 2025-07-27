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
import sys
import argparse
from datetime import datetime
from pathlib import Path
try:
    from .mcp_agent import MCPWeatherAgent
    from .models.structured_responses import WeatherQueryResponse, ValidationResult
    from .session_manager import SessionManager, SessionData
except ImportError:
    from mcp_agent import MCPWeatherAgent
    from models.structured_responses import WeatherQueryResponse, ValidationResult
    from session_manager import SessionManager, SessionData
from contextlib import asynccontextmanager, ExitStack
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

# Configure logging
logging.getLogger("strands").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
agent: Optional[MCPWeatherAgent] = None
session_manager: Optional[SessionManager] = None
debug_mode: bool = False
global_metrics: Optional['SessionMetrics'] = None
mcp_client: Optional[MCPClient] = None
exit_stack: Optional[ExitStack] = None


def configure_debug_logging(enable_debug: bool = False):
    """
    Configure debug logging for AWS Strands with file output.
    
    Args:
        enable_debug: Whether to enable debug logging
    """
    if not enable_debug:
        return
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    # Create timestamped log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = logs_dir / f"weather_api_debug_{timestamp}.log"
    
    # Configure root logger for debug
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler - INFO level for cleaner output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s | %(name)s | %(message)s")
    console_handler.setFormatter(console_formatter)
    
    # File handler - DEBUG level for detailed logs
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Enable debug for specific Strands modules as per the guide
    logging.getLogger("strands").setLevel(logging.DEBUG)
    logging.getLogger("strands.tools").setLevel(logging.DEBUG)
    logging.getLogger("strands.models").setLevel(logging.DEBUG)
    logging.getLogger("strands.event_loop").setLevel(logging.DEBUG)
    logging.getLogger("strands.agent").setLevel(logging.DEBUG)
    
    # Also enable debug for our modules
    logging.getLogger("weather_agent").setLevel(logging.DEBUG)
    logging.getLogger("__main__").setLevel(logging.DEBUG)
    
    # FastAPI/Uvicorn specific loggers
    logging.getLogger("uvicorn").setLevel(logging.DEBUG)
    logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)
    
    logger.debug(f"\n🔍 Debug logging enabled. Logs will be written to: {log_file}")
    logger.debug("📊 Console will show INFO level, file will contain DEBUG details.")
    logger.debug("\n🔍 DEBUG MODE ENABLED:")
    logger.debug("   - Model's natural language will appear as it streams")
    logger.debug("   - 🔧 [AGENT DEBUG - Tool Call] = Our agent's tool usage logging")
    logger.debug("   - 📥 [AGENT DEBUG - Tool Input] = Tool parameters being sent")
    logger.debug("   - Strands internal debug logs = Framework's internal processing\n")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the agent and session manager on startup and cleanup on shutdown."""
    global agent, session_manager, debug_mode, global_metrics, mcp_client, exit_stack
    
    # Check debug mode from environment variable
    debug_mode = os.getenv("WEATHER_AGENT_DEBUG", "false").lower() == "true"
    
    # Configure debug logging if enabled
    configure_debug_logging(debug_mode)
    
    logger.info("🚀 Starting AWS Strands Weather Agent API...")
    
    # Log telemetry status with enhanced debugging
    telemetry_enabled = os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"
    if telemetry_enabled:
        # Check if Langfuse credentials are configured
        pk = os.getenv("LANGFUSE_PUBLIC_KEY")
        sk = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
        
        if pk and sk:
            logger.info(f"📊 Telemetry: ✅ ENABLED")
            logger.info(f"   - Langfuse Host: {host}")
            logger.info(f"   - Service: {os.getenv('OTEL_SERVICE_NAME', 'weather-agent')}")
            logger.info(f"   - Environment: {os.getenv('DEPLOYMENT_ENVIRONMENT', 'demo')}")
            
            # Enhanced debugging information
            if debug_mode:
                logger.info(f"   - Public Key (first/last 8): {pk[:8]}...{pk[-8:]}" if len(pk) > 16 else f"   - Public Key: {pk}")
                logger.info(f"   - Secret Key (first/last 8): {sk[:8]}...{sk[-8:]}" if len(sk) > 16 else f"   - Secret Key: {sk}")
                logger.info(f"   - OTEL Endpoint: {os.getenv('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', 'NOT SET')}")
                logger.info(f"   - OTEL Headers (length): {len(os.getenv('OTEL_EXPORTER_OTLP_TRACES_HEADERS', ''))}")
        else:
            logger.info(f"📊 Telemetry: ⚠️  CONFIGURED but missing Langfuse credentials")
            logger.info(f"   - LANGFUSE_PUBLIC_KEY: {'SET' if pk else 'NOT SET'}")
            logger.info(f"   - LANGFUSE_SECRET_KEY: {'SET' if sk else 'NOT SET'}")
            logger.info(f"   - LANGFUSE_HOST: {host}")
            logger.info(f"   - Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable")
    else:
        logger.info(f"📊 Telemetry: ❌ DISABLED (ENABLE_TELEMETRY=false)")
    
    # Import and initialize global metrics tracker
    try:
        from .metrics_display import SessionMetrics
    except ImportError:
        from metrics_display import SessionMetrics
    
    global_metrics = SessionMetrics()
    
    # Create MCP client
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:7778/mcp")
    mcp_client = MCPClient(lambda: streamablehttp_client(server_url))
    
    # Create ExitStack to manage MCP client context for app lifetime
    exit_stack = ExitStack()
    
    # Add retry logic for MCP server connectivity
    max_retries = 5
    retry_delay = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            # Enter MCP context once for the entire app lifetime
            exit_stack.enter_context(mcp_client)
            
            # Get tools from MCP server
            tools = mcp_client.list_tools_sync()
            logger.info(f"✅ Loaded {len(tools)} tools from MCP server")
            
            # Initialize agent with tools
            agent = MCPWeatherAgent(
                tools=tools,
                debug_logging=debug_mode
            )
            
            # Initialize session manager
            default_ttl = int(os.getenv("SESSION_DEFAULT_TTL_MINUTES", "60"))
            session_manager = SessionManager(default_ttl_minutes=default_ttl)
            
            logger.info("✅ AWS Strands Weather Agent API ready!")
            yield
            break
        except Exception as e:
            exit_stack.close()  # Clean up on error
            if "list_tools_sync" in str(e) and attempt < max_retries - 1:
                logger.warning(f"MCP server not ready, attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                # Recreate client and stack for retry
                mcp_client = MCPClient(lambda: streamablehttp_client(server_url))
                exit_stack = ExitStack()
            else:
                logger.error(f"Failed to initialize after {attempt + 1} attempts: {e}")
                raise
    
    # Cleanup and show final metrics
    logger.info("\n🧹 Shutting down...")
    
    # Close MCP client context
    if exit_stack:
        exit_stack.close()
    
    # Show final session metrics if any queries were processed
    if global_metrics and global_metrics.total_queries > 0:
        logger.info("\n📊 Final Usage Statistics:")
        logger.info(global_metrics.get_summary())

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

class PerformanceMetrics(BaseModel):
    total_tokens: int
    input_tokens: int
    output_tokens: int
    latency_ms: int
    latency_seconds: float
    throughput_tokens_per_second: float
    model: str
    cycles: int

# QueryResponse removed - using structured WeatherQueryResponse for all queries

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


@app.post("/query", response_model=WeatherQueryResponse)
async def process_query(request: QueryRequest):
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
        # Log query processing start
        if debug_mode:
            logger.info("="*60)
            logger.info("🔄 PROCESSING YOUR QUERY")
            logger.info("="*60)
            logger.info(f"📝 Query: {request.query}")
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
        response = await agent.query(
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
        
        # Prepare metrics data if available
        if hasattr(agent, 'last_metrics') and agent.last_metrics:
            try:
                from .metrics_display import format_metrics
            except ImportError:
                from metrics_display import format_metrics
            
            # Log formatted metrics
            logger.info(format_metrics(agent.last_metrics))
            
            # Add to global metrics
            if global_metrics:
                global_metrics.add_query(agent.last_metrics)
            
            # Extract metrics for response
            total_tokens = agent.last_metrics.accumulated_usage.get('totalTokens', 0)
            input_tokens = agent.last_metrics.accumulated_usage.get('inputTokens', 0)
            output_tokens = agent.last_metrics.accumulated_usage.get('outputTokens', 0)
            latency_ms = agent.last_metrics.accumulated_metrics.get('latencyMs', 0)
            latency_seconds = latency_ms / 1000.0
            throughput = total_tokens / latency_seconds if latency_seconds > 0 else 0
            
            model_id = os.environ.get('BEDROCK_MODEL_ID', 'unknown')
            model_name = model_id.split('.')[-1].split('-v')[0] if '.' in model_id else model_id
            
            # Add metrics to structured response
            response.metrics = PerformanceMetrics(
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                latency_seconds=latency_seconds,
                throughput_tokens_per_second=throughput,
                model=model_name,
                cycles=agent.last_metrics.cycle_count
            ).model_dump()
        
        # Log query completion
        if debug_mode:
            logger.info("="*60)
            logger.info("✅ RESPONSE COMPLETE")
            logger.info("="*60)
        
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AWS Strands Weather Agent API Server"
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging with detailed Strands traces to file'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv("API_PORT", "7777")),
        help='Port to run the server on (default: 7777)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        default=True,
        help='Enable auto-reload for development (default: True)'
    )
    
    args = parser.parse_args()
    
    # Set global debug mode - check both CLI arg and environment variable
    debug_mode = args.debug or os.getenv("WEATHER_AGENT_DEBUG", "false").lower() == "true"
    
    # Configure debug logging if requested
    if debug_mode:
        configure_debug_logging(enable_debug=True)
    
    # Run the server
    uvicorn.run(
        "weather_agent.main:app",
        host="0.0.0.0",
        port=args.port,
        reload=args.reload,
        log_level="debug" if debug_mode else "info"
    )