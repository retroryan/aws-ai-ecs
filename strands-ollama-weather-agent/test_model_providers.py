#!/usr/bin/env python3
"""
Test Model Providers

This script tests both Bedrock and Ollama model providers for the weather agent.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from weather_agent.model_providers import (
    create_model_provider, 
    test_provider_connectivity,
    BedrockProvider,
    OllamaProvider
)
from weather_agent.mcp_agent import MCPWeatherAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_bedrock_provider():
    """Test AWS Bedrock provider."""
    print("\n=== Testing AWS Bedrock Provider ===")
    
    # Save current env
    original_provider = os.environ.get("MODEL_PROVIDER")
    
    try:
        # Set to Bedrock
        os.environ["MODEL_PROVIDER"] = "bedrock"
        
        # Create provider
        provider = create_model_provider()
        assert isinstance(provider, BedrockProvider), "Expected BedrockProvider instance"
        
        # Get info
        info = provider.get_info()
        print(f"Provider: {info['provider']}")
        print(f"Model: {info['model_id']}")
        print(f"Region: {info.get('region', 'N/A')}")
        print(f"Temperature: {info.get('temperature', 'N/A')}")
        
        # Test connectivity
        connected = test_provider_connectivity(provider)
        print(f"Connectivity: {'✅ Connected' if connected else '❌ Not connected'}")
        
        # Create model
        model = provider.create_model()
        print(f"Model type: {type(model).__name__}")
        
        return connected
        
    finally:
        # Restore env
        if original_provider:
            os.environ["MODEL_PROVIDER"] = original_provider
        else:
            os.environ.pop("MODEL_PROVIDER", None)


def test_ollama_provider():
    """Test Ollama provider."""
    print("\n=== Testing Ollama Provider ===")
    
    # Save current env
    original_provider = os.environ.get("MODEL_PROVIDER")
    
    try:
        # Set to Ollama
        os.environ["MODEL_PROVIDER"] = "ollama"
        os.environ["OLLAMA_MODEL"] = "llama3.2:1b"  # Use specific model we know exists
        
        # Create provider
        provider = create_model_provider()
        assert isinstance(provider, OllamaProvider), "Expected OllamaProvider instance"
        
        # Get info
        info = provider.get_info()
        print(f"Provider: {info['provider']}")
        print(f"Model: {info['model_id']}")
        print(f"Host: {info.get('host', 'N/A')}")
        print(f"Temperature: {info.get('temperature', 'N/A')}")
        
        # Test connectivity
        connected = test_provider_connectivity(provider)
        print(f"Connectivity: {'✅ Connected' if connected else '❌ Not connected'}")
        
        # Create model
        model = provider.create_model()
        print(f"Model type: {type(model).__name__}")
        
        return connected
        
    finally:
        # Restore env
        if original_provider:
            os.environ["MODEL_PROVIDER"] = original_provider
        else:
            os.environ.pop("MODEL_PROVIDER", None)


async def test_weather_agent_with_provider(provider_type: str):
    """Test weather agent with specific provider."""
    print(f"\n=== Testing Weather Agent with {provider_type.upper()} ===")
    
    # Save current env
    original_provider = os.environ.get("MODEL_PROVIDER")
    
    try:
        # Set provider
        os.environ["MODEL_PROVIDER"] = provider_type
        if provider_type == "ollama":
            os.environ["OLLAMA_MODEL"] = "llama3.2:1b"
        
        # Create agent
        agent = MCPWeatherAgent(debug_logging=True)
        
        # Get agent info
        info = agent.get_agent_info()
        print(f"Agent provider: {info.get('provider', 'unknown')}")
        print(f"Agent model: {info.get('model', 'unknown')}")
        
        # Test connectivity to MCP servers
        print("\nTesting MCP server connectivity...")
        connectivity = await agent.test_connectivity()
        for server, connected in connectivity.items():
            print(f"  {server}: {'✅' if connected else '❌'}")
        
        if any(connectivity.values()):
            # Test a simple query
            print(f"\nTesting query with {provider_type}...")
            response = await agent.query("What's the weather like in Chicago?")
            print(f"Response length: {len(response)} characters")
            print(f"Response preview: {response[:200]}...")
            return True
        else:
            print("⚠️  No MCP servers available, skipping query test")
            return False
            
    except Exception as e:
        print(f"❌ Error testing agent with {provider_type}: {e}")
        return False
        
    finally:
        # Restore env
        if original_provider:
            os.environ["MODEL_PROVIDER"] = original_provider
        else:
            os.environ.pop("MODEL_PROVIDER", None)


async def compare_providers():
    """Compare responses from both providers."""
    print("\n=== Comparing Provider Responses ===")
    
    test_query = "What's the current temperature in Seattle?"
    responses = {}
    
    for provider_type in ["bedrock", "ollama"]:
        # Check if provider is available
        os.environ["MODEL_PROVIDER"] = provider_type
        if provider_type == "ollama":
            os.environ["OLLAMA_MODEL"] = "llama3.2:1b"
        
        provider = create_model_provider()
        if not test_provider_connectivity(provider):
            print(f"⚠️  {provider_type} not available, skipping comparison")
            continue
        
        try:
            agent = MCPWeatherAgent()
            connectivity = await agent.test_connectivity()
            
            if any(connectivity.values()):
                print(f"\nQuerying {provider_type}: {test_query}")
                response = await agent.query(test_query)
                responses[provider_type] = response
                print(f"{provider_type} response length: {len(response)}")
            else:
                print(f"⚠️  No MCP servers for {provider_type}")
                
        except Exception as e:
            print(f"❌ Error with {provider_type}: {e}")
    
    # Show responses
    if len(responses) == 2:
        print("\n📊 Response Comparison:")
        for provider, response in responses.items():
            print(f"\n{provider.upper()}:")
            print(f"{response[:300]}...")


async def main():
    """Run all tests."""
    print("🧪 Model Provider Test Suite")
    print("=" * 50)
    
    # Test individual providers
    bedrock_ok = test_bedrock_provider()
    ollama_ok = test_ollama_provider()
    
    # Test with weather agent
    if bedrock_ok:
        await test_weather_agent_with_provider("bedrock")
    else:
        print("\n⚠️  Skipping Bedrock agent test (not connected)")
    
    if ollama_ok:
        await test_weather_agent_with_provider("ollama")
    else:
        print("\n⚠️  Skipping Ollama agent test (not connected)")
    
    # Compare providers if both available
    if bedrock_ok and ollama_ok:
        await compare_providers()
    
    print("\n✅ Test suite completed!")
    print(f"   Bedrock: {'✅' if bedrock_ok else '❌'}")
    print(f"   Ollama: {'✅' if ollama_ok else '❌'}")


if __name__ == "__main__":
    asyncio.run(main())