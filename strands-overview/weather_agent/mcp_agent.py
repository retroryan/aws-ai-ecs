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
from typing import Optional, List, Dict, Any
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor

# Strands imports
from strands import Agent
from strands.models import BedrockModel
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

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
    
    def __init__(self, structured_output: bool = False):
        """
        Initialize the weather agent.
        
        Args:
            structured_output: Whether to show detailed tool calls
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
        self.structured_output = structured_output
        
        # For async/sync bridge
        self.executor = ThreadPoolExecutor(max_workers=1)
        
        logger.info(f"Initialized MCPWeatherAgent with model: {self.model_id}")
    
    def _get_mcp_servers(self) -> Dict[str, str]:
        """Get MCP server URLs from environment or defaults."""
        return {
            "forecast": os.getenv("MCP_FORECAST_URL", "http://localhost:8081/mcp"),
            "historical": os.getenv("MCP_HISTORICAL_URL", "http://localhost:8082/mcp"),
            "agricultural": os.getenv("MCP_AGRICULTURAL_URL", "http://localhost:8083/mcp")
        }
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are a knowledgeable weather and agricultural assistant.

Your role is to provide accurate, helpful weather information using real-time data from your tools.

Guidelines:
- Always use tools to get current, accurate weather data
- Provide practical insights for daily planning, travel, and farming
- Be concise but informative
- Include relevant details like temperature, precipitation, and conditions
- For agricultural queries, consider soil moisture, frost risk, and growing conditions

Available capabilities:
- Current weather conditions for any location
- Multi-day weather forecasts
- Historical weather data and patterns
- Agricultural conditions and recommendations

Remember: Always fetch fresh data using your tools rather than making assumptions."""
    
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
            
            if self.structured_output:
                print(f"\n🔧 Available tools: {len(all_tools)}")
                for tool in all_tools[:3]:  # Show first 3 as example
                    print(f"   - {tool.get('name', 'unknown')}: {tool.get('description', '')[:60]}...")
            
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
        
        if self.structured_output:
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
            
            if self.structured_output:
                print(f"\n✅ Response generated successfully")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent configuration."""
        return {
            "model": self.model_id,
            "region": self.region,
            "temperature": self.temperature,
            "mcp_servers": list(self.mcp_servers.keys()),
            "structured_output": self.structured_output
        }


# For backward compatibility
async def create_weather_agent(structured_output: bool = False) -> MCPWeatherAgent:
    """
    Create and initialize a weather agent.
    
    Args:
        structured_output: Whether to show detailed tool calls
        
    Returns:
        Initialized MCPWeatherAgent
    """
    agent = MCPWeatherAgent(structured_output=structured_output)
    
    # Test connectivity
    connectivity = await agent.test_connectivity()
    if not any(connectivity.values()):
        raise RuntimeError("No MCP servers are available")
    
    return agent