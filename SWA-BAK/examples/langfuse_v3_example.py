#!/usr/bin/env python3
"""
Simple example of using Langfuse v3 features with the Weather Agent.

This example demonstrates:
1. Creating an agent with telemetry enabled
2. Running a query that generates traces
3. Scoring the trace for evaluation
"""

import asyncio
import os
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from weather_agent.mcp_agent import create_weather_agent
from weather_agent.langfuse_telemetry import force_flush_telemetry


async def main():
    """Run a simple weather query with Langfuse v3 features"""
    
    # Create agent with telemetry enabled
    agent = await create_weather_agent(
        enable_telemetry=True,
        telemetry_user_id="example-user@demo.com",
        telemetry_session_id="example-session-123",
        telemetry_tags=["example", "langfuse-v3"]
    )
    
    # Run a query
    print("🌤️  Querying weather...")
    response = await agent.query("What's the weather like in San Francisco?")
    print(f"\n📝 Response: {response}\n")
    
    # Force flush to ensure traces are sent
    force_flush_telemetry()
    
    # Get agent info showing v3 integration
    info = agent.get_agent_info()
    print("📊 Agent Info:")
    print(f"   Model: {info['model']}")
    print(f"   Telemetry: {info['telemetry']}")
    
    # Note: In a real application, you would:
    # 1. Wait for the trace to be processed
    # 2. Get the trace ID from Langfuse
    # 3. Score the trace using agent.score_trace(trace_id, ...)
    
    print("\n✅ Example completed! Check your Langfuse dashboard for traces.")


if __name__ == "__main__":
    asyncio.run(main())