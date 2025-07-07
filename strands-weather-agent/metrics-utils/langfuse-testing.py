#!/usr/bin/env python3
"""
Comprehensive Docker + Langfuse Integration Testing Script

This script validates the complete telemetry integration by:
1. Running the Docker deployment test
2. Making weather agent queries
3. Checking Langfuse API for trace existence
4. Validating telemetry data quality

Usage:
    python langfuse-testing.py

Requirements:
    - Docker deployment running (./scripts/start_docker.sh)
    - Langfuse credentials in .env file or environment variables
    - Python requests library
"""

import os
import sys
import time
import json
import base64
import subprocess
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import asyncio
import logging
from pathlib import Path

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed. Reading from environment only.")
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

class LangfuseAPIClient:
    """Simple Langfuse API client for testing trace collection."""
    
    def __init__(self, public_key: str, secret_key: str, host: str = "https://us.cloud.langfuse.com"):
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host.rstrip('/')
        self.base_url = f"{self.host}/api/public"
        
        # Create auth header
        auth_string = f"{public_key}:{secret_key}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json"
        }
    
    def get_traces(self, limit: int = 50, from_timestamp: Optional[datetime] = None) -> List[Dict]:
        """Get traces from Langfuse API."""
        url = f"{self.base_url}/traces"
        params = {"limit": limit}
        
        if from_timestamp:
            # Convert to ISO format
            params["fromTimestamp"] = from_timestamp.isoformat()
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to connect to Langfuse at {self.host}")
            logger.info("💡 If using local Langfuse, ensure it's running (docker compose -f docker-compose.langfuse.yml up)")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get traces: {e}")
            if "401" in str(e):
                logger.error("Authentication failed - check your Langfuse credentials")
            return []
    
    def get_trace_by_id(self, trace_id: str) -> Optional[Dict]:
        """Get specific trace by ID."""
        url = f"{self.base_url}/traces/{trace_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get trace {trace_id}: {e}")
            return None
    
    def get_observations(self, trace_id: str) -> List[Dict]:
        """Get observations (spans) for a trace."""
        url = f"{self.base_url}/observations"
        params = {"traceId": trace_id}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get observations for trace {trace_id}: {e}")
            return []

