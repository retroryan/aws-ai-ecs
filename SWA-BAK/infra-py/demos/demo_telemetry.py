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
from datetime import datetime


class TelemetryDemo:
    """Demo showcasing Langfuse telemetry integration"""
    
    def __init__(self, region="us-east-1"):
        self.region = region
        self.cfn = boto3.client("cloudformation", region_name=region)
        self.session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
    def get_alb_url(self):
        """Get ALB URL from CloudFormation"""
        try:
            stack = self.cfn.describe_stacks(StackName="strands-weather-agent-base")["Stacks"][0]
            for output in stack["Outputs"]:
                if output["OutputKey"] == "ALBDNSName":
                    return f"http://{output['OutputValue']}"
        except:
            return None
    
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
        
        try:
            start_time = time.time()
            resp = requests.post(f"{url}/query", json=payload, timeout=30)
            elapsed = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Response ({elapsed:.1f}s):")
                print(f"   {data['response'][:150]}...")
                
                # Show telemetry hints
                if 'telemetry_enabled' in data and data['telemetry_enabled']:
                    print(f"📊 Telemetry: ✅ Active (trace recorded)")
                else:
                    print(f"📊 Telemetry: ⚠️  Not configured")
                
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
        url = self.get_alb_url()
        if not url:
            print("❌ Could not find deployed service. Deploy with:")
            print("   python3 infra/deploy.py all")
            return
        
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
            print("   To enable: cp cloud.env.example cloud.env")
        
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
            print("   💰 Token Usage: LLM token consumption and costs")
            print("   🏷️  Session Tracking: All queries grouped by session")
            print(f"\n👉 Dashboard: {langfuse_host}")
            print(f"👉 Filter by session: {self.session_id}")
        else:
            print("ℹ️  To see telemetry data:")
            print("1. Add your Langfuse credentials to cloud.env")
            print("2. Redeploy: python3 infra/deploy.py services")
            print("3. Run this demo again")
        
        # API docs reminder
        print(f"\n📚 Explore the API: {url}/docs")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Demo script for AWS Strands with Langfuse telemetry"
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    
    args = parser.parse_args()
    
    demo = TelemetryDemo(args.region)
    demo.run_demo()


if __name__ == "__main__":
    main()