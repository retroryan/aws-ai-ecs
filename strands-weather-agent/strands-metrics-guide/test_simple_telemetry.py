#!/usr/bin/env python3
"""
Simple test to verify Langfuse telemetry is working with the Weather Agent.
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load .env file FIRST from parent directory
from dotenv import load_dotenv
env_path = parent_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"📋 Loaded environment from {env_path}")

# Import after env vars are set
from weather_agent.mcp_agent import create_weather_agent

async def test_simple_query():
    """Run a simple query with telemetry."""
    print("\n🧪 Simple Langfuse Telemetry Test")
    print("=" * 50)
    
    # Create unique identifiers
    session_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    try:
        # Create agent with telemetry
        print("\n📊 Creating agent with Langfuse telemetry...")
        print(f"   Langfuse Host: {os.getenv('LANGFUSE_HOST')}")
        print(f"   Session ID: {session_id}")
        
        agent = await create_weather_agent(
            enable_telemetry=True,
            telemetry_user_id="test-user",
            telemetry_session_id=session_id,
            telemetry_tags=["test", "simple", "weather-agent"]
        )
        
        # Run a simple query
        query = "What's the current weather in Boston?"
        print(f"\n💭 Query: {query}")
        print("🔄 Processing...")
        
        response = await agent.query(query)
        
        print(f"\n🤖 Response: {response[:200]}..." if len(response) > 200 else f"\n🤖 Response: {response}")
        
        print(f"\n✅ Test completed successfully!")
        print(f"\n🔗 View trace at: {os.getenv('LANGFUSE_HOST')}/projects/current")
        print(f"   Session ID: {session_id}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Note: Ensure AWS credentials are configured before running
    # You can use: export $(aws configure export-credentials --format env-no-export)
    
    asyncio.run(test_simple_query())