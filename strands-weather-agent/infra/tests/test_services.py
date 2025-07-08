#!/usr/bin/env python3
"""
Simple Test Script for Strands Weather Agent Demo
Tests the deployed services and Langfuse connectivity
"""

import json
import sys
import time
from pathlib import Path
import requests
import boto3
from dotenv import load_dotenv
import os


class ServiceTester:
    """Test deployed services and telemetry"""
    
    def __init__(self, region="us-east-1"):
        self.region = region
        self.cfn = boto3.client("cloudformation", region_name=region)
        self.ecs = boto3.client("ecs", region_name=region)
        self.logs = boto3.client("logs", region_name=region)
        
        # Load configuration
        self.load_config()
        
    def load_config(self):
        """Load cloud.env if it exists"""
        # Try multiple possible locations for cloud.env
        possible_paths = [
            Path(__file__).parent.parent.parent / "cloud.env",  # From tests directory
            Path(__file__).parent.parent / "cloud.env",         # From infra-py directory
            Path.cwd() / "cloud.env"                            # From current directory
        ]
        
        cloud_env = None
        for path in possible_paths:
            if path.exists():
                cloud_env = path
                break
        
        if cloud_env:
            load_dotenv(cloud_env)
            self.langfuse_host = os.getenv("LANGFUSE_HOST")
            self.langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        else:
            self.langfuse_host = None
            self.langfuse_public_key = None
    
    def get_alb_url(self):
        """Get the ALB URL from CloudFormation"""
        try:
            stack = self.cfn.describe_stacks(StackName="strands-weather-agent-base")["Stacks"][0]
            for output in stack["Outputs"]:
                if output["OutputKey"] == "ALBDNSName":
                    return f"http://{output['OutputValue']}"
        except Exception as e:
            print(f"❌ Could not get ALB URL: {e}")
            return None
    
    def test_health(self, base_url):
        """Test health endpoint"""
        print("\n🏥 Testing Health Endpoint...")
        try:
            resp = requests.get(f"{base_url}/health", timeout=10)
            if resp.status_code == 200:
                print(f"✅ Health check passed: {resp.json()}")
                return True
            else:
                print(f"❌ Health check failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def test_query(self, base_url, query):
        """Test a weather query"""
        print(f"\n🤖 Testing query: '{query}'")
        try:
            resp = requests.post(
                f"{base_url}/query",
                json={"query": query},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Response: {data['response']}")
                if 'session_id' in data:
                    print(f"📝 Session ID: {data['session_id']}")
                
                # Display performance metrics if available
                if 'metrics' in data and data['metrics']:
                    metrics = data['metrics']
                    print("\n📊 Performance Metrics:")
                    print(f"   ├─ Tokens: {metrics.get('total_tokens', 0)} total "
                          f"({metrics.get('input_tokens', 0)} input, "
                          f"{metrics.get('output_tokens', 0)} output)")
                    print(f"   ├─ Latency: {metrics.get('latency_seconds', 0)} seconds")
                    print(f"   ├─ Throughput: {metrics.get('throughput_tokens_per_second', 0):.0f} tokens/second")
                    print(f"   ├─ Model: {metrics.get('model', 'unknown')}")
                    print(f"   └─ Cycles: {metrics.get('cycles', 0)}")
                
                # Display trace URL if available
                if 'trace_url' in data and data['trace_url']:
                    print(f"\n🔗 Trace: {data['trace_url']}")
                
                return True
            else:
                print(f"❌ Query failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ Query error: {e}")
            return False
    
    def test_mcp_status(self, base_url):
        """Test MCP server connectivity"""
        print("\n🔌 Testing MCP Server Status...")
        try:
            resp = requests.get(f"{base_url}/mcp/status", timeout=10)
            if resp.status_code == 200:
                status = resp.json()
                print(f"✅ Connected servers: {status['connected_count']}/{status['total_count']}")
                for server, connected in status['servers'].items():
                    emoji = "✅" if connected else "❌"
                    print(f"   {emoji} {server}: {'connected' if connected else 'disconnected'}")
                return True
            else:
                print(f"❌ MCP status failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"❌ MCP status error: {e}")
            return False
    
    def test_langfuse_connectivity(self):
        """Test Langfuse connectivity if configured"""
        if not self.langfuse_host:
            print("\n⚠️  Langfuse not configured (cloud.env not found)")
            return
        
        print(f"\n📊 Testing Langfuse Connectivity...")
        print(f"Host: {self.langfuse_host}")
        
        # Check if telemetry is enabled in deployment
        try:
            stack = self.cfn.describe_stacks(StackName="strands-weather-agent-services")["Stacks"][0]
            telemetry_enabled = False
            for param in stack["Parameters"]:
                if param["ParameterKey"] == "EnableTelemetry" and param["ParameterValue"] == "true":
                    telemetry_enabled = True
                    break
            
            if telemetry_enabled:
                print("✅ Telemetry is enabled in deployment")
                
                # Check if Langfuse host is reachable
                try:
                    resp = requests.get(self.langfuse_host, timeout=5)
                    print("✅ Langfuse host is reachable")
                except:
                    print("⚠️  Cannot reach Langfuse host (this may be normal)")
                
                # Check CloudWatch logs for Langfuse activity
                self.check_langfuse_logs()
            else:
                print("⚠️  Telemetry is disabled in deployment")
                print("   Deploy with: python3 infra/deploy.py services")
        except Exception as e:
            print(f"❌ Could not check deployment status: {e}")
    
    def check_langfuse_logs(self):
        """Check CloudWatch logs for Langfuse activity"""
        try:
            # Look for recent Langfuse-related log entries
            response = self.logs.filter_log_events(
                logGroupName="/ecs/strands-weather-agent-main",
                filterPattern="langfuse",
                startTime=int((time.time() - 300) * 1000)  # Last 5 minutes
            )
            
            if response['events']:
                print("✅ Found Langfuse activity in logs")
                print(f"\n📈 Visit your Langfuse dashboard: {self.langfuse_host}")
            else:
                print("⚠️  No recent Langfuse activity (run some queries first)")
        except:
            print("⚠️  Could not check logs (this is normal if no queries have been run)")
    
    def check_ecs_services(self):
        """Check ECS service status"""
        print("\n🐳 ECS Service Status:")
        services = [
            "strands-weather-agent-main",
            "strands-weather-agent-forecast",
            "strands-weather-agent-historical",
            "strands-weather-agent-agricultural"
        ]
        
        for service in services:
            try:
                resp = self.ecs.describe_services(
                    cluster="strands-weather-agent",
                    services=[service]
                )
                if resp['services']:
                    svc = resp['services'][0]
                    status = f"{svc['runningCount']}/{svc['desiredCount']}"
                    emoji = "✅" if svc['runningCount'] == svc['desiredCount'] else "⚠️"
                    print(f"   {emoji} {service}: {status} tasks running")
            except:
                print(f"   ❌ {service}: Not found")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Strands Weather Agent Test Suite")
        print("=" * 50)
        
        # Get ALB URL
        base_url = self.get_alb_url()
        if not base_url:
            print("❌ Cannot proceed without ALB URL")
            return False
        
        print(f"\n🌐 Testing against: {base_url}")
        
        # Check ECS services
        self.check_ecs_services()
        
        # Run tests
        all_passed = True
        all_passed &= self.test_health(base_url)
        all_passed &= self.test_mcp_status(base_url)
        
        # Test some queries and collect metrics
        queries = [
            "What's the weather in Seattle?",
            "Give me a 5-day forecast for Chicago",
            "Are conditions good for planting corn in Iowa?"
        ]
        
        total_tokens = 0
        total_latency = 0
        query_count = 0
        
        for query in queries:
            start_time = time.time()
            resp = requests.post(
                f"{base_url}/query",
                json={"query": query},
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                all_passed &= True
                print(f"\n🤖 Testing query: '{query}'")
                print(f"✅ Response: {data['response']}")
                
                # Collect metrics
                if 'metrics' in data and data['metrics']:
                    metrics = data['metrics']
                    total_tokens += metrics.get('total_tokens', 0)
                    total_latency += metrics.get('latency_seconds', 0)
                    query_count += 1
                    
                    print("\n📊 Performance Metrics:")
                    print(f"   ├─ Tokens: {metrics.get('total_tokens', 0)} total "
                          f"({metrics.get('input_tokens', 0)} input, "
                          f"{metrics.get('output_tokens', 0)} output)")
                    print(f"   ├─ Latency: {metrics.get('latency_seconds', 0)} seconds")
                    print(f"   ├─ Throughput: {metrics.get('throughput_tokens_per_second', 0):.0f} tokens/second")
                    print(f"   ├─ Model: {metrics.get('model', 'unknown')}")
                    print(f"   └─ Cycles: {metrics.get('cycles', 0)}")
            else:
                all_passed &= False
        
        # Test Langfuse if configured
        self.test_langfuse_connectivity()
        
        # Performance Summary
        if query_count > 0:
            print("\n📊 Performance Summary")
            print("=" * 50)
            print(f"Total queries processed: {query_count}")
            print(f"Total tokens used: {total_tokens:,}")
            print(f"Average tokens per query: {total_tokens // query_count:,}")
            print(f"Total model processing time: {total_latency:.1f} seconds")
            print(f"Average latency per query: {total_latency / query_count:.1f} seconds")
            if total_latency > 0:
                print(f"Overall throughput: {total_tokens / total_latency:.0f} tokens/second")
        
        # Summary
        print("\n" + "=" * 50)
        if all_passed:
            print("✅ All tests passed!")
            print(f"\n📚 API Documentation: {base_url}/docs")
            if self.langfuse_host and self.langfuse_public_key:
                print(f"📊 Langfuse Dashboard: {self.langfuse_host}")
        else:
            print("❌ Some tests failed")
        
        return all_passed


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Strands Weather Agent deployment")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    
    args = parser.parse_args()
    
    tester = ServiceTester(args.region)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()