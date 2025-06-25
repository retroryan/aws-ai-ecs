#!/usr/bin/env python3
"""
Simple test to verify Ollama integration works without MCP servers.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from weather_agent.model_providers import create_model_provider, test_provider_connectivity
from strands import Agent


async def test_ollama_basic():
    """Test basic Ollama functionality with a simple agent."""
    print("=== Testing Ollama Integration ===\n")
    
    # Set to use Ollama
    os.environ["MODEL_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = "llama3.2:1b"
    
    # Create provider
    provider = create_model_provider()
    print(f"Provider: {provider.get_info()['provider']}")
    print(f"Model: {provider.get_info()['model_id']}")
    
    # Test connectivity
    if not test_provider_connectivity(provider):
        print("❌ Ollama not available")
        return False
    
    print("✅ Ollama is connected\n")
    
    # Create a simple agent without MCP
    model = provider.create_model()
    agent = Agent(
        model=model,
        system_prompt="You are a helpful weather assistant. When asked about weather, provide a brief, informative response.",
        tools=[]  # No tools, just LLM
    )
    
    # Test queries
    test_queries = [
        "What kind of weather data would a weather agent need?",
        "Explain the difference between forecast and historical weather data.",
        "What are MCP servers in the context of weather agents?"
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        response = agent(query)
        
        # Extract text from response
        if hasattr(response, 'content'):
            text = response.content
        elif hasattr(response, 'text'):
            text = response.text
        else:
            text = str(response)
        
        print(f"Response: {text[:200]}...\n")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_ollama_basic())
    
    if success:
        print("✅ Ollama integration test passed!")
        print("\nNext steps:")
        print("1. Start MCP servers: ./scripts/start_servers.sh")
        print("2. Run full agent: MODEL_PROVIDER=ollama python main.py")
    else:
        print("❌ Ollama integration test failed")