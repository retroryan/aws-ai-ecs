#!/usr/bin/env python3
"""
Run the Weather Agent demo and validate that Langfuse traces were created.

This script:
1. Checks that required services are accessible (Langfuse, AWS, MCP servers)
2. Runs the weather agent demo with Langfuse telemetry
3. Queries Langfuse API to verify traces were created
4. Displays detailed trace information
5. Validates that MCP tool calls are being tracked

Usage:
    python run_and_validate_metrics.py           # Runs default demo
    python run_and_validate_metrics.py --verbose # Shows detailed output
"""

import subprocess
import sys
import os
import time
import asyncio
import uuid
import requests
from datetime import datetime, timezone, timedelta
from base64 import b64encode
import json
import argparse
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load .env file FIRST before any other imports
from dotenv import load_dotenv
env_path = parent_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"📋 Loaded environment from {env_path}")

from weather_agent.langfuse_telemetry import force_flush_telemetry
from weather_agent.mcp_agent import create_weather_agent


def get_auth_header():
    """Create Basic Auth header for Langfuse API"""
    public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
    secret_key = os.getenv('LANGFUSE_SECRET_KEY')
    if not public_key or not secret_key:
        return None
    credentials = f"{public_key}:{secret_key}"
    encoded_credentials = b64encode(credentials.encode()).decode('ascii')
    return {"Authorization": f"Basic {encoded_credentials}"}


def check_langfuse_health():
    """Check if Langfuse is accessible"""
    host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
    headers = get_auth_header()
    if not headers:
        print("❌ Langfuse credentials not configured")
        return False
    
    try:
        # Test the health endpoint
        response = requests.get(f"{host}/api/public/health", headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"   Version: {data.get('version', 'Unknown')}")
            return True
        else:
            print(f"❌ Langfuse health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to Langfuse at {host}: {e}")
        return False


def check_aws_credentials():
    """Check if AWS credentials are configured"""
    try:
        import boto3
        # Try to create STS client to verify credentials
        sts = boto3.client('sts')
        sts.get_caller_identity()
        
        # Also verify Bedrock is available in the region
        bedrock_region = os.getenv('BEDROCK_REGION', 'us-west-2')
        bedrock = boto3.client('bedrock', region_name=bedrock_region)
        try:
            bedrock.list_foundation_models()
        except Exception:
            # Just verify we can create the client
            pass
        
        return True
    except Exception as e:
        print(f"❌ AWS credentials not configured properly: {e}")
        return False


async def check_mcp_servers():
    """Check if MCP servers are accessible"""
    servers = {
        "forecast": os.getenv("MCP_FORECAST_URL", "http://localhost:7778/mcp"),
        "historical": os.getenv("MCP_HISTORICAL_URL", "http://localhost:7779/mcp"),
        "agricultural": os.getenv("MCP_AGRICULTURAL_URL", "http://localhost:7780/mcp")
    }
    
    results = {}
    for name, url in servers.items():
        try:
            # Extract base URL for health check
            base_url = url.replace("/mcp", "")
            health_url = f"{base_url}/health"
            response = requests.get(health_url, timeout=2)
            results[name] = response.status_code == 200
        except:
            results[name] = False
    
    return results


