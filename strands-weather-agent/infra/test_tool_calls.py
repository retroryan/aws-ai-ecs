#!/usr/bin/env python3
"""Test raw tool calls to MCP servers to isolate the issue"""

import asyncio
import aiohttp
import json

async def test_mcp_server_directly():
    """Test calling MCP server directly to see format"""
    
    # First, let's list available tools
    url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com/mcp/status"
    
    async with aiohttp.ClientSession() as session:
        # Test MCP status
        print("🔍 Testing MCP status endpoint...")
        async with session.get(url) as response:
            data = await response.json()
            print(f"MCP Status: {json.dumps(data, indent=2)}")
        
        # Now let's test calling the forecast server through the main service
        print("\n📡 Testing weather query that should use coordinates...")
        query_url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com/query"
        
        # Simple location-based query
        payload = {
            "query": "Weather forecast for New York City"
        }
        
        async with session.post(query_url, json=payload) as response:
            result = await response.json()
            print(f"\nLocation-based query status: {response.status}")
            if "apologize" in result.get("response", ""):
                print("⚠️ Formatting error detected in location-based query")
            else:
                print("✅ Location-based query succeeded")

async def test_direct_mcp_call():
    """Test calling MCP servers directly via their internal URLs"""
    
    # These are the internal service discovery URLs
    forecast_url = "http://forecast.strands-weather.local:7778/mcp/"
    
    print("\n🔧 Testing direct MCP server call (this will fail from outside AWS)...")
    print("Note: This is expected to fail as we're outside the VPC")
    
    # Example of what the agent might be sending
    tool_call = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_forecast",
            "arguments": {
                "location": "Seattle",
                "latitude": 47.6062,
                "longitude": -122.3321,
                "days": 3
            }
        },
        "id": 1
    }
    
    print(f"\nTool call format: {json.dumps(tool_call, indent=2)}")

async def check_logs_for_tool_calls():
    """Guide to check CloudWatch logs for actual tool calls"""
    
    print("\n📋 To diagnose the issue, check CloudWatch logs with:")
    print("aws logs filter-log-events \\")
    print("  --log-group-name /ecs/strands-weather-agent-main \\")
    print("  --start-time $(echo $(($(date +%s) - 600)))000 \\")
    print("  --filter-pattern '\"tool_name\\\":\\\"get_forecast\\\"' \\") 
    print("  --region us-east-1")
    
    print("\nLook for the actual tool call arguments being sent")

async def main():
    print("🧪 Testing MCP Tool Call Formats\n")
    
    await test_mcp_server_directly()
    await test_direct_mcp_call()
    await check_logs_for_tool_calls()

if __name__ == "__main__":
    asyncio.run(main())