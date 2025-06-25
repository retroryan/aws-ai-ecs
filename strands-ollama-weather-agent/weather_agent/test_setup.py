#!/usr/bin/env python3
"""Test the weather agent setup."""

import sys
import os

print("🧪 Testing Weather Agent Setup")
print("=" * 40)

# Check Python version
print(f"✓ Python version: {sys.version.split()[0]}")

# Check current directory
print(f"✓ Current directory: {os.getcwd()}")

# Test imports
try:
    from mcp_agent import MCPWeatherAgent, create_weather_agent
    print("✓ Successfully imported mcp_agent")
except ImportError as e:
    print(f"✗ Failed to import mcp_agent: {e}")

try:
    from models.structured_responses import WeatherQueryResponse
    print("✓ Successfully imported models")
except ImportError as e:
    print(f"✗ Failed to import models: {e}")

# Check environment variables
bedrock_model = os.getenv("BEDROCK_MODEL_ID")
if bedrock_model:
    print(f"✓ BEDROCK_MODEL_ID is set: {bedrock_model}")
else:
    print("✗ BEDROCK_MODEL_ID is not set")

print("\n✅ Setup test complete!")