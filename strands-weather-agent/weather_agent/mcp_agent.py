"""
MCP Weather Agent using AWS Strands

This module demonstrates how to use MCP servers with AWS Strands:
- Native MCP integration without custom wrappers
- Automatic tool discovery and execution
- Built-in streaming and session management
- 50% less code than orchestration frameworks
"""

import asyncio
import os
import logging
import uuid
import json
from typing import Optional, List, Dict, Any, Type, TypeVar
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

# Pydantic imports for error handling
from pydantic import ValidationError

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from strands.agent.conversation_manager import SlidingWindowConversationManager
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient
# from strands.tools.structured_output import convert_pydantic_to_tool_spec  # Not available in current version

# Local imports
from .models.structured_responses import (
    WeatherQueryResponse, ExtractedLocation, WeatherDataSummary,
    AgriculturalAssessment, ValidationResult
)
from .prompts import PromptManager

# Type variable for structured output
T = TypeVar('T')

# Load environment variables
from pathlib import Path
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
    Weather agent using AWS Strands with MCP integration.
    
    This agent connects to MCP servers for weather data and uses
    Strands' native capabilities for tool orchestration.
    """
    
    def __init__(self, debug_logging: bool = False, prompt_type: Optional[str] = None, session_storage_dir: Optional[str] = None):
        """
        Initialize the weather agent.
        
        Args:
            debug_logging: Whether to show detailed debug logging for tool calls
            prompt_type: Type of system prompt to use (default, agriculture, simple)
                        Can also be set via SYSTEM_PROMPT environment variable
            session_storage_dir: Directory to store session files (optional)
        """
        # Model configuration
        self.model_id = os.getenv("BEDROCK_MODEL_ID", 
                                  "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
        self.region = os.getenv("BEDROCK_REGION", "us-west-2")
        self.temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        
        # Create Bedrock model
        self.bedrock_model = BedrockModel(
            model_id=self.model_id,
            region_name=self.region,
            temperature=self.temperature
        )
        
        # MCP server configuration
        self.mcp_servers = self._get_mcp_servers()
        self.debug_logging = debug_logging
        
        # For async/sync bridge
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        # System prompt configuration with PromptManager
        self.prompt_manager = PromptManager()
        self.prompt_type = prompt_type or os.getenv("SYSTEM_PROMPT", "default")
        
        # Session management - can use either in-memory or file-based storage
        self.session_storage_dir = session_storage_dir
        if session_storage_dir:
            # File-based session storage
            self.sessions_path = Path(session_storage_dir)
            self.sessions_path.mkdir(exist_ok=True)
            self.sessions = {}  # Cache for loaded sessions
        else:
            # In-memory session storage
            self.sessions = {}
        
        # Conversation manager for handling context window overflow
        self.conversation_manager = SlidingWindowConversationManager(
            window_size=20,  # Keep last 20 message pairs
            should_truncate_results=True
        )
        
        logger.info(f"Initialized MCPWeatherAgent with model: {self.model_id}")
        logger.info(f"Session storage: {'file-based' if session_storage_dir else 'in-memory'}")
    
    def _get_mcp_servers(self) -> Dict[str, str]:
        """Get MCP server URLs from environment or defaults."""
        return {
            "forecast": os.getenv("MCP_FORECAST_URL", "http://localhost:8081/mcp"),
            "historical": os.getenv("MCP_HISTORICAL_URL", "http://localhost:8082/mcp"),
            "agricultural": os.getenv("MCP_AGRICULTURAL_URL", "http://localhost:8083/mcp")
        }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt using the PromptManager."""
        return self.prompt_manager.get_prompt(self.prompt_type)
    
    def _create_mcp_clients(self) -> List[tuple[str, MCPClient]]:
        """Create MCP client instances."""
        clients = []
        
        for name, url in self.mcp_servers.items():
            try:
                client = MCPClient(
                    lambda url=url: streamablehttp_client(url)
                )
                clients.append((name, client))
                logger.info(f"Created MCP client for {name}")
            except Exception as e:
                logger.warning(f"Failed to create {name} client: {e}")
        
        return clients
    
    async def test_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all MCP servers."""
        results = {}
        
        for name, url in self.mcp_servers.items():
            try:
                client = MCPClient(
                    lambda url=url: streamablehttp_client(url)
                )
                
                # Test within context
                with client:
                    tools = client.list_tools_sync()
                    results[name] = True
                    logger.info(f"✅ {name} server: {len(tools)} tools available")
                    
            except Exception as e:
                results[name] = False
                logger.error(f"❌ {name} server: {e}")
        
        return results
    
    def _get_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get conversation messages for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of messages in Strands format
        """
        if not session_id:
            return []
        
        if self.session_storage_dir:
            # File-based storage
            session_file = self.sessions_path / f"{session_id}.json"
            
            if session_file.exists():
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                        return session_data.get('messages', [])
                except Exception as e:
                    logger.warning(f"Failed to load session {session_id}: {e}")
                    return []
            else:
                return []
        else:
            # In-memory storage
            return self.sessions.get(session_id, {}).get('messages', [])
    
    def _save_session_messages(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        """
        Save conversation messages for a session.
        
        Args:
            session_id: The session identifier
            messages: List of messages to save
        """
        if not session_id:
            return
        
        session_data = {
            'messages': messages,
            'last_updated': datetime.utcnow().isoformat(),
            'prompt_type': self.prompt_type
        }
        
        if self.session_storage_dir:
            # File-based storage
            session_file = self.sessions_path / f"{session_id}.json"
            
            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                # Cache in memory for faster access
                if session_id not in self.sessions:
                    self.sessions[session_id] = {}
                self.sessions[session_id]['messages'] = messages
                
            except Exception as e:
                logger.error(f"Failed to save session {session_id}: {e}")
        else:
            # In-memory storage
            self.sessions[session_id] = session_data
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a conversation session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if session was cleared, False if it didn't exist
        """
        if not session_id:
            return False
        
        if self.session_storage_dir:
            # File-based storage
            session_file = self.sessions_path / f"{session_id}.json"
            
            if session_file.exists():
                try:
                    session_file.unlink()
                    # Remove from cache
                    self.sessions.pop(session_id, None)
                    logger.info(f"Cleared session {session_id}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to clear session {session_id}: {e}")
                    return False
            else:
                return False
        else:
            # In-memory storage
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Cleared session {session_id}")
                return True
            else:
                return False
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session info dict or None if session doesn't exist
        """
        if not session_id:
            return None
        
        messages = self._get_session_messages(session_id)
        if not messages:
            return None
        
        # Count message types
        user_messages = [m for m in messages if m.get('role') == 'user']
        assistant_messages = [m for m in messages if m.get('role') == 'assistant']
        
        return {
            'session_id': session_id,
            'total_messages': len(messages),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'conversation_turns': len(user_messages),  # Each user message is a turn
            'storage_type': 'file' if self.session_storage_dir else 'memory'
        }
    
    def _process_with_clients_sync(self, message: str, clients: List[tuple[str, MCPClient]], 
                                   session_messages: Optional[List[Dict[str, Any]]] = None) -> tuple[str, List[Dict[str, Any]]]:
        """
        Process query synchronously within MCP client contexts with conversation history.
        
        Args:
            message: The user's query
            clients: List of MCP client tuples
            session_messages: Previous conversation messages
            
        Returns:
            Tuple of (response_text, updated_messages)
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
            
            if self.debug_logging:
                print(f"\n🔧 Available tools: {len(all_tools)}")
                for tool in all_tools[:3]:  # Show first 3 as example
                    tool_name = getattr(tool, 'name', 'unknown')
                    tool_desc = getattr(tool, 'description', '')[:60] if hasattr(tool, 'description') else ''
                    print(f"   - {tool_name}: {tool_desc}...")
            
            # Create agent within context with conversation history
            agent = Agent(
                model=self.bedrock_model,
                tools=all_tools,
                system_prompt=self._get_system_prompt(),
                max_parallel_tools=2,
                messages=session_messages or [],  # Pass conversation history
                conversation_manager=self.conversation_manager
            )
            
            # Process query
            response = agent(message)
            
            # Convert response to string if needed
            response_text = ""
            if hasattr(response, 'content'):
                response_text = response.content
            elif hasattr(response, 'text'):
                response_text = response.text
            else:
                response_text = str(response)
            
            # Return both response and updated messages
            return response_text, agent.messages
    
    async def query(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a query using the weather agent with conversation context.
        
        Args:
            message: The user's query
            session_id: Session ID for conversation tracking. If None, a new session is created.
            
        Returns:
            The agent's response
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        logger.info(f"Processing query (session: {session_id[:8]}...): {message[:50]}...")
        
        if self.debug_logging:
            print(f"\n📝 Query: {message}")
            print(f"🔑 Session: {session_id}")
        
        # Load conversation history
        session_messages = self._get_session_messages(session_id)
        
        if self.debug_logging and session_messages:
            print(f"📚 Loading {len(session_messages)} previous messages")
        
        # Create MCP clients
        clients = self._create_mcp_clients()
        
        if not clients:
            return "I'm unable to connect to the weather services. Please try again later."
        
        try:
            # Run synchronous processing in thread pool with conversation history
            loop = asyncio.get_event_loop()
            response, updated_messages = await loop.run_in_executor(
                self.executor,
                self._process_with_clients_sync,
                message,
                clients,
                session_messages
            )
            
            # Save updated conversation to session
            self._save_session_messages(session_id, updated_messages)
            
            if self.debug_logging:
                print(f"\n✅ Response generated successfully")
                print(f"💾 Saved {len(updated_messages)} messages to session")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def query_structured(self, message: str, session_id: Optional[str] = None) -> WeatherQueryResponse:
        """
        Process a query and return structured response using AWS Strands native capabilities with conversation context.
        
        This method leverages the agent's ability to:
        1. Extract location information using LLM geographic knowledge
        2. Call weather tools with precise coordinates
        3. Format the response according to the WeatherQueryResponse schema
        4. Maintain conversation context across multiple turns
        
        Args:
            message: The user's weather query
            session_id: Session ID for conversation tracking. If None, a new session is created.
            
        Returns:
            Structured WeatherQueryResponse with locations, weather data, and metadata
        """
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        logger.info(f"Processing structured query (session: {session_id[:8]}...): {message[:50]}...")
        start_time = datetime.utcnow()
        
        # Load conversation history
        session_messages = self._get_session_messages(session_id)
        
        if self.debug_logging and session_messages:
            print(f"📚 Loading {len(session_messages)} previous messages for structured query")
        
        # Create MCP clients
        clients = self._create_mcp_clients()
        
        if not clients:
            # Return error response
            return WeatherQueryResponse(
                query_type="general",
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
                summary="I'm unable to connect to the weather services. Please try again later.",
                warnings=["No MCP servers available"],
                processing_time_ms=0
            )
        
        try:
            # Process with structured output and conversation history
            response, updated_messages = await self._process_structured_query(message, clients, session_messages)
            
            # Save updated conversation to session
            self._save_session_messages(session_id, updated_messages)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            response.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if self.debug_logging:
                print(f"💾 Saved {len(updated_messages)} messages to structured query session")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in structured query: {e}")
            # Return error response
            return WeatherQueryResponse(
                query_type="general",
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
                summary=f"I encountered an error processing your request: {str(e)}",
                warnings=["Processing error occurred"],
                processing_time_ms=0
            )
    
    def _process_structured_query_sync(self, message: str, clients: List[tuple[str, MCPClient]], 
                                       session_messages: Optional[List[Dict[str, Any]]] = None) -> tuple[WeatherQueryResponse, List[Dict[str, Any]]]:
        """
        Process structured query synchronously within MCP client contexts using native Strands structured output.
        
        Args:
            message: The user's query
            clients: List of MCP client tuples
            session_messages: Previous conversation messages
            
        Returns:
            Tuple of (structured_response, updated_messages)
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
            
            # Create agent within context with conversation history
            agent = Agent(
                model=self.bedrock_model,
                tools=all_tools,
                system_prompt=self._get_system_prompt(),
                max_parallel_tools=2,
                messages=session_messages or [],  # Pass conversation history
                conversation_manager=self.conversation_manager
            )
            
            # Use native Strands structured output
            try:
                response = agent.structured_output(
                    WeatherQueryResponse,
                    prompt=message
                )
                return response, agent.messages
                
            except ValidationError as e:
                logger.error(f"Structured output validation failed: {e}")
                # Handle Pydantic validation errors specifically
                fallback_response = WeatherQueryResponse(
                    query_type="general",
                    query_confidence=0.3,
                    locations=[ExtractedLocation(
                        name="Unknown",
                        latitude=0.0,
                        longitude=0.0,
                        timezone="UTC",
                        country_code="XX",
                        confidence=0.0,
                        needs_clarification=True
                    )],
                    summary=f"The response couldn't be properly validated. Validation error: {str(e)}",
                    warnings=["Response validation failed", "Please try rephrasing your query"],
                    processing_time_ms=0
                )
                return fallback_response, agent.messages if 'agent' in locals() else session_messages or []
            except Exception as e:
                logger.error(f"Structured output failed: {e}")
                # Fallback response for general errors
                fallback_response = WeatherQueryResponse(
                    query_type="general",
                    query_confidence=0.5,
                    locations=[ExtractedLocation(
                        name="Unknown",
                        latitude=0.0,
                        longitude=0.0,
                        timezone="UTC",
                        country_code="XX",
                        confidence=0.0,
                        needs_clarification=True
                    )],
                    summary=f"I encountered an error processing your request: {str(e)}",
                    warnings=["Structured output generation failed"],
                    processing_time_ms=0
                )
                return fallback_response, agent.messages if 'agent' in locals() else session_messages or []
    
    async def _process_structured_query(self, message: str, clients: List[tuple[str, MCPClient]], 
                                        session_messages: Optional[List[Dict[str, Any]]] = None) -> tuple[WeatherQueryResponse, List[Dict[str, Any]]]:
        """
        Process structured query asynchronously with conversation history.
        
        Args:
            message: The user's query
            clients: List of MCP client tuples
            session_messages: Previous conversation messages
            
        Returns:
            Tuple of (structured_response, updated_messages)
        """
        loop = asyncio.get_event_loop()
        response, updated_messages = await loop.run_in_executor(
            self.executor,
            self._process_structured_query_sync,
            message,
            clients,
            session_messages
        )
        return response, updated_messages
    
    def validate_response(self, response: WeatherQueryResponse) -> ValidationResult:
        """
        Validate a structured weather response.
        
        Args:
            response: The response to validate
            
        Returns:
            ValidationResult with any errors, warnings, or suggestions
        """
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
        
        # Model-specific suggestions
        if errors and "haiku" in self.model_id.lower():
            suggestions.append(
                "Consider using Claude 3.5 Sonnet for better geographic intelligence and structured output"
            )
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        session_count = len(self.sessions) if hasattr(self, 'sessions') else 0
        return {
            "model": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "mcp_servers": list(self.mcp_servers.keys()),
            "debug_logging": self.debug_logging,
            "session_management": {
                "active_sessions": session_count,
                "storage_type": "file" if self.session_storage_dir else "memory",
                "conversation_manager": "SlidingWindowConversationManager",
                "window_size": self.conversation_manager.window_size if hasattr(self.conversation_manager, 'window_size') else None
            }
        }
    


# For backward compatibility
async def create_weather_agent(debug_logging: bool = False, prompt_type: Optional[str] = None) -> MCPWeatherAgent:
    """
    Create and initialize a weather agent.
    
    Args:
        debug_logging: Whether to show detailed debug logging
        prompt_type: Type of system prompt to use (default, agriculture, simple)
        
    Returns:
        Initialized MCPWeatherAgent
    """
    agent = MCPWeatherAgent(debug_logging=debug_logging, prompt_type=prompt_type)
    
    # Test connectivity
    connectivity = await agent.test_connectivity()
    if not any(connectivity.values()):
        raise RuntimeError("No MCP servers are available")
    
    return agent