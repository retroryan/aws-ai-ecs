#!/usr/bin/env python3
"""
Demo Script for Strands Weather Agent with Langfuse Telemetry
Showcases the integration in a clear, demo-friendly way
"""

import json
import time
import requests
import boto3
from pathlib import Path
from dotenv import load_dotenv
import os
import sys
from datetime import datetime
from typing import Dict, List, Any


class TelemetryDemo:
    """Demo showcasing Langfuse telemetry integration"""
    
    def __init__(self, region="us-east-1"):
        self.region = region
        self.cfn = boto3.client("cloudformation", region_name=region)
        self.session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Metrics tracking
        self.total_queries = 0
        self.successful_queries = 0
        self.total_tokens_all = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_latency = 0.0
        self.total_cycles = 0
        self.model_used = ""
        self.all_session_ids = []
        self.query_metrics = []
        
    def get_api_url(self):
        """Get API URL from environment or CloudFormation stack."""
        # Try environment variable first
        api_url = os.getenv("API_URL")
        if api_url:
            return api_url
        
        # Try to get from CloudFormation stack
        try:
            # Check services stack for ALB URL
            response = self.cfn.describe_stacks(StackName="strands-weather-agent-services")
            for output in response["Stacks"][0].get("Outputs", []):
                if output["OutputKey"] == "ApplicationURL":
                    return output["OutputValue"]
            
            # Check base stack for ALB URL
            response = self.cfn.describe_stacks(StackName="strands-weather-agent-base")
            for output in response["Stacks"][0].get("Outputs", []):
                if output["OutputKey"] == "ALBDNSName":
                    return f"http://{output['OutputValue']}"
                    
        except Exception:
            pass
        
        # Default to localhost
        return "http://localhost:7777"
    
    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{'=' * 60}")
        print(f"🌟 {text}")
        print('=' * 60)
    
    def run_query(self, url, query, delay=2):
        """Run a query and display results"""
        print(f"\n📍 Query: '{query}'")
        
        payload = {
            "query": query,
            "session_id": self.session_id
        }
        
        self.total_queries += 1
        
        try:
            start_time = time.time()
            resp = requests.post(f"{url}/query", json=payload, timeout=30)
            elapsed = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Response ({elapsed:.1f}s):")
                print(f"   {data['summary'][:150]}...")
                
                # Track session ID
                session_id = data.get('session_id')
                if session_id and session_id not in self.all_session_ids:
                    self.all_session_ids.append(session_id)
                
                # Show telemetry hints
                if 'telemetry_enabled' in data and data['telemetry_enabled']:
                    print(f"📊 Telemetry: ✅ Active (trace recorded)")
                else:
                    print(f"📊 Telemetry: ⚠️  Not configured")
                
                # Display and track metrics if available
                metrics = data.get('metrics', {})
                if metrics:
                    print("\n📊 Performance Metrics:")
                    total_tokens = metrics.get('total_tokens', 0)
                    input_tokens = metrics.get('input_tokens', 0)
                    output_tokens = metrics.get('output_tokens', 0)
                    latency_seconds = metrics.get('latency_seconds', 0)
                    throughput = metrics.get('throughput_tokens_per_second', 0)
                    model = metrics.get('model', 'unknown')
                    cycles = metrics.get('cycles', 0)
                    
                    print(f"   ├─ Tokens: {total_tokens} total ({input_tokens} input, {output_tokens} output)")
                    print(f"   ├─ Latency: {latency_seconds:.2f} seconds")
                    print(f"   ├─ Throughput: {int(throughput)} tokens/second")
                    print(f"   ├─ Model: {model}")
                    print(f"   └─ Cycles: {cycles}")
                    
                    # Accumulate metrics
                    self.total_tokens_all += total_tokens
                    self.total_input_tokens += input_tokens
                    self.total_output_tokens += output_tokens
                    self.total_latency += latency_seconds
                    self.total_cycles += cycles
                    self.model_used = model
                    self.successful_queries += 1
                    
                    # Store query metrics
                    self.query_metrics.append({
                        'query': query,
                        'tokens': total_tokens,
                        'latency': latency_seconds,
                        'throughput': throughput
                    })
                
                # Display trace URL if available
                trace_url = data.get('trace_url', '')
                if trace_url:
                    print(f"\n🔗 Trace: {trace_url}")
                
                time.sleep(delay)  # Pause for demo effect
                return True
            else:
                print(f"❌ Query failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def run_demo(self):
        """Run the full demo"""
        self.print_header("AWS Strands + Langfuse Telemetry Demo")
        
        # Get service URL
        url = self.get_api_url()
        
        print(f"\n🌐 Service URL: {url}")
        print(f"📝 Session ID: {self.session_id}")
        
        # Check telemetry status
        self.print_header("Checking Telemetry Configuration")
        
        # Load cloud.env to check Langfuse config
        cloud_env = Path(__file__).parent.parent / "cloud.env"
        if cloud_env.exists():
            load_dotenv(cloud_env)
            langfuse_host = os.getenv("LANGFUSE_HOST")
            if langfuse_host:
                print(f"✅ Langfuse configured: {langfuse_host}")
                print("📊 Traces will be visible in your Langfuse dashboard")
            else:
                print("⚠️  Langfuse host not configured in cloud.env")
        else:
            print("⚠️  cloud.env not found - telemetry disabled")
            print("   To enable telemetry, add Langfuse credentials to cloud.env")
        
        # Run demo queries
        self.print_header("Demo Scenario: Weather Planning Assistant")
        
        demo_queries = [
            {
                "query": "What's the current weather in San Francisco?",
                "description": "Simple current weather query"
            },
            {
                "query": "I'm planning a weekend trip to Seattle. What's the weather forecast?",
                "description": "Multi-day forecast query"
            },
            {
                "query": "Compare the weather between Chicago and Miami for the next 3 days",
                "description": "Complex comparison query"
            },
            {
                "query": "Should I plant tomatoes in Minneapolis this week?",
                "description": "Agricultural recommendation query"
            }
        ]
        
        print("\n🎯 Running demo queries to showcase telemetry...")
        
        for i, demo in enumerate(demo_queries, 1):
            print(f"\n[{i}/{len(demo_queries)}] {demo['description']}")
            self.run_query(url, demo['query'])
        
        # Show telemetry insights
        self.print_header("Telemetry Insights")
        
        if langfuse_host:
            print("🎉 Demo complete! Check your Langfuse dashboard to see:")
            print("\n   📊 Trace Timeline: See the full execution flow")
            print("   🔍 Tool Calls: Which MCP servers were invoked")
            print("   ⏱️  Latency: Time spent in each component")
            print("   💰 Token Usage: LLM token consumption metrics")
            print("   🏷️  Session Tracking: All queries grouped by session")
            print(f"\n👉 Dashboard: {langfuse_host}")
            print(f"👉 Filter by session: {self.session_id}")
        else:
            print("ℹ️  To see telemetry data:")
            print("1. Add your Langfuse credentials to cloud.env")
            print("2. Redeploy: python3 infra/deploy.py services")
            print("3. Run this demo again")
        
        # Display comprehensive metrics summary
        if self.successful_queries > 0:
            self.print_header("OVERALL METRICS SUMMARY")
            
            print("Query Statistics:")
            print(f"  Total Queries: {self.total_queries}")
            print(f"  Successful Queries: {self.successful_queries}")
            print(f"  Unique Sessions: {len(self.all_session_ids)}")
            print("")
            
            print("Token Usage:")
            print(f"  Total Tokens: {self.total_tokens_all:,}")
            print(f"  Input Tokens: {self.total_input_tokens:,}")
            print(f"  Output Tokens: {self.total_output_tokens:,}")
            
            # Calculate averages
            avg_tokens = self.total_tokens_all // self.successful_queries
            avg_input = self.total_input_tokens // self.successful_queries
            avg_output = self.total_output_tokens // self.successful_queries
            avg_latency = self.total_latency / self.successful_queries
            
            print(f"  Average per Query: {avg_tokens:,} tokens ({avg_input:,} in, {avg_output:,} out)")
            print("")
            
            print("Performance:")
            print(f"  Total Processing Time: {self.total_latency:.1f}s")
            print(f"  Average Latency: {avg_latency:.2f}s per query")
            if self.total_latency > 0:
                avg_throughput = int(self.total_tokens_all / self.total_latency)
                print(f"  Overall Throughput: {avg_throughput:,} tokens/second")
            print(f"  Total Agent Cycles: {self.total_cycles}")
            print(f"  Model: {self.model_used}")
            
            # Show telemetry summary if enabled
            if langfuse_host and os.getenv("LANGFUSE_PUBLIC_KEY"):
                print("")
                print("Telemetry:")
                print(f"  Langfuse Host: {langfuse_host}")
                print(f"  Traces Generated: {self.successful_queries}")
                print(f"  Sessions Tracked: {len(self.all_session_ids)}")
            
            # Cost estimation based on AWS Bedrock pricing
            if self.model_used:
                pass  # Placeholder for cost estimation
        
        # API docs reminder
        print(f"\n📚 Explore the API: {url}/docs")
        print(f"📖 View API metrics: {url}/metrics" if self.successful_queries > 0 else "")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Demo script for AWS Strands with Langfuse telemetry"
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    
    args = parser.parse_args()
    
    demo = TelemetryDemo(args.region)
    
    # Check if API is accessible
    api_url = demo.get_api_url()
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Cannot connect to API at {api_url}")
        print(f"Details: {e}")
        print("\nMake sure the Weather Agent is running:")
        print("- Local: python main.py")
        print("- Docker: ./scripts/start_docker.sh")
        print("- AWS: python infra/deploy.py status")
        sys.exit(1)
    
    demo.run_demo()


if __name__ == "__main__":
    main()