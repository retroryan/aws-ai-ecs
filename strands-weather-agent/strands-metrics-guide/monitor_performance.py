#!/usr/bin/env python3
"""Monitor telemetry performance impact."""

import asyncio
import time
from statistics import mean, stdev
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load .env first from parent directory
from dotenv import load_dotenv
env_path = parent_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

async def benchmark_with_telemetry(enabled=True):
    """Benchmark query performance."""
    from weather_agent.mcp_agent import create_weather_agent
    
    agent = await create_weather_agent(enable_telemetry=enabled)
    
    times = []
    queries = [
        "Weather in Chicago?",
        "Temperature in NYC?",
        "Forecast for LA?"
    ]
    
    for query in queries * 3:  # Run each 3 times
        start = time.time()
        await agent.query(query)
        elapsed = time.time() - start
        times.append(elapsed)
    
    return {
        "mean": mean(times),
        "stdev": stdev(times) if len(times) > 1 else 0,
        "min": min(times),
        "max": max(times)
    }

async def main():
    print("🔍 Telemetry Performance Impact Analysis")
    print("=" * 50)
    
    # Note: Ensure AWS credentials are configured before running
    
    # Benchmark without telemetry
    print("\n⏱️  Without telemetry...")
    without = await benchmark_with_telemetry(False)
    
    # Benchmark with telemetry
    print("\n⏱️  With telemetry...")
    with_telemetry = await benchmark_with_telemetry(True)
    
    # Compare
    print("\n📊 Results:")
    print(f"Without telemetry: {without['mean']:.3f}s ± {without['stdev']:.3f}s")
    print(f"With telemetry: {with_telemetry['mean']:.3f}s ± {with_telemetry['stdev']:.3f}s")
    
    overhead = with_telemetry['mean'] - without['mean']
    percent = (overhead / without['mean']) * 100
    print(f"\nOverhead: {overhead:.3f}s ({percent:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())