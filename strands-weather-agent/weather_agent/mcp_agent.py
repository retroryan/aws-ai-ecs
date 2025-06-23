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
from typing import Optional, List, Dict, Any, Type, TypeVar
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# Pydantic imports for error handling
from pydantic import ValidationError

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient
from strands.tools.structured_output import convert_pydantic_to_tool_spec

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
    
    def __init__(self, debug_logging: bool = False, prompt_type: Optional[str] = None):
        """
        Initialize the weather agent.
        
        Args:
            debug_logging: Whether to show detailed debug logging for tool calls
            prompt_type: Type of system prompt to use (default, agriculture, simple)
                        Can also be set via SYSTEM_PROMPT environment variable
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
        
        logger.info(f"Initialized MCPWeatherAgent with model: {self.model_id}")
    
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
    
    def _process_with_clients_sync(self, message: str, clients: List[tuple[str, MCPClient]]) -> str:
        """
        Process query synchronously within MCP client contexts.
        
        This is required because MCP clients must be used within their context managers.
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
            
            # Create agent within context
            agent = Agent(
                model=self.bedrock_model,
                tools=all_tools,
                system_prompt=self._get_system_prompt(),
                max_parallel_tools=2
            )
            
            # Process query
            response = agent(message)
            
            # Convert response to string if needed
            if hasattr(response, 'content'):
                return response.content
            elif hasattr(response, 'text'):
                return response.text
            else:
                return str(response)
    
    async def query(self, message: str, session_id: Optional[str] = None) -> str:
        """
        Process a query using the weather agent.
        
        Args:
            message: The user's query
            session_id: Optional session ID (not used in current implementation)
            
        Returns:
            The agent's response
        """
        logger.info(f"Processing query: {message[:50]}...")
        
        if self.debug_logging:
            print(f"\n📝 Query: {message}")
        
        # Create MCP clients
        clients = self._create_mcp_clients()
        
        if not clients:
            return "I'm unable to connect to the weather services. Please try again later."
        
        try:
            # Run synchronous processing in thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self.executor,
                self._process_with_clients_sync,
                message,
                clients
            )
            
            if self.debug_logging:
                print(f"\n✅ Response generated successfully")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    async def query_structured(self, message: str, session_id: Optional[str] = None) -> WeatherQueryResponse:
        """
        Process a query and return structured response using AWS Strands native capabilities.
        
        This method leverages the agent's ability to:
        1. Extract location information using LLM geographic knowledge
        2. Call weather tools with precise coordinates
        3. Format the response according to the WeatherQueryResponse schema
        
        Args:
            message: The user's weather query
            session_id: Optional session ID for conversation tracking
            
        Returns:
            Structured WeatherQueryResponse with locations, weather data, and metadata
        """
        logger.info(f"Processing structured query: {message[:50]}...")
        start_time = datetime.utcnow()
        
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
            # Process with structured output
            response = await self._process_structured_query(message, clients)
            
            # Calculate processing time
            end_time = datetime.utcnow()
            response.processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
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
    
    def _process_structured_query_sync(self, message: str, clients: List[tuple[str, MCPClient]]) -> WeatherQueryResponse:
        """
        Process structured query synchronously within MCP client contexts using native Strands structured output.
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
            
            # Create agent within context
            agent = Agent(
                model=self.bedrock_model,
                tools=all_tools,
                system_prompt=self._get_system_prompt(),
                max_parallel_tools=2
            )
            
            # Use native Strands structured output
            try:
                response = agent.structured_output(
                    WeatherQueryResponse,
                    prompt=message
                )
                return response
                
            except ValidationError as e:
                logger.error(f"Structured output validation failed: {e}")
                # Handle Pydantic validation errors specifically
                return WeatherQueryResponse(
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
            except Exception as e:
                logger.error(f"Structured output failed: {e}")
                # Fallback response for general errors
                return WeatherQueryResponse(
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
    
    async def _process_structured_query(self, message: str, clients: List[tuple[str, MCPClient]]) -> WeatherQueryResponse:
        """
        Process structured query asynchronously.
        """
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            self._process_structured_query_sync,
            message,
            clients
        )
        return response
    
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
        return {
            "model": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "mcp_servers": list(self.mcp_servers.keys()),
            "debug_logging": self.debug_logging
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