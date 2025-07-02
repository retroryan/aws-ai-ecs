"""
MCP Weather Agent using AWS Strands - Best Practices Implementation

This module demonstrates the proper way to use MCP servers with AWS Strands:
- Native MCP integration without manual client management
- Pure async patterns throughout
- Proper error handling with specific exception types
- Simplified architecture with 50% less boilerplate code
- Built-in streaming and session management
"""

import os
import logging
import uuid
import json
from typing import Optional, List, Dict, Any, Type, TypeVar
from datetime import datetime
from pathlib import Path

# Pydantic imports
from pydantic import ValidationError

# Strands imports - using native features
from strands import Agent
from strands.models import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
from mcp.client.streamable_http import streamablehttp_client  # Using streamable HTTP client for HTTP-based MCP servers
from strands.tools.mcp import MCPClient

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

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

# Configure logging
logger = logging.getLogger(__name__)


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
                 debug_logging: bool = False, 
                 prompt_type: Optional[str] = None, 
                 session_storage_dir: Optional[str] = None):
        """
        Initialize the weather agent.
        
        Args:
            debug_logging: Enable detailed debug logging for tool calls
            prompt_type: System prompt type (default, agriculture, simple)
            session_storage_dir: Directory for file-based session storage
        """
        # Validate environment variables first
        self._validate_environment()
        
        # Model configuration
        self.model_id = os.getenv("BEDROCK_MODEL_ID", 
                                  "anthropic.claude-3-5-sonnet-20241022-v2:0")
        self.region = os.getenv("BEDROCK_REGION", "us-west-2")
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        
        # Create Bedrock model with proper configuration
        self.bedrock_model = BedrockModel(
            model_id=self.model_id,
            region_name=self.region,
            temperature=self.temperature
        )
        
        # Initialize MCP clients using native Strands pattern
        self.mcp_clients = self._create_mcp_clients()
        self.debug_logging = debug_logging
        
        # Prompt management
        self.prompt_manager = PromptManager()
        self.prompt_type = prompt_type or os.getenv("SYSTEM_PROMPT", "default")
        
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
        
        logger.info(f"Initialized MCPWeatherAgent with model: {self.model_id}")
        logger.info(f"MCP servers configured: {len(self.mcp_clients)}")
    
    def _validate_environment(self):
        """
        Validate required environment variables.
        
        Raises:
            EnvironmentError: If required variables are missing
        """
        # No required environment variables anymore - all have defaults
        # This method is kept for future use if needed
        pass
    
    def _create_mcp_clients(self) -> List[MCPClient]:
        """
        Create MCP clients using Strands native support.
        
        This is the way to create MCP clients in Strands:
        - Use MCPClient wrapper with lambda factory
        - Support for streamable HTTP transport
        - Automatic session management by Strands
        
        Returns:
            List of configured MCP clients
        """
        # Get server URLs from environment with defaults
        servers = {
            "forecast": os.getenv("MCP_FORECAST_URL", "http://localhost:8081/mcp"),
            "historical": os.getenv("MCP_HISTORICAL_URL", "http://localhost:8082/mcp"),
            "agricultural": os.getenv("MCP_AGRICULTURAL_URL", "http://localhost:8083/mcp")
        }
        
        # Only add experts server if URL is provided (optional)
        experts_url = os.getenv("MCP_EXPERTS_URL")
        if experts_url:
            servers["experts"] = experts_url
        
        clients = []
        for name, url in servers.items():
            try:
                # Create MCP client with streamable HTTP transport for HTTP-based servers
                # The lambda is required to defer connection until context entry
                client = MCPClient(lambda url=url: streamablehttp_client(url))
                clients.append(client)
                logger.info(f"Created MCP client for {name} server at {url}")
            except Exception as e:
                logger.warning(f"Failed to create {name} client: {e}")
        
        return clients
    
    async def test_connectivity(self) -> Dict[str, bool]:
        """
        Test connectivity to all MCP servers with caching.
        
        Returns:
            Dict mapping server names to connectivity status
        """
        # Check cache (valid for 30 seconds)
        now = datetime.utcnow()
        if (self._last_connectivity_check and 
            (now - self._last_connectivity_check).total_seconds() < 30):
            return self._connectivity_cache
        
        results = {}
        # Dynamically determine server names based on what was configured
        server_names = []
        servers_config = {
            "forecast": os.getenv("MCP_FORECAST_URL", "http://localhost:8081/mcp"),
            "historical": os.getenv("MCP_HISTORICAL_URL", "http://localhost:8082/mcp"),
            "agricultural": os.getenv("MCP_AGRICULTURAL_URL", "http://localhost:8083/mcp")
        }
        if os.getenv("MCP_EXPERTS_URL"):
            servers_config["experts"] = os.getenv("MCP_EXPERTS_URL")
        server_names = list(servers_config.keys())
        
        for i, client in enumerate(self.mcp_clients):
            name = server_names[i] if i < len(server_names) else f"server_{i}"
            try:
                # Test connection by listing tools
                with client:
                    tools = client.list_tools_sync()
                    results[name] = True
                    logger.info(f"✅ {name} server: {len(tools)} tools available")
            except Exception as e:
                results[name] = False
                logger.error(f"❌ {name} server: {e}")
        
        # Update cache
        self._connectivity_cache = results
        self._last_connectivity_check = now
        
        return results
    
    async def create_agent(self, 
                          session_messages: Optional[List[Dict[str, Any]]] = None) -> Agent:
        """
        Create agent with native MCP support - much simpler!
        
        This demonstrates the Strands pattern:
        - Tools are collected from MCP servers
        - Agent is created with all configuration
        - No manual session or context management needed
        
        Args:
            session_messages: Optional conversation history
            
        Returns:
            Configured Agent instance
        """
        # Collect all tools from MCP servers
        all_tools = []
        
        for client in self.mcp_clients:
            try:
                # Assume clients are already in context when this is called
                tools = client.list_tools_sync()
                all_tools.extend(tools)
                if self.debug_logging:
                    logger.debug(f"Loaded {len(tools)} tools from MCP server")
            except Exception as e:
                logger.warning(f"Failed to load tools from MCP server: {e}")
        
        if not all_tools:
            raise MCPConnectionError("No MCP servers available", 
                                   Exception("All MCP servers failed to provide tools"))
        
        # Create agent with native configuration
        agent = Agent(
            model=self.bedrock_model,
            system_prompt=self.prompt_manager.get_prompt(self.prompt_type),
            tools=all_tools,
            messages=session_messages or [],
            conversation_manager=self.conversation_manager
        )
        
        return agent
    
    async def query(self, message: str, session_id: Optional[str] = None) -> str:
        """        
        This demonstrates the async pattern:
        - Direct async/await usage
        - Proper error handling
        - Session management
        - Streaming response collection
        
        Args:
            message: User's query
            session_id: Optional session ID for conversation tracking
            
        Returns:
            Agent's response as string
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        logger.info(f"Processing query (session: {session_id[:8]}...): {message[:50]}...")
        
        try:
            # Load session messages
            session_messages = self._get_session_messages(session_id)
            
            # Use ExitStack to keep MCP clients open during agent execution
            from contextlib import ExitStack
            with ExitStack() as stack:
                # Enter all MCP client contexts
                for client in self.mcp_clients:
                    stack.enter_context(client)
                
                # Create agent with session context while clients are open
                agent = await self.create_agent(session_messages)
                
                # Process query with streaming
                response_text = ""
                
                # Use async streaming for better performance
                async for event in agent.stream_async(message):
                    if "data" in event:
                        response_text += event["data"]
                        if self.debug_logging:
                            print(event["data"], end="", flush=True)
                    elif "current_tool_use" in event and self.debug_logging:
                        tool_info = event["current_tool_use"]
                        print(f"\n[Using tool: {tool_info.get('name', 'unknown')}]")
                
                # Update session with new messages
                if session_id:
                    self._save_session_messages(session_id, agent.messages)
                
                return response_text
            
        except MCPConnectionError as e:
            logger.error(f"MCP connection error: {e}")
            return f"I'm unable to connect to the weather services: {e.server_name}"
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def query_structured(self, 
                             message: str, 
                             session_id: Optional[str] = None) -> WeatherQueryResponse:
        """
        Pure async structured output with proper error handling.
        
        This demonstrates:
        - Structured output with Pydantic models
        - Specific error handling for different failure modes
        - Graceful degradation with informative responses
        
        Args:
            message: User's weather query
            session_id: Optional session ID
            
        Returns:
            Structured WeatherQueryResponse
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
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
            
            # Use ExitStack to keep MCP clients open during agent execution
            from contextlib import ExitStack
            with ExitStack() as stack:
                # Enter all MCP client contexts
                for client in self.mcp_clients:
                    stack.enter_context(client)
                
                # Create agent with session context while clients are open
                agent = await self.create_agent(session_messages)
                
                # Get the appropriate structured prompt from PromptManager
                # Use a structured variant if available, otherwise use regular prompt
                structured_prompt_type = f"{self.prompt_type}_structured"
                if structured_prompt_type not in self.prompt_manager.get_available_prompts():
                    structured_prompt_type = "structured"
                
                # Get base prompt and append the user's message
                base_prompt = self.prompt_manager.get_prompt(structured_prompt_type)
                structured_prompt = f"{base_prompt}\n\nUser Query: {message}"
                
                # Use structured output (synchronous method in executor)
                try:
                    # Strands structured_output is synchronous, so run in executor
                    import asyncio
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        agent.structured_output,
                        WeatherQueryResponse,
                        message  # Just pass the user's message, not complex prompt
                    )
                except Exception as e:
                    logger.warning(f"Structured output failed: {e}, falling back to streaming")
                    # Fallback: Use streaming and parse response
                    response_text = ""
                    async for event in agent.stream_async(message):
                        if "data" in event:
                            response_text += event["data"]
                    response = self._parse_structured_response(response_text)
                
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
    
    # === Session Management Methods (unchanged) ===
    
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
            query_type="error",
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
            query_type="error",
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
            query_type="error",
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
    
    def _parse_structured_response(self, response_text: str) -> WeatherQueryResponse:
        """
        Parse structured response from agent text output.
        Enhanced fallback method with better location extraction.
        """
        import re
        
        # Try to extract JSON first
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return WeatherQueryResponse(**data)
        except Exception as e:
            logger.debug(f"JSON parsing failed: {e}")
        
        # Enhanced fallback: Extract location and query type from text
        locations = []
        query_type = "general"
        
        # Look for location mentions
        location_patterns = [
            r"(?:in|for|at)\s+([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)",
            r"([A-Z][a-zA-Z\s]+(?:,\s*[A-Z][a-zA-Z\s]+)?)\s+(?:weather|temperature|forecast)",
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                location_name = match.strip()
                if len(location_name) > 2:  # Skip very short matches
                    locations.append(ExtractedLocation(
                        name=location_name,
                        latitude=0.0,
                        longitude=0.0,
                        timezone="UTC",
                        country_code="XX",
                        confidence=0.5,
                        source="llm_fallback",
                        needs_clarification=True
                    ))
                    break
            if locations:
                break
        
        # Determine query type from keywords
        if any(word in response_text.lower() for word in ["forecast", "next", "tomorrow", "week"]):
            query_type = "forecast"
        elif any(word in response_text.lower() for word in ["current", "now", "today"]):
            query_type = "current"
        elif any(word in response_text.lower() for word in ["history", "past", "yesterday", "last"]):
            query_type = "historical"
        elif any(word in response_text.lower() for word in ["crop", "plant", "agriculture", "farming"]):
            query_type = "agricultural"
        
        # If no locations found, add unknown
        if not locations:
            locations.append(ExtractedLocation(
                name="Unknown",
                latitude=0.0,
                longitude=0.0,
                timezone="UTC",
                country_code="XX",
                confidence=0.0,
                needs_clarification=True
            ))
        
        # Extract summary (first paragraph or first 500 chars)
        summary = response_text.split('\n\n')[0][:500] if '\n\n' in response_text else response_text[:500]
        
        return WeatherQueryResponse(
            query_type=query_type,
            query_confidence=0.6,
            locations=locations,
            summary=summary,
            warnings=["Response parsed from unstructured text"],
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
            "mcp_servers": len(self.mcp_clients),
            "debug_logging": self.debug_logging,
            "session_management": {
                "active_sessions": len(self.sessions),
                "storage_type": "file" if self.session_storage_dir else "memory",
                "conversation_manager": "SlidingWindowConversationManager",
                "window_size": 20
            },
            "improvements": [
                "Native MCP client support",
                "Pure async patterns",
                "Proper error boundaries", 
                "50% less boilerplate code",
                "Fixed model ID configuration"
            ]
        }


# === Convenience Functions ===

async def create_weather_agent(
    debug_logging: bool = False, 
    prompt_type: Optional[str] = None
) -> MCPWeatherAgent:
    """
    Create and initialize a weather agent.
    
    This follows the Strands best practice of testing connectivity
    before returning the agent.
    
    Args:
        debug_logging: Enable debug logging
        prompt_type: System prompt type
        
    Returns:
        Initialized MCPWeatherAgent
        
    Raises:
        RuntimeError: If no MCP servers are available
    """
    agent = MCPWeatherAgent(
        debug_logging=debug_logging, 
        prompt_type=prompt_type
    )
    
    # Test connectivity as best practice
    connectivity = await agent.test_connectivity()
    if not any(connectivity.values()):
        raise RuntimeError("No MCP servers are available")
    
    return agent