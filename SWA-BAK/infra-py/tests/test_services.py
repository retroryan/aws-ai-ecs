#!/usr/bin/env python3
"""
Service Integration Tests for Strands Weather Agent.
Tests the deployed services, ALB, and ECS infrastructure.
"""

import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import argparse

import requests
from rich.console import Console
from rich.panel import Panel

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tests.config import config
from tests.utils import (
    AWSClientManager,
    get_alb_url,
    check_service_health,
    wait_for_services_healthy,
    format_metrics,
    check_langfuse_logs,
    print_test_header,
    print_test_summary,
    get_recent_logs
)


console = Console()


class ServiceTester:
    """Test deployed services and telemetry."""
    
    def __init__(self, region: Optional[str] = None):
        self.region = region or config.aws.region
        self.aws = AWSClientManager(self.region)
        self.base_url: Optional[str] = None
        self.results: Dict[str, bool] = {}
        self.metrics_summary: List[Dict[str, Any]] = []
        
    def setup(self) -> bool:
        """Setup test environment and get ALB URL."""
        print_test_header("Test Setup")
        
        # Get ALB URL
        self.base_url = get_alb_url(self.aws)
        if not self.base_url:
            console.print("❌ Cannot get ALB URL. Is the infrastructure deployed?", style="red")
            return False
        
        console.print(f"🌐 Testing against: {self.base_url}", style="cyan")
        
        # Wait for services to be healthy
        if not wait_for_services_healthy(self.aws):
            console.print("⚠️  Services not fully healthy, but continuing tests...", style="yellow")
        
        return True
    
    def test_health_endpoint(self) -> bool:
        """Test the health endpoint."""
        print_test_header("Health Endpoint Test")
        
        try:
            resp = requests.get(
                f"{self.base_url}/health", 
                timeout=config.timeouts.health_check_timeout
            )
            
            if resp.status_code == 200:
                health_data = resp.json()
                console.print(f"✅ Health check passed", style="green")
                console.print(f"Response: {json.dumps(health_data, indent=2)}", style="dim")
                self.results['health'] = True
                return True
            else:
                console.print(f"❌ Health check failed: {resp.status_code}", style="red")
                self.results['health'] = False
                return False
                
        except Exception as e:
            console.print(f"❌ Health check error: {e}", style="red")
            self.results['health'] = False
            return False
    
    def test_mcp_status(self) -> bool:
        """Test MCP server connectivity."""
        print_test_header("MCP Server Status Test")
        
        try:
            resp = requests.get(
                f"{self.base_url}/mcp/status",
                timeout=config.timeouts.health_check_timeout
            )
            
            if resp.status_code == 200:
                status = resp.json()
                connected = status.get('connected_count', 0)
                total = status.get('total_count', 0)
                
                console.print(f"MCP Servers: {connected}/{total} connected", 
                             style="green" if connected == total else "yellow")
                
                # Show individual server status
                servers = status.get('servers', {})
                for server, is_connected in servers.items():
                    emoji = "✅" if is_connected else "❌"
                    console.print(f"  {emoji} {server}: {'connected' if is_connected else 'disconnected'}")
                
                self.results['mcp_status'] = connected > 0
                return connected > 0
            else:
                console.print(f"❌ MCP status failed: {resp.status_code}", style="red")
                self.results['mcp_status'] = False
                return False
                
        except Exception as e:
            console.print(f"❌ MCP status error: {e}", style="red")
            self.results['mcp_status'] = False
            return False
    
    def test_query(self, query_info: Dict[str, str]) -> bool:
        """Test a single query."""
        query = query_info['query']
        description = query_info.get('description', '')
        
        console.print(f"\n📝 {description}", style="dim")
        console.print(f"Query: '{query}'", style="cyan")
        
        try:
            start_time = time.time()
            resp = requests.post(
                f"{self.base_url}/query",
                json={"query": query},
                timeout=config.timeouts.query_timeout
            )
            elapsed = time.time() - start_time
            
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get('response', '')
                
                # Truncate long responses for display
                if len(response_text) > 200:
                    display_text = response_text[:200] + "..."
                else:
                    display_text = response_text
                
                console.print(f"✅ Response: {display_text}", style="green")
                
                # Show session ID if available
                if 'session_id' in data:
                    console.print(f"Session ID: {data['session_id']}", style="dim")
                
                # Collect and display metrics
                if 'metrics' in data and data['metrics']:
                    metrics = data['metrics']
                    metrics['query'] = query
                    metrics['elapsed_time'] = elapsed
                    self.metrics_summary.append(metrics)
                    
                    if config.verbose:
                        console.print(format_metrics(metrics))
                
                # Show trace URL if available
                if 'trace_url' in data and data['trace_url']:
                    console.print(f"🔗 Trace: {data['trace_url']}", style="blue")
                
                return True
            else:
                console.print(f"❌ Query failed: {resp.status_code}", style="red")
                if config.verbose and resp.text:
                    console.print(f"Error: {resp.text}", style="red dim")
                return False
                
        except Exception as e:
            console.print(f"❌ Query error: {e}", style="red")
            return False
    
    def test_queries(self) -> bool:
        """Test multiple queries."""
        print_test_header("Query Tests")
        
        queries_to_test = config.queries.basic_queries
        if config.verbose:
            queries_to_test.extend(config.queries.stress_queries)
        
        passed = 0
        failed = 0
        
        for query_info in queries_to_test:
            if self.test_query(query_info):
                passed += 1
            else:
                failed += 1
                if config.fail_fast:
                    break
        
        self.results['queries'] = failed == 0
        console.print(f"\nQuery Results: {passed} passed, {failed} failed", 
                     style="green" if failed == 0 else "red")
        
        return failed == 0
    
    def test_ecs_services(self) -> bool:
        """Check ECS service status."""
        print_test_header("ECS Service Status")
        
        all_healthy = True
        
        for service in config.services.all_services:
            healthy, status = check_service_health(self.aws, service)
            emoji = "✅" if healthy else "❌"
            style = "green" if healthy else "red"
            
            console.print(f"{emoji} {service}: {status}", style=style)
            
            if not healthy:
                all_healthy = False
                # Show recent logs for unhealthy services
                if config.verbose:
                    logs = get_recent_logs(self.aws, service, lines=5)
                    if logs:
                        console.print("  Recent logs:", style="dim")
                        for log in logs:
                            console.print(f"    {log[:100]}...", style="dim")
        
        self.results['ecs_services'] = all_healthy
        return all_healthy
    
    def test_langfuse_integration(self) -> bool:
        """Test Langfuse telemetry integration."""
        if config.skip_langfuse:
            console.print("\n⏭️  Skipping Langfuse tests (TEST_SKIP_LANGFUSE=true)", style="yellow")
            return True
        
        print_test_header("Langfuse Telemetry Integration")
        
        if not config.langfuse.is_configured:
            console.print("⚠️  Langfuse not configured (missing LANGFUSE_HOST or LANGFUSE_PUBLIC_KEY)", 
                         style="yellow")
            self.results['langfuse'] = None  # Not tested
            return True
        
        console.print(f"Langfuse Host: {config.langfuse.host}", style="cyan")
        
        # Check if telemetry is enabled in deployment
        try:
            stack = self.aws.cfn.describe_stacks(
                StackName=config.aws.services_stack_name
            )['Stacks'][0]
            
            telemetry_enabled = False
            for param in stack['Parameters']:
                if param['ParameterKey'] == 'EnableTelemetry' and param['ParameterValue'] == 'true':
                    telemetry_enabled = True
                    break
            
            if telemetry_enabled:
                console.print("✅ Telemetry is enabled in deployment", style="green")
                
                # Check for recent Langfuse activity in logs
                has_activity, event_count = check_langfuse_logs(self.aws)
                
                if has_activity:
                    console.print(f"✅ Found {event_count} Langfuse events in recent logs", 
                                 style="green")
                    console.print(f"\n📈 Visit your Langfuse dashboard: {config.langfuse.host}", 
                                 style="cyan")
                    self.results['langfuse'] = True
                else:
                    console.print("⚠️  No recent Langfuse activity (run some queries first)", 
                                 style="yellow")
                    self.results['langfuse'] = False
            else:
                console.print("⚠️  Telemetry is disabled in deployment", style="yellow")
                self.results['langfuse'] = False
                
        except Exception as e:
            console.print(f"❌ Could not check deployment status: {e}", style="red")
            self.results['langfuse'] = False
            return False
        
        return True
    
    def show_performance_summary(self):
        """Display aggregated performance metrics."""
        if not self.metrics_summary:
            return
        
        print_test_header("Performance Summary")
        
        total_tokens = sum(m.get('total_tokens', 0) for m in self.metrics_summary)
        total_latency = sum(m.get('latency_seconds', 0) for m in self.metrics_summary)
        query_count = len(self.metrics_summary)
        
        summary = f"""
Total queries: {query_count}
Total tokens: {total_tokens:,}
Average tokens/query: {total_tokens // query_count:,}
Total latency: {total_latency:.1f}s
Average latency/query: {total_latency / query_count:.1f}s
"""
        
        if total_latency > 0:
            summary += f"Overall throughput: {total_tokens / total_latency:.0f} tokens/s\n"
        
        console.print(Panel(summary.strip(), title="Metrics", border_style="cyan"))
    
    def run_all_tests(self) -> bool:
        """Run all tests."""
        start_time = time.time()
        
        console.print("🧪 Strands Weather Agent Service Tests", style="bold cyan")
        console.print(f"Region: {self.region}", style="dim")
        console.print(f"Verbose: {config.verbose}", style="dim")
        console.print()
        
        # Setup
        if not self.setup():
            return False
        
        # Run tests
        tests = [
            self.test_health_endpoint,
            self.test_mcp_status,
            self.test_ecs_services,
            self.test_queries,
            self.test_langfuse_integration
        ]
        
        for test in tests:
            if not test() and config.fail_fast:
                console.print("\n⚠️  Stopping tests (fail-fast mode)", style="yellow")
                break
        
        # Show performance summary
        if self.metrics_summary:
            self.show_performance_summary()
        
        # Final summary
        duration = time.time() - start_time
        passed = sum(1 for v in self.results.values() if v is True)
        failed = sum(1 for v in self.results.values() if v is False)
        
        print_test_summary(passed, failed, duration)
        
        # Show additional info
        if config.api_url_override:
            console.print(f"\n📍 Tested custom URL: {config.api_url_override}", style="yellow")
        else:
            console.print(f"\n📚 API Documentation: {self.base_url}/docs", style="cyan")
        
        return failed == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test Strands Weather Agent deployment")
    parser.add_argument("--region", help="AWS region (overrides config)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose output")
    parser.add_argument("--fail-fast", action="store_true",
                       help="Stop on first failure")
    parser.add_argument("--skip-langfuse", action="store_true",
                       help="Skip Langfuse tests")
    parser.add_argument("--api-url", help="Override API URL (for local testing)")
    
    args = parser.parse_args()
    
    # Override config with command line args
    if args.verbose:
        config.verbose = True
    if args.fail_fast:
        config.fail_fast = True
    if args.skip_langfuse:
        config.skip_langfuse = True
    if args.api_url:
        config.api_url_override = args.api_url
    
    # Run tests
    tester = ServiceTester(args.region)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()