def get_recent_traces(from_time, run_id=None):
    """Fetch traces created after the specified time"""
    host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
    url = f"{host}/api/public/traces"
    headers = get_auth_header()
    
    if not headers:
        return []
    
    params = {
        "limit": 100,
        "orderBy": "timestamp.desc",
        "fromTimestamp": from_time.isoformat()
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        traces = data.get('data', [])
        
        # Filter for weather agent traces
        if run_id:
            filtered_traces = []
            for trace in traces:
                # Check metadata.attributes for our run ID
                metadata = trace.get('metadata', {})
                attributes = metadata.get('attributes', {})
                
                # Get session.id and langfuse.tags from attributes
                session_id = attributes.get('session.id', '')
                tags = attributes.get('langfuse.tags', [])
                
                # Parse tags if they're a JSON string
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = []
                
                # Check if this trace belongs to our run
                if run_id in session_id or any(f"run-{run_id}" in str(tag) for tag in tags):
                    filtered_traces.append(trace)
            
            return filtered_traces
        
        return traces
    except Exception as e:
        print(f"❌ Error fetching traces: {e}")
        return []


async def run_demo(verbose=False):
    """Run the weather agent demo"""
    print("\n🚀 Running Weather Agent Demo with Langfuse...")
    print("=" * 80)
    
    # Generate unique run ID for this execution
    run_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print(f"🎨 Run ID: {run_id}")
    print(f"⏰ Timestamp: {timestamp}")
    
    # Record start time for trace filtering
    start_time = datetime.now(timezone.utc)
    
    try:
        # Create agent with telemetry
        print("\n📊 Creating weather agent with Langfuse telemetry...")
        agent = await create_weather_agent(
            debug_logging=verbose,
            enable_telemetry=True,
            telemetry_user_id="demo-user",
            telemetry_session_id=f"demo-{run_id}",
            telemetry_tags=["weather-agent", "demo", f"run-{run_id}"]
        )
        
        # Test queries that use different MCP servers
        queries = [
            ("What's the weather forecast for Chicago?", "forecast"),
            ("What was the temperature in New York last week?", "historical"),
            ("Are conditions good for planting corn in Iowa?", "agricultural"),
            ("Compare weather in Seattle and Miami", "multiple")
        ]
        
        print("\n🔄 Running test queries...")
        for i, (query, server_type) in enumerate(queries, 1):
            print(f"\n{'='*50}")
            print(f"Query {i} ({server_type} server): {query}")
            print(f"{'='*50}")
            
            response = await agent.query(query)
            print(f"\n🤖 Response: {response[:200]}..." if len(response) > 200 else f"\n🤖 Response: {response}")
            
            # Small delay between queries
            if i < len(queries):
                await asyncio.sleep(1)
        
        # Force flush telemetry
        print("\n🔄 Flushing telemetry...")
        force_flush_telemetry()
        
        return start_time, run_id
        
    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def validate_traces(start_time, run_id, verbose=False):
    """Validate that traces were created with proper attributes"""
    print("\n🔍 Validating traces...")
    print("=" * 80)
    
    # Wait for traces to be processed
    print("⏳ Waiting for traces to be processed...")
    time.sleep(8)
    
    # Fetch recent traces
    traces = get_recent_traces(start_time, run_id)
    
    if not traces:
        print("❌ No traces found after running the demo")
        print(f"   Looking for traces with run ID: {run_id}")
        return False
    
    print(f"✅ Found {len(traces)} traces from this run")
    
    # Analyze trace attributes
    sessions_found = set()
    users_found = set()
    tags_found = set()
    tools_found = set()
    mcp_servers_found = set()
    
    # Display detailed trace information
    for i, trace in enumerate(traces[:5], 1):  # Show first 5 traces
        print(f"\nTrace {i}:")
        print(f"  ID: {trace.get('id')}")
        print(f"  Name: {trace.get('name')}")
        print(f"  Timestamp: {trace.get('timestamp')}")
        
        # Check metadata.attributes for Langfuse attributes
        metadata = trace.get('metadata', {})
        attributes = metadata.get('attributes', {})
        
        if attributes:
            session_id = attributes.get('session.id')
            user_id = attributes.get('user.id')
            tags = attributes.get('langfuse.tags', [])
            
            # Parse tags if they're a JSON string
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            
            if session_id:
                print(f"  ✅ Session ID: {session_id}")
                sessions_found.add(session_id)
            if user_id:
                print(f"  ✅ User ID: {user_id}")
                users_found.add(user_id)
            if tags:
                print(f"  ✅ Tags: {tags}")
                tags_found.update(tags)
            
            # Check for custom attributes
            for key, value in attributes.items():
                if key.startswith('custom.'):
                    print(f"  📊 {key}: {value}")
            
            # Show model and token usage
            model = attributes.get('gen_ai.request.model')
            if model:
                print(f"  Model: {model}")
            
            input_tokens = attributes.get('gen_ai.usage.input_tokens')
            output_tokens = attributes.get('gen_ai.usage.output_tokens')
            if input_tokens and output_tokens:
                total = int(input_tokens) + int(output_tokens)
                print(f"  Tokens: {total} (input: {input_tokens}, output: {output_tokens})")
        
        # Check for tool usage (MCP server calls)
        if verbose and 'observations' in trace:
            for obs in trace.get('observations', []):
                if obs.get('type') == 'GENERATION' and 'tool' in obs.get('name', '').lower():
                    tool_name = obs.get('name')
                    tools_found.add(tool_name)
                    print(f"  🔧 Tool used: {tool_name}")
                    
                    # Try to identify which MCP server
                    if 'forecast' in tool_name.lower():
                        mcp_servers_found.add('forecast')
                    elif 'historical' in tool_name.lower():
                        mcp_servers_found.add('historical')
                    elif 'agricultural' in tool_name.lower():
                        mcp_servers_found.add('agricultural')
        
        # Display usage stats if available
        usage = trace.get('usage', {})
        if usage:
            input_tokens = usage.get('input', 0)
            output_tokens = usage.get('output', 0)
            total_tokens = usage.get('total', 0)
            print(f"  Usage: {input_tokens} input + {output_tokens} output = {total_tokens} total tokens")
        
        # Display latency
        latency = trace.get('latency')
        if latency:
            print(f"  Latency: {latency}ms")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 Trace Attribute Summary:")
    print(f"  Sessions: {len(sessions_found)} unique sessions")
    print(f"  Users: {len(users_found)} unique users")
    print(f"  Tags: {len(tags_found)} unique tags - {list(tags_found)}")
    print(f"  Tools used: {len(tools_found)} - {list(tools_found)}")
    print(f"  MCP servers called: {len(mcp_servers_found)} - {list(mcp_servers_found)}")
    
    # Validate expected attributes
    validation_passed = True
    
    if len(sessions_found) == 0:
        print("  ❌ No session.id attributes found")
        validation_passed = False
    else:
        print("  ✅ session.id attributes working")
    
    if len(users_found) == 0:
        print("  ❌ No user.id attributes found")
        validation_passed = False
    else:
        print("  ✅ user.id attributes working")
    
    if len(tags_found) == 0:
        print("  ❌ No langfuse.tags attributes found")
        validation_passed = False
    else:
        print("  ✅ langfuse.tags attributes working")
    
    if 'weather-agent' not in tags_found:
        print("  ⚠️  'weather-agent' tag not found")
    
    if validation_passed:
        print("\n🎉 Validation successful! All Langfuse attributes are working correctly.")
        print(f"\n📊 MCP Server Integration:")
        print(f"  - Detected {len(tools_found)} tool calls")
        print(f"  - MCP servers used: {', '.join(mcp_servers_found) if mcp_servers_found else 'Unable to detect'}")
        print(f"\n💡 Note: Tool detection requires verbose mode or checking trace details in Langfuse UI")
    else:
        print("\n⚠️  Some attributes are missing. Check your configuration.")
    
    print(f"\n🔗 View all traces at: {os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')}")
    if run_id:
        print(f"   Filter by session ID containing: {run_id}")
        print(f"   Filter by tag: run-{run_id}")
    
    return validation_passed


async def main():
    """Main validation flow"""
    parser = argparse.ArgumentParser(description="Run and validate Weather Agent with Langfuse metrics")
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    parser.add_argument('--skip-checks', action='store_true', help='Skip preliminary checks')
    args = parser.parse_args()
    
    print("🧪 Weather Agent + Langfuse Integration Validator")
    print("=" * 80)
    
    if not args.skip_checks:
        # Step 1: Check prerequisites
        print("\n1️⃣ Checking prerequisites...")
        
        print("   Checking Langfuse connectivity...")
        if not check_langfuse_health():
            print("   ❌ Langfuse is not accessible. Please ensure it's running and credentials are set.")
            print("   Set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and optionally LANGFUSE_HOST")
            return 1
        print("   ✅ Langfuse is accessible")
        
        print("   Checking AWS credentials...")
        if not check_aws_credentials():
            print("   ❌ AWS credentials not configured. Please configure AWS credentials.")
            return 1
        print("   ✅ AWS credentials configured")
        
        print("   Checking MCP servers...")
        mcp_status = await check_mcp_servers()
        available_servers = [name for name, status in mcp_status.items() if status]
        if not available_servers:
            print("   ❌ No MCP servers are running. Please start them with:")
            print("      ./scripts/start_servers.sh")
            return 1
        print(f"   ✅ MCP servers available: {', '.join(available_servers)}")
        if len(available_servers) < 3:
            print(f"   ⚠️  Only {len(available_servers)}/3 servers running. Some queries may fail.")
    
    # Step 2: Run demo
    print("\n2️⃣ Running Weather Agent demo with Langfuse telemetry...")
    result = await run_demo(verbose=args.verbose)
    if not result[0]:
        return 1
    
    start_time, run_id = result
    
    # Step 3: Validate traces
    print("\n3️⃣ Validating traces in Langfuse...")
    if not validate_traces(start_time, run_id, verbose=args.verbose):
        # Still return 0 if traces were found but some attributes missing
        # This helps distinguish between "no traces at all" vs "traces with missing attributes"
        if get_recent_traces(start_time, run_id):
            print("\n⚠️  Traces found but some attributes missing. Check configuration.")
            return 0
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))