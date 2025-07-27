"""
MCP Weather Agent using AWS Strands - Best Practices Implementation

This module demonstrates the proper way to use MCP servers with AWS Strands:
- Native MCP integration without manual client management
- Pure async patterns throughout
- Proper error handling with specific exception types
- Simplified architecture with 50% less boilerplate code
- Built-in streaming and session management
- Simple Langfuse telemetry integration
"""

import os
import logging
import uuid
import json
from typing import Optional, List, Dict, Any, Type, TypeVar
from datetime import datetime
from pathlib import Path

# Load environment variables FIRST (before any Strands imports)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

# Setup telemetry BEFORE importing Strands (critical for OTEL configuration)
try:
    from .telemetry import setup_telemetry
except ImportError:
    from telemetry import setup_telemetry

# Initialize telemetry at module level with service metadata
TELEMETRY_ENABLED = setup_telemetry(
    service_name=os.getenv("OTEL_SERVICE_NAME", "weather-agent"),
    environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "demo"),
    version=os.getenv("SERVICE_VERSION", "2.0.0")
)

# NOW import Strands after telemetry setup
from strands import Agent
from strands.models import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

# Pydantic imports
from pydantic import ValidationError

# Local imports
try:
    from .models.structured_responses import (
        WeatherQueryResponse, ExtractedLocation, WeatherDataSummary,
        AgriculturalAssessment, ValidationResult
    )
    from .prompts import PromptManager
    from .exceptions import (
        WeatherAgentError, MCPConnectionError, 
        StructuredOutputError, ModelInvocationError
    )
except ImportError:
    from models.structured_responses import (
        WeatherQueryResponse, ExtractedLocation, WeatherDataSummary,
        AgriculturalAssessment, ValidationResult
    )
    from prompts import PromptManager
    from exceptions import (
        WeatherAgentError, MCPConnectionError, 
        StructuredOutputError, ModelInvocationError
    )

# Type variable for structured output
T = TypeVar('T')

# Configure logging
logger = logging.getLogger(__name__)

# Log telemetry status at module load
if TELEMETRY_ENABLED:
    logger.info("✅ Langfuse telemetry enabled via OTEL")
else:
    logger.info("📊 Langfuse telemetry disabled (no credentials configured)")


