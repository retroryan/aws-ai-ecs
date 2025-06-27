#!/usr/bin/env python3
"""
Simple demonstration of the correct way to use Strands structured output.

This module can be run directly to test structured output functionality:
    python -m weather_agent.structured_output_demo
"""

import asyncio
import os
from typing import Optional
from pydantic import BaseModel, Field

# Set up environment
os.environ.setdefault("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
os.environ.setdefault("BEDROCK_REGION", "us-west-2")


class WeatherInfo(BaseModel):
    """Simple weather information model for testing."""
    location: str = Field(description="The location name")
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    conditions: Optional[str] = Field(None, description="Weather conditions")
    summary: str = Field(description="Brief weather summary")


async def test_strands_structured_output():
    """Test Strands SDK structured output directly."""
    from strands import Agent
    from strands.models import BedrockModel
    
    print("=== Testing Strands Structured Output ===\n")
    
    # Create a simple agent
    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-west-2"
    )
    
    agent = Agent(
        model=model,
        system_prompt="You are a helpful weather assistant.",
        tools=[],  # No tools needed for this test
        load_tools_from_directory=False
    )
    
    # Test the structured output method
    query = "The weather in Seattle is rainy with a temperature of 15 degrees Celsius"
    print(f"Query: {query}")
    
    try:
        # The correct way to use structured_output in Strands
        # Note: This is a synchronous method
        result = agent.structured_output(WeatherInfo, query)
        
        print(f"\nStructured Output Result:")
        print(f"  Location: {result.location}")
        print(f"  Temperature: {result.temperature}°C")
        print(f"  Conditions: {result.conditions}")
        print(f"  Summary: {result.summary}")
        
        print("\n✅ Structured output working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_async_wrapper():
    """Test async wrapper for structured output."""
    from strands import Agent
    from strands.models import BedrockModel
    import asyncio
    
    print("\n\n=== Testing Async Wrapper Pattern ===\n")
    
    # Create agent
    model = BedrockModel(
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name="us-west-2"
    )
    
    agent = Agent(
        model=model,
        system_prompt="You are a helpful weather assistant.",
        tools=[],
        load_tools_from_directory=False
    )
    
    # Async wrapper function
    async def async_structured_output(agent, model_class, prompt):
        """Run synchronous structured_output in async context."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            agent.structured_output,
            model_class,
            prompt
        )
    
    query = "Chicago has sunny weather today with 22 degrees"
    print(f"Query: {query}")
    
    try:
        # Use the async wrapper
        result = await async_structured_output(agent, WeatherInfo, query)
        
        print(f"\nAsync Wrapper Result:")
        print(f"  Location: {result.location}")
        print(f"  Temperature: {result.temperature}°C")
        print(f"  Conditions: {result.conditions}")
        print(f"  Summary: {result.summary}")
        
        print("\n✅ Async wrapper pattern working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_weather_agent_integration():
    """Test the weather agent's structured output."""
    try:
        from .mcp_agent import MCPWeatherAgent
    except ImportError:
        from mcp_agent import MCPWeatherAgent
    
    print("\n\n=== Testing Weather Agent Integration ===\n")
    
    # Create weather agent
    agent = MCPWeatherAgent(debug_logging=False)
    
    # Check if MCP servers are running
    connectivity = await agent.test_connectivity()
    print(f"MCP Server Status: {connectivity}")
    
    if not any(connectivity.values()):
        print("\n⚠️  MCP servers not running. Skipping integration test.")
        print("   To run servers: ./scripts/start_servers.sh")
        return
    
    # Test structured query
    query = "What's the current weather in London?"
    print(f"\nQuery: {query}")
    
    try:
        response = await agent.query_structured(query)
        
        print(f"\nWeather Agent Result:")
        print(f"  Query Type: {response.query_type}")
        print(f"  Confidence: {response.query_confidence}")
        
        location = response.get_primary_location()
        print(f"  Location: {location.name}")
        print(f"  Coordinates: ({location.latitude}, {location.longitude})")
        
        print(f"\n  Summary: {response.summary[:150]}...")
        
        print("\n✅ Weather agent structured output working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("Strands Structured Output Demo")
    print("=" * 50)
    
    # Test basic structured output
    await test_strands_structured_output()
    
    # Test async wrapper pattern
    await test_async_wrapper()
    
    # Test weather agent integration
    await test_weather_agent_integration()
    
    print("\n" + "=" * 50)
    print("Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())