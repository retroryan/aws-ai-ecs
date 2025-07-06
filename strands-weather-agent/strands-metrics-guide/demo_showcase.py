#!/usr/bin/env python3
"""
Professional demo showcase for AWS Strands Weather Agent with Langfuse v3 metrics and debug logging.

This script provides a comprehensive demonstration of the Weather Agent's capabilities:
- Multi-server coordination across forecast, historical, and agricultural data
- Structured output with type-safe responses
- Telemetry tracking with Langfuse v3 (OTEL-based with scoring support)
- Debug logging for development insights
- Deterministic trace IDs and evaluation scoring
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
from typing import List, Dict, Any
import json
import logging
from base64 import b64encode
import requests

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Load .env file FIRST before any other imports
from dotenv import load_dotenv
env_path = parent_dir / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)

from weather_agent.mcp_agent import create_weather_agent
from weather_agent.langfuse_telemetry import force_flush_telemetry


class WeatherAgentDemoShowcase:
    """Professional demo showcase for the Weather Agent system."""
    
    def __init__(self, enable_telemetry: bool = True, verbose: bool = False, debug: bool = False):
        self.enable_telemetry = enable_telemetry
        self.verbose = verbose
        self.debug = debug
        self.logger = self._setup_logging()
        self.demo_queries = [
            {
                "category": "Current Weather",
                "queries": [
                    "What's the current weather in San Francisco?",
                    "Tell me about the temperature and conditions in New York City"
                ]
            },
            {
                "category": "Weather Forecasts",
                "queries": [
                    "Give me a 5-day forecast for Seattle",
                    "What's the weather forecast for Chicago this week?"
                ]
            },
            {
                "category": "Historical Weather",
                "queries": [
                    "What was the weather like in Los Angeles last week?",
                    "Show me historical temperatures for Boston over the past month"
                ]
            },
            {
                "category": "Agricultural Insights",
                "queries": [
                    "Are conditions good for planting tomatoes in Iowa?",
                    "What's the frost risk for crops in Minnesota?"
                ]
            },
            {
                "category": "Multi-Location Comparisons",
                "queries": [
                    "Compare the weather between Miami and Denver",
                    "Which city has better weather right now: Phoenix or Portland?"
                ]
            }
        ]
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger("demo_showcase")
        logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
        
        # Remove existing handlers
        logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
        
        # File handler for debug logs
        if self.debug:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"demo_showcase_debug_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
            
            # Enable debug for Strands modules
            for module in ['strands', 'strands.tools', 'strands.models', 'strands.tools.mcp']:
                logging.getLogger(module).setLevel(logging.DEBUG)
            
            print(f"📝 Debug logs will be saved to: {log_file}")
        
        return logger
    
    def print_header(self):
        """Print a professional header for the demo."""
        print("\n" + "="*80)
        print("🌤️  AWS STRANDS WEATHER AGENT DEMO SHOWCASE")
        print("="*80)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔧 Model: {os.getenv('BEDROCK_MODEL_ID', 'Not configured')}")
        print(f"🌍 Region: {os.getenv('BEDROCK_REGION', 'us-west-2')}")
        if self.enable_telemetry:
            print(f"📊 Telemetry: Enabled (Langfuse)")
        else:
            print(f"📊 Telemetry: Disabled")
        if self.debug:
            print(f"🐛 Debug Mode: Enabled")
        print("="*80)
    
    def print_category_header(self, category: str, description: str = ""):
        """Print a category header."""
        print(f"\n{'─'*60}")
        print(f"📁 {category.upper()}")
        if description:
            print(f"   {description}")
        print(f"{'─'*60}")
    
    async def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met."""
        print("\n🔍 Checking prerequisites...")
        
        all_good = True
        
        # Check AWS credentials
        try:
            import boto3
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print(f"✅ AWS credentials configured (Account: {identity['Account']})")
        except Exception as e:
            print(f"❌ AWS credentials not configured: {e}")
            all_good = False
        
        # Check MCP servers
        import requests
        servers = {
            "Forecast Server": "http://localhost:7778/health",
            "Historical Server": "http://localhost:7779/health",
            "Agricultural Server": "http://localhost:7780/health"
        }
        
        for name, url in servers.items():
            try:
                resp = requests.get(url, timeout=2)
                if resp.status_code == 200:
                    print(f"✅ {name} is running")
                else:
                    print(f"❌ {name} returned status {resp.status_code}")
                    all_good = False
            except Exception:
                print(f"❌ {name} is not accessible")
                all_good = False
        
        # Check Langfuse if telemetry is enabled
        if self.enable_telemetry:
            host = os.getenv('LANGFUSE_HOST')
            if host and os.getenv('LANGFUSE_PUBLIC_KEY'):
                print(f"✅ Langfuse configured ({host})")
            else:
                print("⚠️  Langfuse not configured (telemetry will be disabled)")
                self.enable_telemetry = False
        
        return all_good
    
    async def run_query_demo(self, agent, query: str, show_details: bool = False) -> Dict[str, Any]:
        """Run a single query and return results."""
        print(f"\n💬 Query: \"{query}\"")
        self.logger.debug(f"Running query: {query}")
        
        start_time = datetime.now()
        
        try:
            # Run the query
            response = await agent.query(query)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Truncate response for display
            display_response = response[:200] + "..." if len(response) > 200 else response
            print(f"🤖 Response: {display_response}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            
            self.logger.debug(f"Query completed in {elapsed:.2f}s")
            self.logger.debug(f"Full response: {response}")
            
            if show_details and hasattr(agent, 'last_tool_calls'):
                print(f"🔧 Tools used: {len(agent.last_tool_calls)}")
                self.logger.debug(f"Tool calls: {agent.last_tool_calls}")
            
            return {
                "query": query,
                "response": response,
                "elapsed": elapsed,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
            self.logger.error(f"Query failed: {e}", exc_info=True)
            return {
                "query": query,
                "error": str(e),
                "elapsed": 0,
                "success": False
            }
    
    async def run_structured_output_demo(self, agent):
        """Demonstrate structured output capabilities."""
        self.print_category_header("Structured Output Demo", 
                                   "Showing type-safe structured responses")
        
        test_queries = [
            "What's the weather in Tokyo?",
            "Compare temperatures in London and Paris"
        ]
        
        for query in test_queries:
            print(f"\n💬 Query: \"{query}\"")
            try:
                response = await agent.query_structured(query)
                
                print("📋 Structured Response:")
                print(f"   Summary: {response.summary[:100]}...")
                print(f"   Query Type: {response.query_type}")
                print(f"   Locations Found: {len(response.locations)}")
                
                for loc in response.locations:
                    print(f"   📍 {loc.name}: ({loc.latitude:.2f}, {loc.longitude:.2f})")
                    if hasattr(loc, 'timezone'):
                        print(f"      Timezone: {loc.timezone}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def run_full_demo(self):
        """Run the complete demo showcase."""
        self.print_header()
        
        # Check prerequisites
        if not await self.check_prerequisites():
            print("\n⚠️  Some prerequisites are not met. Demo may not work properly.")
            response = input("Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return
        
        # Initialize agent
        print("\n🚀 Initializing Weather Agent...")
        
        session_id = f"demo-showcase-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        try:
            agent = await create_weather_agent(
                debug_logging=self.debug,
                enable_telemetry=self.enable_telemetry,
                telemetry_user_id="demo-showcase",
                telemetry_session_id=session_id,
                telemetry_tags=["showcase", "demo", "weather-agent"]
            )
            print("✅ Agent initialized successfully")
            self.logger.debug(f"Agent created with session ID: {session_id}")
            
            # Test connectivity
            print("\n🔗 Testing MCP server connectivity...")
            connectivity = await agent.test_connectivity()
            for server, status in connectivity.items():
                status_icon = "✅" if status else "❌"
                print(f"   {status_icon} {server} server")
            
            # Run demo queries by category
            all_results = []
            
            for category_info in self.demo_queries:
                category = category_info["category"]
                queries = category_info["queries"]
                
                self.print_category_header(category)
                
                for query in queries:
                    result = await self.run_query_demo(agent, query, self.verbose)
                    all_results.append(result)
                    
                    # Small delay between queries
                    await asyncio.sleep(0.5)
            
            # Structured output demo
            if self.verbose:
                await self.run_structured_output_demo(agent)
            
            # Show summary
            self.print_summary(all_results)
            
            # Flush telemetry if enabled
            if self.enable_telemetry:
                print("\n📊 Flushing telemetry data...")
                force_flush_telemetry()
                print(f"✅ Telemetry data sent to Langfuse")
                print(f"🔗 View traces at: {os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')}")
                print(f"   Session ID: {session_id}")
                
                # Validate metrics if requested
                if self.verbose:
                    await self.validate_metrics(session_id)
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print a summary of the demo results."""
        print("\n" + "="*80)
        print("📊 DEMO SUMMARY")
        print("="*80)
        
        total = len(results)
        successful = sum(1 for r in results if r["success"])
        failed = total - successful
        
        print(f"Total Queries: {total}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        if successful > 0:
            avg_time = sum(r["elapsed"] for r in results if r["success"]) / successful
            print(f"⏱️  Average Response Time: {avg_time:.2f}s")
        
        print("\n✨ Demo showcase complete!")
        print("="*80)
    
    def get_auth_header(self):
        """Create Basic Auth header for Langfuse API"""
        public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        secret_key = os.getenv('LANGFUSE_SECRET_KEY')
        if not public_key or not secret_key:
            return None
        credentials = f"{public_key}:{secret_key}"
        encoded_credentials = b64encode(credentials.encode()).decode('ascii')
        return {"Authorization": f"Basic {encoded_credentials}"}
    
    async def validate_metrics(self, session_id: str):
        """Validate that metrics were properly recorded in Langfuse."""
        print("\n🔍 Validating metrics in Langfuse...")
        
        # Wait for traces to be processed
        await asyncio.sleep(5)
        
        host = os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')
        headers = self.get_auth_header()
        
        if not headers:
            print("⚠️  Cannot validate metrics - Langfuse credentials not configured")
            return
        
        try:
            # Query for recent traces
            url = f"{host}/api/public/traces"
            params = {
                "limit": 50,
                "orderBy": "timestamp.desc"
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            traces = data.get('data', [])
            
            # Find traces from this session
            session_traces = []
            for trace in traces:
                metadata = trace.get('metadata', {})
                attributes = metadata.get('attributes', {})
                trace_session = attributes.get('session.id', '')
                
                if session_id in trace_session:
                    session_traces.append(trace)
            
            if session_traces:
                print(f"✅ Found {len(session_traces)} traces from this session")
                
                # Analyze metrics
                total_tokens = 0
                total_latency = 0
                tools_used = set()
                
                for trace in session_traces:
                    # Token usage
                    usage = trace.get('usage', {})
                    if usage:
                        total_tokens += usage.get('total', 0)
                    
                    # Latency
                    latency = trace.get('latency', 0)
                    total_latency += latency
                    
                    # Tool usage
                    attributes = trace.get('metadata', {}).get('attributes', {})
                    for key, value in attributes.items():
                        if 'tool' in key.lower():
                            tools_used.add(value)
                
                print(f"📊 Metrics Summary:")
                print(f"   Total tokens used: {total_tokens:,}")
                print(f"   Average latency: {total_latency/len(session_traces):.0f}ms")
                print(f"   Unique tools called: {len(tools_used)}")
                
                # Cost estimation (rough)
                if total_tokens > 0:
                    model_id = os.getenv('BEDROCK_MODEL_ID', '')
                    if 'claude' in model_id.lower():
                        # Rough Claude pricing
                        input_cost = 0.003  # per 1K tokens
                        output_cost = 0.015  # per 1K tokens
                        estimated_cost = (total_tokens / 1000) * ((input_cost + output_cost) / 2)
                        print(f"   Estimated cost: ${estimated_cost:.4f}")
            else:
                print("⚠️  No traces found for this session yet")
                
        except Exception as e:
            print(f"⚠️  Could not validate metrics: {e}")
            self.logger.debug(f"Metrics validation error: {e}", exc_info=True)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Professional Weather Agent Demo Showcase")
    parser.add_argument("--no-telemetry", action="store_true", 
                        help="Disable Langfuse telemetry")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed information and validate metrics")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Enable debug logging to file")
    parser.add_argument("--quick", action="store_true",
                        help="Run a quick demo with fewer queries")
    
    args = parser.parse_args()
    
    showcase = WeatherAgentDemoShowcase(
        enable_telemetry=not args.no_telemetry,
        verbose=args.verbose,
        debug=args.debug
    )
    
    if args.quick:
        # Reduce queries for quick demo
        showcase.demo_queries = showcase.demo_queries[:2]
        for category in showcase.demo_queries:
            category["queries"] = category["queries"][:1]
    
    await showcase.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main())