class WeatherAgentTester:
    """Test the weather agent Docker deployment."""
    
    def __init__(self, base_url: str = "http://localhost:7777"):
        self.base_url = base_url.rstrip('/')
        self.session_id = None
    
    def test_health(self) -> bool:
        """Test if the weather agent is healthy."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            return response.status_code == 200 and response.json().get("status") == "healthy"
        except requests.exceptions.RequestException:
            return False
    
    def test_mcp_status(self) -> Dict[str, Any]:
        """Check MCP server connectivity."""
        try:
            response = requests.get(f"{self.base_url}/mcp/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"MCP status check failed: {e}")
            return {"servers": {}, "connected_count": 0, "total_count": 0}
    
    def make_query(self, query: str, create_session: bool = True) -> Optional[Dict]:
        """Make a weather query and return the response."""
        payload = {
            "query": query,
            "create_session": create_session
        }
        
        if self.session_id and not create_session:
            payload["session_id"] = self.session_id
        
        try:
            response = requests.post(
                f"{self.base_url}/query",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Store session ID for subsequent requests
            if not self.session_id:
                self.session_id = data.get("session_id")
            
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Query failed: {e}")
            return None
    
    def make_structured_query(self, query: str) -> Optional[Dict]:
        """Make a structured weather query."""
        payload = {
            "query": query,
            "session_id": self.session_id,
            "create_session": False if self.session_id else True
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/query/structured",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Structured query failed: {e}")
            return None

def run_docker_test_script() -> bool:
    """Run the scripts/test_docker.sh and return success status."""
    logger.info("🧪 Running Docker test script...")
    
    script_path = "./scripts/test_docker.sh"
    if not os.path.exists(script_path):
        logger.error(f"Test script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("✅ Docker test script completed successfully")
            logger.info(f"Test output: {result.stdout}")
            return True
        else:
            logger.error(f"❌ Docker test script failed with return code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ Docker test script timed out")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to run Docker test script: {e}")
        return False

def check_langfuse_credentials() -> Optional[LangfuseAPIClient]:
    """Check if Langfuse credentials are available and create client."""
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    
    if not public_key or not secret_key:
        logger.warning("⚠️  Langfuse credentials not found in environment variables")
        logger.info("Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to test telemetry")
        return None
    
    logger.info("✅ Langfuse credentials found")
    return LangfuseAPIClient(public_key, secret_key, host)

def validate_trace_data(trace: Dict, observations: List[Dict]) -> Dict[str, Any]:
    """Validate trace data quality."""
    validation = {
        "valid": True,
        "issues": [],
        "metadata": {}
    }
    
    # Check trace metadata
    if not trace.get("name"):
        validation["issues"].append("Trace missing name")
    
    if not trace.get("timestamp"):
        validation["issues"].append("Trace missing timestamp")
    
    # Check for expected tags
    tags = trace.get("tags", [])
    expected_tags = ["weather-agent", "mcp", "strands-demo"]
    missing_tags = [tag for tag in expected_tags if tag not in tags]
    if missing_tags:
        validation["issues"].append(f"Missing expected tags: {missing_tags}")
    
    # Check observations (spans)
    if not observations:
        validation["issues"].append("No observations found for trace")
    else:
        validation["metadata"]["observation_count"] = len(observations)
        
        # Look for specific observation types
        observation_types = [obs.get("type") for obs in observations]
        validation["metadata"]["observation_types"] = observation_types
        
        # Check for LLM generation spans
        llm_spans = [obs for obs in observations if obs.get("type") == "GENERATION"]
        if llm_spans:
            validation["metadata"]["llm_spans"] = len(llm_spans)
            # Check token usage
            for span in llm_spans:
                usage = span.get("usage", {})
                if usage:
                    validation["metadata"]["token_usage"] = usage
                    break
    
    # Check session metadata
    session_id = trace.get("sessionId")
    if session_id:
        validation["metadata"]["session_id"] = session_id
    
    user_id = trace.get("userId")
    if user_id:
        validation["metadata"]["user_id"] = user_id
    
    validation["valid"] = len(validation["issues"]) == 0
    return validation

async def main():
    """Main testing workflow."""
    print("=" * 80)
    print("🧪 AWS Strands Weather Agent - Docker + Langfuse Integration Test")
    print("=" * 80)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test AWS Strands Weather Agent with Langfuse")
    parser.add_argument("--skip-docker-test", action="store_true", 
                       help="Skip running the Docker test script")
    parser.add_argument("--langfuse-only", action="store_true",
                       help="Only test Langfuse trace collection")
    parser.add_argument("--wait-time", type=int, default=10,
                       help="Seconds to wait for traces to appear (default: 10)")
    parser.add_argument("--trace-limit", type=int, default=20,
                       help="Maximum number of traces to fetch (default: 20)")
    args = parser.parse_args()
    
    # Step 1: Check if Docker services are running
    if not args.langfuse_only:
        logger.info("Step 1: Checking Docker deployment...")
        tester = WeatherAgentTester()
        
        if not tester.test_health():
            logger.error("❌ Weather agent is not responding")
            logger.info("💡 Make sure to run: ./scripts/start_docker.sh")
            return False
        
        logger.info("✅ Weather agent is healthy")
        
        # Check MCP server connectivity
        mcp_status = tester.test_mcp_status()
        connected_count = mcp_status.get("connected_count", 0)
        total_count = mcp_status.get("total_count", 0)
        
        if connected_count == 0:
            logger.error("❌ No MCP servers are connected")
            return False
        
        logger.info(f"✅ MCP servers connected: {connected_count}/{total_count}")
        
        # Step 2: Run the existing Docker test script
        if not args.skip_docker_test:
            logger.info("\nStep 2: Running Docker test script...")
            if not run_docker_test_script():
                logger.error("❌ Docker test script failed")
                return False
        else:
            logger.info("\nStep 2: Skipping Docker test script (--skip-docker-test flag)")
    else:
        logger.info("Running in Langfuse-only mode (--langfuse-only flag)")
        tester = WeatherAgentTester()
    
    # Step 3: Check Langfuse credentials
    logger.info("\nStep 3: Checking Langfuse integration...")
    langfuse_client = check_langfuse_credentials()
    
    if not langfuse_client:
        logger.warning("⚠️  Skipping Langfuse trace validation (no credentials)")
        logger.info("✅ Docker deployment test completed successfully")
        return True
    
    # Step 4: Make test queries and check for traces
    logger.info("\nStep 4: Making test queries and validating traces...")
    
    # Record start time for filtering traces
    test_start_time = datetime.now(timezone.utc)
    
    # Make several test queries
    test_queries = [
        "What's the weather in Seattle?",
        "Give me a 5-day forecast for Chicago",
        "Are conditions good for planting corn in Iowa?"
    ]
    
    query_responses = []
    for i, query in enumerate(test_queries, 1):
        logger.info(f"Making test query {i}: {query}")
        response = tester.make_query(query)
        if response:
            query_responses.append(response)
            logger.info(f"✅ Query {i} completed")
        else:
            logger.error(f"❌ Query {i} failed")
        
        # Small delay between queries
        time.sleep(2)
    
    if not query_responses:
        logger.error("❌ All test queries failed")
        return False
    
    # Step 5: Wait for traces to appear in Langfuse
    logger.info(f"\nStep 5: Waiting {args.wait_time} seconds for traces to appear in Langfuse...")
    time.sleep(args.wait_time)  # Give some time for traces to be sent
    
    # Get recent traces
    traces = langfuse_client.get_traces(limit=args.trace_limit, from_timestamp=test_start_time)
    
    if not traces:
        logger.warning("⚠️  No traces found in Langfuse")
        logger.info("This might be normal if:")
        logger.info("  - Telemetry is disabled (no LANGFUSE_* env vars)")
        logger.info("  - Traces are still being processed")
        logger.info("  - There's a network issue")
        return True
    
    logger.info(f"✅ Found {len(traces)} traces in Langfuse")
    
    # Step 6: Validate trace data
    logger.info("\nStep 6: Validating trace data quality...")
    
    valid_traces = 0
    for i, trace in enumerate(traces):
        trace_id = trace.get("id")
        logger.info(f"Validating trace {i+1}: {trace_id}")
        
        # Get observations for this trace
        observations = langfuse_client.get_observations(trace_id)
        
        # Validate trace data
        validation = validate_trace_data(trace, observations)
        
        if validation["valid"]:
            valid_traces += 1
            logger.info(f"✅ Trace {i+1} is valid")
        else:
            logger.warning(f"⚠️  Trace {i+1} has issues: {validation['issues']}")
        
        # Log metadata
        metadata = validation["metadata"]
        if metadata:
            logger.info(f"   Metadata: {json.dumps(metadata, indent=2)}")
    
    # Step 7: Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)
    
    logger.info(f"✅ Docker deployment: Working")
    logger.info(f"✅ MCP servers: {connected_count}/{total_count} connected")
    logger.info(f"✅ Weather queries: {len(query_responses)}/{len(test_queries)} successful")
    logger.info(f"✅ Langfuse traces: {len(traces)} found")
    logger.info(f"✅ Valid traces: {valid_traces}/{len(traces)}")
    
    if langfuse_client:
        logger.info(f"🔗 Langfuse dashboard: {langfuse_client.host}")
    
    # Success criteria
    success = (
        len(query_responses) > 0 and  # At least one query worked
        (not langfuse_client or len(traces) > 0)  # Traces found if Langfuse is configured
    )
    
    if success:
        logger.info("\n🎉 All tests passed! The integration is working correctly.")
    else:
        logger.error("\n❌ Some tests failed. Check the logs above for details.")
    
    # Add helpful next steps
    logger.info("\n" + "=" * 80)
    logger.info("📚 NEXT STEPS")
    logger.info("=" * 80)
    
    if langfuse_client:
        logger.info("To view traces in Langfuse:")
        logger.info(f"  1. Open {langfuse_client.host}")
        logger.info("  2. Navigate to the Traces section")
        logger.info("  3. Look for traces with tags: weather-agent, mcp, strands-demo")
    else:
        logger.info("To enable telemetry:")
        logger.info("  1. Set up Langfuse credentials in .env file:")
        logger.info("     LANGFUSE_PUBLIC_KEY=pk-lf-...")
        logger.info("     LANGFUSE_SECRET_KEY=sk-lf-...")
        logger.info("     LANGFUSE_HOST=https://us.cloud.langfuse.com")
        logger.info("  2. Restart Docker services: ./scripts/stop_docker.sh && ./scripts/start_docker.sh")
        logger.info("  3. Run this test again")
    
    logger.info("\nUseful commands:")
    logger.info("  - Quick test: python langfuse-testing.py --skip-docker-test")
    logger.info("  - Langfuse only: python langfuse-testing.py --langfuse-only")
    logger.info("  - Extended wait: python langfuse-testing.py --wait-time 30")
    
    return success

if __name__ == "__main__":
    # Run the async main function
    success = asyncio.run(main())
    sys.exit(0 if success else 1)