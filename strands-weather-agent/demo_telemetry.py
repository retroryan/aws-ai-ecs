#!/usr/bin/env python3
"""
Demo: How to use AWS Strands with Langfuse observability

This script demonstrates the clean, simple way to integrate Strands with Langfuse.
Telemetry is automatic if environment variables are set!

Usage:
    1. Set Langfuse credentials in .env:
       LANGFUSE_PUBLIC_KEY=pk-lf-...
       LANGFUSE_SECRET_KEY=sk-lf-...
       LANGFUSE_HOST=https://us.cloud.langfuse.com
    
    2. Run this script:
       python demo_telemetry.py
    
    3. Check Langfuse dashboard for traces
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from weather_agent.mcp_agent import MCPWeatherAgent


async def main():
    """Demonstrate simple telemetry usage"""
    print("🌟 AWS Strands + Langfuse Telemetry Demo")
    print("=" * 50)
    
    # Create agent - telemetry is automatic!
    print("📡 Creating weather agent...")
    agent = MCPWeatherAgent(debug_logging=True)
    
    # Check if telemetry is enabled
    agent_info = agent.get_agent_info()
    telemetry_status = agent_info.get("telemetry", {})
    
    if telemetry_status.get("enabled"):
        print("✅ Telemetry enabled - traces will appear in Langfuse")
        print(f"🔗 Dashboard: {os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')}")
    else:
        print("📊 Telemetry disabled - set Langfuse credentials to enable")
    
    print("\n🌤️  Making weather queries...")
    
    # Make a few queries to generate traces
    queries = [
        "What's the weather like in Seattle?",
        "Give me a 3-day forecast for New York",
        "Is it good weather for planting tomatoes in California?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n🔄 Query {i}: {query}")
        try:
            response = await agent.query(query)
            print(f"✅ Response: {response[:100]}...")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n🎯 Demo complete!")
    if telemetry_status.get("enabled"):
        print("📊 Check your Langfuse dashboard for traces with these tags:")
        print("   - weather-agent")
        print("   - mcp") 
        print("   - strands-demo")
    
    print("\n💡 Key points:")
    print("   • Telemetry setup happens automatically at import time")
    print("   • No complex configuration needed")
    print("   • Works perfectly with or without Langfuse")
    print("   • Uses native Strands OTEL integration")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        sys.exit(1)