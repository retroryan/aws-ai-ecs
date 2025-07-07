#!/usr/bin/env python3
"""
Demonstrate Langfuse v3 features in the Weather Agent.

This script showcases:
1. Deterministic trace ID generation
2. Direct scoring of traces
3. Using Langfuse v3 client for advanced operations
4. Integration with Strands' OTEL-based telemetry

Usage:
    python demo_langfuse_v3.py
"""

import asyncio
import os
import sys
import time
import json
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load .env file
from dotenv import load_dotenv
env_path = parent_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"📋 Loaded environment from {env_path}")

from weather_agent.langfuse_telemetry import (
    force_flush_telemetry, get_langfuse_client, create_deterministic_trace_id
)
from weather_agent.mcp_agent import create_weather_agent


async def demo_deterministic_traces():
    """Demonstrate deterministic trace IDs for reliable scoring"""
    print("\n🔬 Demo: Deterministic Trace IDs")
    print("=" * 80)
    
    # Create a unique seed for this test
    test_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Generate deterministic trace ID
    trace_id = create_deterministic_trace_id(test_id)
    if not trace_id:
        print("❌ Langfuse v3 not available - cannot create deterministic trace IDs")
        return None
    
    print(f"✅ Generated deterministic trace ID: {trace_id}")
    print(f"   Seed: {test_id}")
    
    # Verify it's deterministic
    trace_id_2 = create_deterministic_trace_id(test_id)
    if trace_id == trace_id_2:
        print("✅ Verified: Same seed produces same trace ID")
    else:
        print("❌ Error: Trace IDs don't match!")
    
    # Create agent with this session
    agent = await create_weather_agent(
        enable_telemetry=True,
        telemetry_session_id=test_id,
        telemetry_user_id="demo-user@example.com",
        telemetry_tags=["langfuse-v3-demo", "deterministic-trace"]
    )
    
    # Run a query
    query = "What's the temperature in Chicago?"
    print(f"\n🔄 Running query: '{query}'")
    response = await agent.query(query)
    print(f"✅ Query completed")
    
    # Force flush to ensure trace is sent
    force_flush_telemetry()
    
    return trace_id, agent


async def demo_scoring(trace_id: str, agent):
    """Demonstrate Langfuse v3 scoring API"""
    print("\n🏆 Demo: Trace Scoring")
    print("=" * 80)
    
    if not trace_id:
        print("⚠️  No trace ID available - skipping scoring demo")
        return
    
    # Wait for trace to be processed
    print("⏳ Waiting for trace to be processed...")
    time.sleep(5)
    
    # Score the trace using the agent's method
    print(f"\n🎯 Scoring trace: {trace_id}")
    
    # Example scores
    scores = [
        ("accuracy", 0.95, "Response accurately reported Chicago weather"),
        ("relevance", 1.0, "Response was highly relevant to the query"),
        ("latency", 0.8, "Response time was acceptable")
    ]
    
    for name, value, comment in scores:
        success = await agent.score_trace(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
            data_type="NUMERIC"
        )
        if success:
            print(f"  ✅ {name}: {value} - {comment}")
        else:
            print(f"  ❌ Failed to score {name}")


async def demo_v3_client_operations():
    """Demonstrate direct Langfuse v3 client operations"""
    print("\n🔧 Demo: Direct Langfuse v3 Client Operations")
    print("=" * 80)
    
    client = get_langfuse_client()
    if not client:
        print("❌ Langfuse v3 client not available")
        return
    
    print("✅ Langfuse v3 client initialized")
    
    # Test auth check
    try:
        if client.auth_check():
            print("✅ Authentication successful")
        else:
            print("❌ Authentication failed")
    except Exception as e:
        print(f"⚠️  Auth check error: {e}")
    
    # Show client configuration
    print(f"\n📊 Client Configuration:")
    print(f"   Host: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    print(f"   Service: weather-agent")
    print(f"   Tracing Enabled: True (v3 parameter)")


async def demo_structured_output_with_scoring():
    """Demonstrate structured output with scoring"""
    print("\n📊 Demo: Structured Output with Scoring")
    print("=" * 80)
    
    # Create a unique test ID
    test_id = f"structured-{uuid.uuid4().hex[:8]}"
    
    # Create agent
    agent = await create_weather_agent(
        enable_telemetry=True,
        telemetry_session_id=test_id,
        telemetry_user_id="structured-demo@example.com",
        telemetry_tags=["langfuse-v3", "structured-output"]
    )
    
    # Run structured query
    query = "What's the weather forecast for Seattle for the next 3 days?"
    print(f"🔄 Running structured query: '{query}'")
    
    response = await agent.query_structured(query)
    
    print("\n📋 Structured Response:")
    print(f"   Query Type: {response.query_type}")
    print(f"   Confidence: {response.query_confidence}")
    print(f"   Locations: {len(response.locations)}")
    for loc in response.locations:
        print(f"     - {loc.name} ({loc.latitude}, {loc.longitude})")
    print(f"   Summary: {response.summary[:100]}...")
    
    # Validate and score
    validation = agent.validate_response(response)
    score = 1.0 if validation.valid else 0.5
    
    print(f"\n✅ Validation: {'PASSED' if validation.valid else 'FAILED'}")
    if validation.warnings:
        print(f"   Warnings: {validation.warnings}")
    
    # Force flush
    force_flush_telemetry()


async def main():
    """Run all Langfuse v3 demos"""
    print("\n🚀 Langfuse v3 Integration Demo")
    print("=" * 80)
    
    # Check prerequisites
    if not os.getenv('LANGFUSE_PUBLIC_KEY'):
        print("❌ LANGFUSE_PUBLIC_KEY not set in environment")
        print("   Please configure your .env file with Langfuse credentials")
        return 1
    
    try:
        # Run demos
        trace_id, agent = await demo_deterministic_traces()
        await demo_v3_client_operations()
        await demo_scoring(trace_id, agent)
        await demo_structured_output_with_scoring()
        
        print("\n✅ All Langfuse v3 demos completed successfully!")
        print("\n📊 Check your Langfuse dashboard for:")
        print("   - Traces with deterministic IDs")
        print("   - Scoring data on traces")
        print("   - Structured output validation")
        print("   - Custom tags and metadata")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))