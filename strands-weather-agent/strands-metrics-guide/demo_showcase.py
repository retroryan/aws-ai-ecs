#!/usr/bin/env python3
"""
Professional demo showcase for AWS Strands Weather Agent with Langfuse metrics.

This script provides a polished demonstration of the Weather Agent's capabilities
including multi-server coordination, structured output, and telemetry tracking.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import argparse
from typing import List, Dict, Any
import json

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
    
    def __init__(self, enable_telemetry: bool = True, verbose: bool = False):
        self.enable_telemetry = enable_telemetry
        self.verbose = verbose
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
        
        start_time = datetime.now()
        
        try:
            # Run the query
            response = await agent.query(query)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Truncate response for display
            display_response = response[:200] + "..." if len(response) > 200 else response
            print(f"🤖 Response: {display_response}")
            print(f"⏱️  Time: {elapsed:.2f}s")
            
            if show_details and hasattr(agent, 'last_tool_calls'):
                print(f"🔧 Tools used: {len(agent.last_tool_calls)}")
            
            return {
                "query": query,
                "response": response,
                "elapsed": elapsed,
                "success": True
            }
            
        except Exception as e:
            print(f"❌ Error: {e}")
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
                debug_logging=self.verbose,
                enable_telemetry=self.enable_telemetry,
                telemetry_user_id="demo-showcase",
                telemetry_session_id=session_id,
                telemetry_tags=["showcase", "demo", "weather-agent"]
            )
            print("✅ Agent initialized successfully")
            
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


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Professional Weather Agent Demo Showcase")
    parser.add_argument("--no-telemetry", action="store_true", 
                        help="Disable Langfuse telemetry")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed information")
    parser.add_argument("--quick", action="store_true",
                        help="Run a quick demo with fewer queries")
    
    args = parser.parse_args()
    
    showcase = WeatherAgentDemoShowcase(
        enable_telemetry=not args.no_telemetry,
        verbose=args.verbose
    )
    
    if args.quick:
        # Reduce queries for quick demo
        showcase.demo_queries = showcase.demo_queries[:2]
        for category in showcase.demo_queries:
            category["queries"] = category["queries"][:1]
    
    await showcase.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main())