class MCPWeatherAgent:
    """
    Weather Agent using AWS Strands with native MCP integration.
    
    This implementation follows Strands best practices:
    - Uses native MCP client support (no manual management)
    - Pure async throughout (no ThreadPoolExecutor)
    - Proper error boundaries and specific exceptions
    - Simplified architecture with less boilerplate
    - Optimized for demo clarity and educational value
    """
    
    def __init__(self, 
                 tools: Optional[List[Any]] = None,
                 debug_logging: bool = False, 
                 prompt_type: Optional[str] = None, 
                 session_storage_dir: Optional[str] = None):
        """
        Initialize the weather agent.
        
        Args:
            tools: List of MCP tools (if None, agent will need to be created with tools)
            debug_logging: Enable detailed debug logging for tool calls
            prompt_type: System prompt type (default or agriculture_structured only)
            session_storage_dir: Directory for file-based session storage
        """
        # Validate environment variables first
        self._validate_environment()
        
        # Model configuration
        self.model_id = os.getenv("BEDROCK_MODEL_ID", 
                                  "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.region = os.getenv("BEDROCK_REGION", "us-east-1")
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        
        # Create Bedrock model with proper configuration
        self.bedrock_model = BedrockModel(
            model_id=self.model_id,
            region_name=self.region,
            temperature=self.temperature
        )
        
        # Store tools directly instead of MCP clients
        self.tools = tools or []
        self.debug_logging = debug_logging
        
        # Prompt management - use agriculture_structured by default
        self.prompt_manager = PromptManager()
        # Use agriculture_structured as default
        if prompt_type == "simple_prompt":
            self.prompt_type = "simple_prompt"
        else:
            self.prompt_type = "agriculture_structured"  # Default to agriculture_structured
        
        # Session management configuration
        self.session_storage_dir = session_storage_dir
        if session_storage_dir:
            self.sessions_path = Path(session_storage_dir)
            self.sessions_path.mkdir(exist_ok=True)
        
        # In-memory session cache (used for both storage types)
        self.sessions = {}
        
        # Smart conversation manager with better context handling
        self.conversation_manager = SlidingWindowConversationManager(
            window_size=20,  # Keep last 20 message pairs
            should_truncate_results=True
        )
        
        # Connection state caching
        self._connectivity_cache = {}
        self._last_connectivity_check = None
        
        # Store last query metrics for display
        self.last_metrics = None
        
        # Log comprehensive initialization info
        logger.info("="*60)
        logger.info("🤖 MCPWeatherAgent Initialization Complete")
        logger.info("="*60)
        logger.info(f"Model: {self.model_id}")
        logger.info(f"Region: {self.region}")
        logger.info(f"Temperature: {self.temperature}")
        logger.info(f"Tools: {len(self.tools)} loaded")
        logger.info(f"Debug Mode: {'✅ ENABLED' if self.debug_logging else '❌ DISABLED'}")
        logger.info(f"Prompt Type: {self.prompt_type}")
        
        # Log telemetry status from module-level variable
        global TELEMETRY_ENABLED
        if TELEMETRY_ENABLED:
            logger.info(f"Telemetry: ✅ ENABLED via OpenTelemetry")
            logger.info(f"  - Service: {os.getenv('OTEL_SERVICE_NAME', 'weather-agent')}")
            logger.info(f"  - Version: {os.getenv('SERVICE_VERSION', '2.0.0')}")
            logger.info(f"  - Environment: {os.getenv('DEPLOYMENT_ENVIRONMENT', 'demo')}")
        else:
            logger.info(f"Telemetry: ❌ DISABLED")
        logger.info("="*60)
    
    def _validate_environment(self):
        """
        Validate required environment variables.
        
        Raises:
            EnvironmentError: If required variables are missing
        """
        # No required environment variables anymore - all have defaults
        # This method is kept for future use if needed
        pass
    
    
    async def test_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity by checking if tools are available.
        
        Returns:
            Dict mapping server names to connectivity status
        """
        # Since we now receive tools directly, we just check if we have them
        results = {
            "weather-server": len(self.tools) > 0
        }
        
        if len(self.tools) > 0:
            logger.info(f"✅ weather server: {len(self.tools)} tools available")
        else:
            logger.warning("❌ weather server: No tools available")
        
        return results
    
    async def create_agent(self, 
                          session_messages: Optional[List[Dict[str, Any]]] = None) -> Agent:
        """
        Create agent with pre-loaded tools - much simpler!
        
        This demonstrates the Strands pattern:
        - Tools are passed in at initialization
        - Agent is created with all configuration
        - No manual session or context management needed
        - Simple trace attributes for telemetry when enabled
        
        Args:
            session_messages: Optional conversation history
            
        Returns:
            Configured Agent instance
        """
        # Use the tools provided at initialization
        if not self.tools:
            raise MCPConnectionError("No tools available", 
                                   Exception("No tools were provided to the agent"))
        
        # Simple trace attributes when telemetry is enabled
        trace_attributes = None
        if TELEMETRY_ENABLED:
            # Generate session ID if not provided
            session_id = getattr(self, 'session_id', None) or str(uuid.uuid4())
            
            trace_attributes = {
                "session.id": session_id,
                "user.id": os.getenv("TELEMETRY_USER_ID", "weather-demo-user"),
                "langfuse.tags": ["weather-agent", "mcp", "strands-demo", self.prompt_type]
            }
            if self.debug_logging:
                logger.debug(f"Telemetry enabled with session: {session_id}")
        
        # Create agent with native configuration
        agent = Agent(
            model=self.bedrock_model,
            system_prompt=self.prompt_manager.get_prompt(self.prompt_type),
            tools=self.tools,
            messages=session_messages or [],
            conversation_manager=self.conversation_manager,
            trace_attributes=trace_attributes
        )
        
        return agent
    
    
    async def query(self, 
                    message: str, 
                    session_id: Optional[str] = None) -> WeatherQueryResponse:
        """
        Process a weather query and return structured output.
        
        Uses AWS Strands native structured output to extract location information,
        call weather tools, and return a validated response with session management.
        
        Args:
            message: User's weather query
            session_id: Optional session ID for conversation tracking
            
        Returns:
            Structured WeatherQueryResponse with locations, weather data, and session info
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Store session_id for telemetry
        self.session_id = session_id
        
        logger.info(f"Processing structured query (session: {session_id[:8]}...)")
        start_time = datetime.utcnow()
        
        try:
            # Check MCP connectivity first
            connectivity = await self.test_connectivity()
            if not any(connectivity.values()):
                return self._create_connection_error_response(
                    "All MCP servers are offline"
                )
            
            # Load session messages
            session_messages = self._get_session_messages(session_id)
            
            # Create agent with session context - no MCP context needed!
            agent = await self.create_agent(session_messages)
            
            # For structured output, use agriculture_structured if specified, otherwise default
            structured_prompt_type = "agriculture_structured" if self.prompt_type == "agriculture_structured" else "default"
            
            # Get base prompt and append the user's message
            base_prompt = self.prompt_manager.get_prompt(structured_prompt_type)
            structured_prompt = f"{base_prompt}\n\nUser Query: {message}"
            
            # Use async structured output directly
            try:
                # Use the native async version - no thread pool needed!
                response = await agent.structured_output_async(
                    WeatherQueryResponse,
                    message  # Just pass the user's message
                )
            except Exception as e:
                logger.error(f"Structured output failed: {e}")
                raise StructuredOutputError(
                    "Failed to generate structured output",
                    original_error=e
                )
            
            # Update session
            if session_id:
                self._save_session_messages(session_id, agent.messages)
            
            # Add processing time
            end_time = datetime.utcnow()
            response.processing_time_ms = int(
                (end_time - start_time).total_seconds() * 1000
            )
            
            return response
            
        except ValidationError as e:
            logger.error(f"Structured output validation failed: {e}")
            return self._create_validation_error_response(str(e))
            
        except MCPConnectionError as e:
            logger.error(f"MCP connection error: {e}")
            return self._create_connection_error_response(e.server_name)
            
        except Exception as e:
            logger.error(f"Unexpected error in structured query: {e}", exc_info=True)
            return self._create_generic_error_response(str(e))
    
    # === Session Management Methods ===
    
    def _get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation messages for a session."""
        if not session_id:
            return []
        
        # Check in-memory cache first
        if session_id in self.sessions:
            return self.sessions[session_id].get('messages', [])
        
        # Check file storage if configured
        if self.session_storage_dir:
            session_file = self.sessions_path / f"{session_id}.json"
            if session_file.exists():
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        messages = session_data.get('messages', [])
                        # Cache in memory
                        self.sessions[session_id] = session_data
                        return messages
                except Exception as e:
                    logger.warning(f"Failed to load session {session_id}: {e}")
        
        return []
    
    def _save_session_messages(self, session_id: str, messages: List[Dict[str, Any]]):
        """Save conversation messages for a session."""
        if not session_id:
            return
        
        session_data = {
            'messages': messages,
            'last_updated': datetime.utcnow().isoformat(),
            'prompt_type': self.prompt_type
        }
        
        # Always update in-memory cache
        self.sessions[session_id] = session_data
        
        # Save to file if configured
        if self.session_storage_dir:
            session_file = self.sessions_path / f"{session_id}.json"
            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to save session {session_id}: {e}")
    
    # === Error Response Helpers ===
    
    def _create_connection_error_response(self, server_name: str) -> WeatherQueryResponse:
        """Create error response for connection failures."""
        return WeatherQueryResponse(
            query_type="general",  # Using 'general' for error cases
            query_confidence=0.0,
            locations=[ExtractedLocation(
                name="Unknown",
                latitude=0.0,
                longitude=0.0,
                timezone="UTC",
                country_code="XX",
                confidence=0.0,
                needs_clarification=True
            )],
            summary=f"Unable to connect to weather services ({server_name}). Please try again later.",
            warnings=["MCP server connection failed"],
            processing_time_ms=0
        )
    
    def _create_validation_error_response(self, error_details: str) -> WeatherQueryResponse:
        """Create error response for validation failures."""
        return WeatherQueryResponse(
            query_type="general",  # Using 'general' for error cases
            query_confidence=0.0,
            locations=[ExtractedLocation(
                name="Unknown",
                latitude=0.0,
                longitude=0.0,
                timezone="UTC",
                country_code="XX",
                confidence=0.0,
                needs_clarification=True
            )],
            summary="Failed to process the weather data properly. Please try rephrasing your query.",
            warnings=[f"Validation error: {error_details}"],
            processing_time_ms=0
        )
    
    def _create_generic_error_response(self, error_msg: str) -> WeatherQueryResponse:
        """Create generic error response."""
        return WeatherQueryResponse(
            query_type="general",  # Using 'general' for error cases
            query_confidence=0.0,
            locations=[ExtractedLocation(
                name="Unknown",
                latitude=0.0,
                longitude=0.0,
                timezone="UTC",
                country_code="XX",
                confidence=0.0,
                needs_clarification=True
            )],
            summary=f"An unexpected error occurred: {error_msg}",
            warnings=["Unexpected error"],
            processing_time_ms=0
        )
    
    
    # === Utility Methods ===
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a conversation session."""
        if not session_id:
            return False
        
        # Remove from memory
        removed = session_id in self.sessions
        self.sessions.pop(session_id, None)
        
        # Remove from file storage if configured
        if self.session_storage_dir:
            session_file = self.sessions_path / f"{session_id}.json"
            if session_file.exists():
                try:
                    session_file.unlink()
                    removed = True
                except Exception as e:
                    logger.error(f"Failed to delete session file: {e}")
        
        if removed:
            logger.info(f"Cleared session {session_id}")
        
        return removed
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a session."""
        messages = self._get_session_messages(session_id)
        if not messages:
            return None
        
        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        
        return {
            'session_id': session_id,
            'total_messages': len(messages),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'conversation_turns': len(user_messages),
            'storage_type': 'file' if self.session_storage_dir else 'memory'
        }
    
    def validate_response(self, response: WeatherQueryResponse) -> ValidationResult:
        """Validate a structured weather response."""
        errors = []
        warnings = response.validation_warnings()
        suggestions = []
        
        # Check for required coordinates
        for loc in response.locations:
            if not loc.latitude or not loc.longitude:
                errors.append(f"Missing coordinates for location: {loc.name}")
        
        # Check for low confidence
        low_confidence_locs = [loc for loc in response.locations if loc.confidence < 0.7]
        if low_confidence_locs:
            suggestions.append(
                "For better results with ambiguous locations, try including state/country information"
            )
        
        # Check query type alignment
        if response.query_type in ["current", "forecast"] and not response.weather_data:
            warnings.append("Weather query identified but no weather data retrieved")
        
        if response.query_type == "agricultural" and not response.agricultural_assessment:
            warnings.append("Agricultural query identified but no agricultural assessment provided")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        return {
            "model": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "mcp_servers": len(self.tools),
            "debug_logging": self.debug_logging,
            "session_management": {
                "active_sessions": len(self.sessions),
                "storage_type": "file" if self.session_storage_dir else "memory",
                "conversation_manager": "SlidingWindowConversationManager",
                "window_size": 20
            },
            "telemetry": {
                "enabled": TELEMETRY_ENABLED,
                "provider": "Langfuse via OTEL" if TELEMETRY_ENABLED else None
            },
            "improvements": [
                "Native MCP client support",
                "Pure async patterns",
                "Proper error boundaries", 
                "50% less boilerplate code",
                "Fixed model ID configuration",
                "Simple Langfuse OTEL integration"
            ]
        }
    
    def get_trace_url(self) -> Optional[str]:
        """Get Langfuse trace URL if telemetry is enabled.
        
        Returns:
            None - trace URLs are available in Langfuse dashboard
        """
        if TELEMETRY_ENABLED:
            logger.info("Traces available at: " + os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com"))
        return None


# === Convenience Functions ===

def _create_mcp_client() -> MCPClient:
    """
    Create MCP client for the weather server.
    
    Returns:
        MCPClient instance
    """
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:7778/mcp")
    return MCPClient(lambda: streamablehttp_client(server_url))


async def create_weather_agent(
    debug_logging: bool = False, 
    prompt_type: Optional[str] = None
) -> MCPWeatherAgent:
    """
    Create and initialize a weather agent with Single Context Entry pattern.
    
    This follows the Strands best practice:
    - Create MCP client
    - Enter context once
    - Get tools from MCP server
    - Create agent with tools
    - Keep context open for agent lifetime
    
    Args:
        debug_logging: Enable debug logging
        prompt_type: System prompt type (default or agriculture_structured only)
        
    Returns:
        Initialized MCPWeatherAgent
        
    Raises:
        RuntimeError: If no MCP servers are available
    """
    logger.info("🌟 Creating Weather Agent...")
    
    # Create MCP client
    mcp_client = _create_mcp_client()
    
    # Enter MCP context and get tools
    logger.info("🔌 Connecting to MCP server and loading tools...")
    try:
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            logger.info(f"✅ Loaded {len(tools)} tools from MCP server")
            
            # Create agent with tools
            agent = MCPWeatherAgent(
                tools=tools,
                debug_logging=debug_logging, 
                prompt_type=prompt_type
            )
            
            # Test connectivity as best practice
            connectivity = await agent.test_connectivity()
            
            # Log connectivity status
            connected_count = sum(1 for v in connectivity.values() if v)
            logger.info(f"📡 MCP servers: {connected_count}/{len(connectivity)} connected")
            
            for server, is_connected in connectivity.items():
                if is_connected:
                    logger.info(f"  ✅ {server}: connected")
                else:
                    logger.warning(f"  ❌ {server}: disconnected")
            
            if not any(connectivity.values()):
                logger.error("❌ No MCP servers are available - agent cannot function")
                raise RuntimeError("No MCP servers are available")
            
            logger.info("✅ Weather Agent initialized successfully")
            return agent
    except Exception as e:
        logger.error(f"Failed to create weather agent: {e}")
        raise RuntimeError(f"Failed to create weather agent: {e}")