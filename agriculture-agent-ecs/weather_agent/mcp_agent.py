"""
MCP Weather Agent using LangGraph with Structured Output

This module demonstrates how to use MCP servers with LangGraph:
- Uses create_react_agent for robust tool handling
- MCP servers run as independent HTTP endpoints
- Automatic tool discovery and execution
- Claude's native tool calling works through LangChain
- Implements structured output using LangGraph Option 1 approach in this document https://langchain-ai.github.io/langgraph/how-tos/react-agent-structured-output/
"""

import os
import json
from typing import Optional, Dict, Any, Union
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
import uuid
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List
import time

# Load environment variables
from pathlib import Path
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass


# Import structured output models
from .models import (
    WeatherCondition,
    DailyForecast,
    OpenMeteoResponse,
    AgricultureAssessment
)


class MCPWeatherAgent:
    """
    A weather agent that uses MCP servers with LangGraph.
    
    This demonstrates the correct approach:
    1. MCP servers run as independent HTTP endpoints
    2. Tools are discovered dynamically
    3. LangGraph's create_react_agent handles tool execution
    4. Claude's native tool calling works automatically
    """
    
    def __init__(self):
        # Get configuration from environment
        model_id = os.getenv("BEDROCK_MODEL_ID")
        region = os.getenv("BEDROCK_REGION", "us-east-1")
        temperature = float(os.getenv("BEDROCK_TEMPERATURE", "0"))
        
        # Require BEDROCK_MODEL_ID to be set
        if not model_id:
            print("❌ ERROR: BEDROCK_MODEL_ID environment variable is required")
            print("   Please set BEDROCK_MODEL_ID to one of:")
            print("   - us.anthropic.claude-3-5-sonnet-20241022-v2:0")
            print("   - us.anthropic.claude-3-haiku-20240307-v1:0")
            print("   - meta.llama3-70b-instruct-v1:0")
            print("   - cohere.command-r-plus-v1:0")
            print("\nExample: export BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0")
            import sys
            sys.exit(1)
        
        # Create LLM instance using init_chat_model with Bedrock
        self.llm = init_chat_model(
            model_id,
            model_provider="bedrock_converse",
            region_name=region,
            temperature=temperature
        )
        print(f"🚀 Using Bedrock model: {model_id} in region {region}")
        
        # Initialize properties
        self.mcp_client = None
        self.tools = []
        self.agent = None
        
        # Note: Simplified approach - no query classifier needed
        # The LLM will directly determine which tools to use
        
        # Initialize memory checkpointer for conversation state
        self.checkpointer = MemorySaver()
        
        # Initialize conversation ID (thread_id for checkpointer)
        self.conversation_id = str(uuid.uuid4())
        
        # Enhanced system message for the agent that works with pre-classified queries
        self.system_message = SystemMessage(
            content=(
                "You are a helpful weather and agricultural assistant powered by AI.\n\n"
                "IMPORTANT: When users ask about weather, ALWAYS use the available tools to get data. The tools provide:\n"
                "- Weather forecasts (current conditions and predictions up to 16 days)\n"
                "- Historical weather data (past weather patterns and trends)\n"
                "- Agricultural conditions (soil moisture, evapotranspiration, growing degree days)\n\n"
                "For every weather query:\n"
                "1. ALWAYS call the appropriate tool(s) first to get real data\n"
                "2. Use the data from tools to provide accurate, specific answers\n"
                "3. Focus on agricultural applications like planting decisions, irrigation scheduling, frost warnings, and harvest planning\n\n"
                "Tool Usage Guidelines:\n"
                "- For current/future weather → use get_weather_forecast tool\n"
                "- For past weather → use get_historical_weather tool\n"
                "- For soil/agricultural conditions → use get_agricultural_conditions tool\n"
                "- For complex queries → use multiple tools to gather comprehensive data\n\n"
                "Location context may be provided in [brackets] to help with disambiguation.\n"
                "Always prefer calling tools with this context over asking for clarification.\n\n"
                "COORDINATE HANDLING:\n"
                "- When users mention coordinates (lat/lon, latitude/longitude), ALWAYS pass them to tools\n"
                "- For faster responses, provide latitude/longitude coordinates for any location you know\n"
                "- You have extensive geographic knowledge - use it to provide coordinates for cities worldwide\n"
                "- If you're unsure of exact coordinates, let the tools handle geocoding instead"
            )
        )
        
    def initialize(self):
        """Initialize MCP connections and create the LangGraph agent."""
        # Configure MCP servers with HTTP endpoints
        # Use environment variables with fallback to local development URLs
        server_config = {
            "forecast": {
                "url": os.getenv("MCP_FORECAST_URL", "http://127.0.0.1:7071/mcp"),
                "transport": "streamable_http"
            },
            "historical": {
                "url": os.getenv("MCP_HISTORICAL_URL", "http://127.0.0.1:7072/mcp"),
                "transport": "streamable_http"
            },
            "agricultural": {
                "url": os.getenv("MCP_AGRICULTURAL_URL", "http://127.0.0.1:7073/mcp"),
                "transport": "streamable_http"
            }
        }
        
        # Create MCP client and discover tools
        self.mcp_client = MultiServerMCPClient(server_config)
        # Convert async get_tools to sync
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async_tools = loop.run_until_complete(self.mcp_client.get_tools())
        loop.close()
        
        # Wrap async tools to work synchronously
        from langchain_core.tools import Tool
        self.tools = []
        for async_tool in async_tools:
            def make_sync_func(tool):
                def sync_func(**kwargs):
                    # Create new event loop for each invocation
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(tool.ainvoke(kwargs))
                        return result
                    finally:
                        loop.close()
                return sync_func
            
            # Create a synchronous version of the tool
            # Use StructuredTool to preserve the input structure
            from langchain_core.tools import StructuredTool
            sync_tool = StructuredTool(
                name=async_tool.name,
                description=async_tool.description,
                func=make_sync_func(async_tool),
                args_schema=async_tool.args_schema
            )
            self.tools.append(sync_tool)
        
        print(f"✅ Connected to {len(server_config)} MCP servers")
        print(f"🔧 Available tools: {len(self.tools)}")
        for tool in self.tools:
            print(f"  → {tool.name}: {tool.description[:60]}...")
        
        # Create React agent with discovered tools and checkpointer
        self.agent = create_react_agent(
            self.llm.bind_tools(self.tools),
            self.tools,
            checkpointer=self.checkpointer
        )
    
    def query(self, user_query: str, thread_id: str = None) -> str:
        """
        Process a query using the LangGraph agent with conversation memory.
        
        Simplified approach:
        1. Pass query directly to LangGraph agent
        2. Agent uses Claude's native tool calling to select appropriate MCP tools
        3. Maintain conversation history via checkpointer
        4. Return natural language response
        
        Args:
            user_query: The user's question
            thread_id: Optional thread ID for conversation tracking. 
                      If not provided, uses the instance's conversation_id
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # Use provided thread_id or instance conversation_id
        thread_id = thread_id or self.conversation_id
        
        # Configure checkpointer with thread_id
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Create messages for the agent
            messages = {"messages": [HumanMessage(content=user_query)]}
            
            # Check if this is the first message in the thread
            checkpoint = self.checkpointer.get(config)
            if checkpoint is None or not checkpoint.get("channel_values", {}).get("messages"):
                # First message in thread - include system message
                messages["messages"].insert(0, self.system_message)
            
            # Run the agent with checkpointer config (sync version with timeout)
            start_time = time.time()
            timeout = 120.0
            
            # Use synchronous invoke
            result = self.agent.invoke(messages, config=config)
            
            # Check if we exceeded timeout
            if time.time() - start_time > timeout:
                raise TimeoutError("Query timed out after 120 seconds")
            
            # Log which tools were used
            tool_calls = []
            for msg in result["messages"]:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for call in msg.tool_calls:
                        tool_calls.append(call['name'])
            
            if tool_calls:
                print(f"\n🔧 Tools used: {', '.join(set(tool_calls))}")
            
            # Return the final response
            final_message = result["messages"][-1]
            return final_message.content
            
        except TimeoutError:
            raise TimeoutError("Query timed out after 120 seconds")
        except Exception as e:
            print(f"\n❌ Error during query: {e}")
            import traceback
            traceback.print_exc()
            return f"An error occurred: {str(e)}"
    
    def query_structured(
        self, 
        user_query: str, 
        response_format: str = "forecast", 
        thread_id: str = None
    ) -> Union[OpenMeteoResponse, AgricultureAssessment]:
        """
        Process a query and return structured output using LangGraph Option 1 approach.
        
        This method demonstrates structured output where:
        1. The agent calls MCP tools to get raw JSON data
        2. The response is parsed and structured into Pydantic models
        3. Returns a structured OpenMeteoResponse consolidating the data
        
        Args:
            user_query: The user's question
            response_format: "forecast" for weather data, "agriculture" for farming assessment
            thread_id: Optional thread ID for conversation tracking
            
        Returns:
            Structured Pydantic model with consolidated Open-Meteo data
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # First get the raw response from the agent
        raw_response = self.query(user_query, thread_id)
        
        # Use the thread_id to get the conversation history
        thread_id = thread_id or self.conversation_id
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = self.checkpointer.get(config)
        
        # Extract tool responses from the checkpoint
        tool_data = {}
        if checkpoint and checkpoint.get("channel_values", {}).get("messages"):
            messages = checkpoint["channel_values"]["messages"]
            
            # Find all tool response messages
            for msg in messages:
                if hasattr(msg, 'type') and msg.type == 'tool' and hasattr(msg, 'name') and hasattr(msg, 'content'):
                    # Extract JSON data from tool response
                    content_str = str(msg.content)
                    json_start = content_str.find('{')
                    if json_start != -1:
                        try:
                            # Find the matching closing brace
                            brace_count = 0
                            json_end = -1
                            for i, char in enumerate(content_str[json_start:]):
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_end = json_start + i + 1
                                        break
                            
                            if json_end > 0:
                                json_data = json.loads(content_str[json_start:json_end])
                                tool_data[msg.name] = json_data
                        except:
                            pass
        
        # Transform based on format
        if response_format == "agriculture":
            # Create agricultural assessment
            ag_data = tool_data.get("get_agricultural_conditions", {})
            
            # Extract recommendations from raw response or tool data
            recommendations = []
            if "recommendations" in ag_data:
                recommendations = ag_data["recommendations"]
            elif "crop_recommendations" in ag_data:
                recommendations = ag_data["crop_recommendations"]
            else:
                # Parse from the raw response text
                if "recommend" in raw_response.lower():
                    # Simple extraction of recommendations
                    lines = raw_response.split('\n')
                    for line in lines:
                        if "•" in line or "-" in line or line.strip().startswith(('1.', '2.', '3.')):
                            rec = line.strip().lstrip('•-123456789. ')
                            if rec and len(rec) > 10:
                                recommendations.append(rec)
            
            return AgricultureAssessment(
                location=ag_data.get("location", user_query),
                assessment_date=ag_data.get("assessment_date", datetime.now().isoformat()),
                temperature=ag_data.get("temperature"),
                soil_temperature=ag_data.get("soil_temperature_0_to_10cm"),
                soil_moisture=ag_data.get("soil_moisture_0_to_10cm"),
                precipitation=ag_data.get("precipitation"),
                evapotranspiration=ag_data.get("evapotranspiration"),
                planting_conditions=ag_data.get("conditions", "Good" if "good" in raw_response.lower() else "Variable"),
                frost_risk=ag_data.get("frost_risk", "low" if "frost" not in raw_response.lower() else "moderate"),
                growing_degree_days=ag_data.get("growing_degree_days"),
                recommendations=recommendations[:5] if recommendations else ["Monitor conditions regularly"],
                data_source="Open-Meteo Agricultural API",
                summary=raw_response
            )
        else:
            # Create weather forecast response
            forecast_data = tool_data.get("get_weather_forecast", {})
            
            # Extract location from tool data or query
            location = forecast_data.get("location", user_query)
            if isinstance(location, dict):
                location = location.get("name", user_query)
            
            # Build current conditions
            current = None
            if "current" in forecast_data:
                curr = forecast_data["current"]
                current = WeatherCondition(
                    temperature=curr.get("temperature_2m"),
                    feels_like=curr.get("apparent_temperature"),
                    humidity=curr.get("relative_humidity_2m"),
                    wind_speed=curr.get("wind_speed_10m"),
                    wind_direction=curr.get("wind_direction_10m"),
                    precipitation=curr.get("precipitation"),
                    conditions=curr.get("weather_code", "Clear")
                )
            
            # Build daily forecast
            daily_forecast = []
            if "daily" in forecast_data:
                daily = forecast_data["daily"]
                times = daily.get("time", [])
                max_temps = daily.get("temperature_2m_max", [])
                min_temps = daily.get("temperature_2m_min", [])
                precip = daily.get("precipitation_sum", [])
                
                for i in range(min(5, len(times))):  # Up to 5 days
                    daily_forecast.append(DailyForecast(
                        date=times[i] if i < len(times) else None,
                        max_temperature=max_temps[i] if i < len(max_temps) else None,
                        min_temperature=min_temps[i] if i < len(min_temps) else None,
                        precipitation=precip[i] if i < len(precip) else None,
                        conditions="Variable"
                    ))
            
            return OpenMeteoResponse(
                location=str(location),
                coordinates=forecast_data.get("coordinates"),
                timezone=forecast_data.get("timezone"),
                current_conditions=current,
                daily_forecast=daily_forecast,
                data_source="Open-Meteo Weather API",
                summary=raw_response
            )
        
        # Fallback if parsing fails
        try:
            if response_format == "agriculture":
                return AgricultureAssessment(
                    location="Unknown",
                    planting_conditions="Unable to assess",
                    summary=raw_response
                )
            else:
                return OpenMeteoResponse(
                    location="Unknown",
                    summary=raw_response
                )
        except Exception as e:
            # Final fallback
            if response_format == "agriculture":
                return AgricultureAssessment(
                    location="Unknown",
                    planting_conditions="Unable to assess",
                    summary=raw_response
                )
            else:
                return OpenMeteoResponse(
                    location="Unknown",
                    summary=raw_response
                )
    
    def clear_history(self):
        """
        Clear conversation history by generating a new conversation ID.
        
        This effectively starts a new conversation thread while keeping
        the checkpointer's previous conversations intact.
        """
        # Generate new conversation ID for a fresh thread
        self.conversation_id = str(uuid.uuid4())
        print(f"🆕 Started new conversation: {self.conversation_id}")
    
    def cleanup(self):
        """Clean up MCP connections (HTTP connections are closed automatically)."""
        # The MultiServerMCPClient handles HTTP connection cleanup
        pass


# Convenience function
def create_mcp_weather_agent():
    """Create and initialize an MCP weather agent."""
    agent = MCPWeatherAgent()
    agent.initialize()
    return agent