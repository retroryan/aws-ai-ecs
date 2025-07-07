#!/usr/bin/env python3
"""Test MCP server directly through the ALB to see tool format"""

import asyncio
import aiohttp
import json

async def test_forecast_tool():
    """Test the forecast tool with different argument formats"""
    
    base_url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com"
    
    # First, let's get the available tools
    print("🔍 Getting available MCP tools...")
    
    async with aiohttp.ClientSession() as session:
        # Get health status
        async with session.get(f"{base_url}/health") as response:
            health = await response.json()
            print(f"Health: {health}")
        
        # Test different query formats to observe the behavior
        test_queries = [
            {
                "desc": "City that doesn't trigger coordinates",
                "query": "Weather in Boston"
            },
            {
                "desc": "City that triggers coordinate lookup", 
                "query": "Weather in Seattle"
            },
            {
                "desc": "Direct coordinate request",
                "query": "Weather at 47.6062 latitude and -122.3321 longitude"
            }
        ]
        
        print("\n📊 Testing different query formats:")
        
        for test in test_queries:
            print(f"\n{'='*50}")
            print(f"Test: {test['desc']}")
            print(f"Query: {test['query']}")
            print('='*50)
            
            # Enable debug mode if possible
            payload = {
                "query": test["query"],
                "debug": True  # May not be supported but worth trying
            }
            
            try:
                async with session.post(f"{base_url}/query", json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    result = await response.json()
                    
                    # Check for error pattern
                    if "apologize" in result.get("response", ""):
                        print("❌ Formatting error detected")
                        # Try to extract the problematic part
                        resp = result["response"]
                        if "I'll use them for a faster response." in resp:
                            print("→ Agent tried to use coordinates for 'faster response'")
                        if "Let me try again" in resp:
                            print("→ Agent retried after initial failure")
                    else:
                        print("✅ No formatting error")
                    
                    # Look for patterns in the response
                    resp_lower = result.get("response", "").lower()
                    if "coordinates" in resp_lower:
                        print("→ Response mentions coordinates")
                    if "latitude" in resp_lower and "longitude" in resp_lower:
                        print("→ Response contains lat/lon values")
                        
            except asyncio.TimeoutError:
                print("❌ Request timed out")
            except Exception as e:
                print(f"❌ Error: {e}")

async def test_agent_info():
    """Try to get more info about the agent configuration"""
    
    base_url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com"
    
    print("\n\n🔧 Checking for debug endpoints...")
    
    async with aiohttp.ClientSession() as session:
        # Try some potential debug endpoints
        endpoints = ["/debug", "/config", "/version", "/tools", "/mcp/tools"]
        
        for endpoint in endpoints:
            try:
                async with session.get(f"{base_url}{endpoint}", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        print(f"✅ Found endpoint: {endpoint}")
                        data = await response.text()
                        print(f"   Response: {data[:100]}...")
                    else:
                        print(f"❌ {endpoint}: {response.status}")
            except:
                print(f"❌ {endpoint}: Not available")

async def main():
    print("🧪 Testing MCP Direct Integration\n")
    
    await test_forecast_tool()
    await test_agent_info()
    
    print("\n\n📋 Analysis:")
    print("The issue appears to be:")
    print("1. Agent recognizes certain cities (Seattle, Boston) and knows their coordinates")
    print("2. Agent tries to use coordinates 'for a faster response'")
    print("3. The coordinate format causes an error in the tool call")
    print("4. Agent falls back to using location name, which works")
    print("\nThis suggests the issue is in how Strands formats the tool arguments when coordinates are provided.")

if __name__ == "__main__":
    asyncio.run(main())