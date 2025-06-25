#!/usr/bin/env python3
"""
Test the weather agent with Ollama using mock mode.

This script tests the Ollama integration without requiring MCP servers to be running.
"""

import asyncio
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set environment variables for Ollama
os.environ['MODEL_PROVIDER'] = 'ollama'
os.environ['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'llama3.2:1b')

from weather_agent.mcp_agent import MCPWeatherAgent


async def test_basic_query():
    """Test basic weather query with mock tools."""
    print("\n=== Testing Basic Query with Mock Tools ===")
    
    # Create agent with mock mode
    agent = MCPWeatherAgent(debug_logging=True, mock_mode=True)
    
    # Get agent info
    info = agent.get_agent_info()
    print(f"\nAgent Info:")
    print(f"  Provider: {info['provider']}")
    print(f"  Model: {info['model']}")
    print(f"  Mock Mode: {info['mock_mode']}")
    print(f"  MCP Servers: {info['mcp_servers']}")
    
    # Test connectivity (should always succeed in mock mode)
    connectivity = await agent.test_connectivity()
    print(f"\nConnectivity Test: {connectivity}")
    
    # Test queries
    queries = [
        "What's the weather in Chicago?",
        "Give me a 3-day forecast for Seattle",
        "What were the temperatures in New York last week?",
        "Are conditions good for planting corn in Iowa?"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        try:
            response = await agent.query(query)
            print(f"\nResponse:\n{response}")
        except Exception as e:
            print(f"\nError: {e}")


async def test_structured_output():
    """Test structured output with mock tools."""
    print("\n\n=== Testing Structured Output with Mock Tools ===")
    
    # Create agent with mock mode
    agent = MCPWeatherAgent(mock_mode=True)
    
    query = "What's the weather forecast for Denver, Colorado?"
    print(f"\nQuery: {query}")
    
    try:
        response = await agent.query_structured(query)
        
        print(f"\nStructured Response:")
        print(f"  Query Type: {response.query_type}")
        print(f"  Confidence: {response.query_confidence}")
        
        if response.locations:
            print(f"\n  Locations:")
            for loc in response.locations:
                print(f"    - {loc.name}: ({loc.latitude}, {loc.longitude})")
                print(f"      Confidence: {loc.confidence}")
        
        if response.weather_data:
            print(f"\n  Weather Data:")
            for data in response.weather_data:
                print(f"    - Current Temp: {data.current_temp}°C")
                if data.forecast:
                    print(f"      Forecast Days: {len(data.forecast)}")
        
        print(f"\n  Summary: {response.summary}")
        
        if response.warnings:
            print(f"\n  Warnings: {response.warnings}")
            
    except Exception as e:
        print(f"\nError in structured output: {e}")
        import traceback
        traceback.print_exc()


async def test_conversation():
    """Test multi-turn conversation with mock tools."""
    print("\n\n=== Testing Conversation with Mock Tools ===")
    
    # Create agent with mock mode
    agent = MCPWeatherAgent(mock_mode=True)
    
    # Use a consistent session ID for the conversation
    session_id = "test-session-001"
    
    conversations = [
        "What's the weather in Boston?",
        "How about tomorrow?",  # Should remember Boston context
        "Is it good for outdoor activities?"
    ]
    
    for i, message in enumerate(conversations):
        print(f"\n--- Turn {i+1} ---")
        print(f"User: {message}")
        
        try:
            response = await agent.query(message, session_id=session_id)
            print(f"Assistant: {response}")
        except Exception as e:
            print(f"Error: {e}")
    
    # Get session info
    session_info = agent.get_session_info(session_id)
    if session_info:
        print(f"\nSession Info:")
        print(f"  Total Messages: {session_info['total_messages']}")
        print(f"  Conversation Turns: {session_info['conversation_turns']}")
    
    # Clear session
    agent.clear_session(session_id)
    print(f"\nSession cleared")


async def main():
    """Run all tests."""
    start_time = datetime.now()
    
    print("🚀 Starting Ollama Mock Mode Tests")
    print(f"Provider: {os.getenv('MODEL_PROVIDER', 'bedrock')}")
    print(f"Model: {os.getenv('OLLAMA_MODEL', 'llama3.2:1b')}")
    
    # Run tests
    await test_basic_query()
    await test_structured_output()
    await test_conversation()
    
    # Calculate total time
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n\n✅ All tests completed in {elapsed:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())