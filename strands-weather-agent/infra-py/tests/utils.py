"""
Shared utilities for Strands Weather Agent tests.
"""

import time
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from tests.config import config


console = Console()


class AWSClientManager:
    """Manages AWS client instances with caching."""
    
    def __init__(self, region: Optional[str] = None):
        self.region = region or config.aws.region
        self._clients: Dict[str, Any] = {}
    
    def get_client(self, service: str) -> Any:
        """Get or create an AWS client for the specified service."""
        if service not in self._clients:
            self._clients[service] = boto3.client(
                service,
                region_name=self.region
            )
        return self._clients[service]
    
    @property
    def cfn(self):
        """CloudFormation client."""
        return self.get_client('cloudformation')
    
    @property
    def ecs(self):
        """ECS client."""
        return self.get_client('ecs')
    
    @property
    def logs(self):
        """CloudWatch Logs client."""
        return self.get_client('logs')


def get_stack_output(client_manager: AWSClientManager, stack_name: str, 
                    output_key: str) -> Optional[str]:
    """Get a specific output value from a CloudFormation stack."""
    try:
        response = client_manager.cfn.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        
        for output in stack.get('Outputs', []):
            if output['OutputKey'] == output_key:
                return output['OutputValue']
        
        return None
    except ClientError as e:
        if 'does not exist' in str(e):
            console.print(f"❌ Stack '{stack_name}' not found", style="red")
        else:
            console.print(f"❌ Error accessing stack: {e}", style="red")
        return None


def get_alb_url(client_manager: AWSClientManager) -> Optional[str]:
    """Get the ALB URL from CloudFormation stack."""
    if config.api_url_override:
        return config.api_url_override
    
    dns_name = get_stack_output(
        client_manager,
        config.aws.base_stack_name,
        'ALBDNSName'
    )
    
    if dns_name:
        return f"http://{dns_name}"
    return None


def check_service_health(client_manager: AWSClientManager, 
                        service_name: str) -> Tuple[bool, str]:
    """Check if an ECS service is healthy."""
    try:
        response = client_manager.ecs.describe_services(
            cluster=config.aws.cluster_name,
            services=[service_name]
        )
        
        if not response['services']:
            return False, "Service not found"
        
        service = response['services'][0]
        running = service['runningCount']
        desired = service['desiredCount']
        
        if running == desired and desired > 0:
            return True, f"{running}/{desired} tasks running"
        else:
            return False, f"{running}/{desired} tasks running"
            
    except Exception as e:
        return False, str(e)


def wait_for_services_healthy(client_manager: AWSClientManager,
                             timeout: int = None) -> bool:
    """Wait for all services to become healthy."""
    timeout = timeout or config.timeouts.service_startup_wait
    start_time = time.time()
    
    console.print(f"⏳ Waiting up to {timeout}s for services to be healthy...", style="cyan")
    
    while time.time() - start_time < timeout:
        all_healthy = True
        unhealthy_services = []
        
        for service in config.services.all_services:
            healthy, status = check_service_health(client_manager, service)
            if not healthy:
                all_healthy = False
                unhealthy_services.append(f"{service}: {status}")
        
        if all_healthy:
            console.print("✅ All services are healthy!", style="green")
            return True
        
        # Show progress
        elapsed = int(time.time() - start_time)
        console.print(f"[{elapsed}s] Waiting... Unhealthy: {', '.join(unhealthy_services)}", 
                     style="dim")
        time.sleep(5)
    
    console.print("❌ Timeout waiting for services to be healthy", style="red")
    return False


def format_metrics(metrics: Dict[str, Any]) -> Table:
    """Format performance metrics as a rich table."""
    table = Table(title="Performance Metrics", box=None)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    if metrics:
        table.add_row("Total Tokens", str(metrics.get('total_tokens', 0)))
        table.add_row("Input Tokens", str(metrics.get('input_tokens', 0)))
        table.add_row("Output Tokens", str(metrics.get('output_tokens', 0)))
        table.add_row("Latency", f"{metrics.get('latency_seconds', 0):.2f}s")
        table.add_row("Throughput", f"{metrics.get('throughput_tokens_per_second', 0):.0f} tokens/s")
        table.add_row("Model", metrics.get('model', 'unknown'))
        table.add_row("Cycles", str(metrics.get('cycles', 0)))
    
    return table


def check_langfuse_logs(client_manager: AWSClientManager, 
                       minutes: int = 5) -> Tuple[bool, int]:
    """Check CloudWatch logs for recent Langfuse activity."""
    try:
        start_time = int((time.time() - minutes * 60) * 1000)
        
        response = client_manager.logs.filter_log_events(
            logGroupName=f"{config.services.log_group_prefix}-main",
            filterPattern="langfuse",
            startTime=start_time
        )
        
        event_count = len(response.get('events', []))
        return event_count > 0, event_count
        
    except Exception:
        return False, 0


def print_test_header(title: str):
    """Print a formatted test section header."""
    console.print(f"\n{'='*50}")
    console.print(f"🧪 {title}", style="bold cyan")
    console.print('='*50)


def print_test_summary(passed: int, failed: int, duration: float):
    """Print test execution summary."""
    total = passed + failed
    console.print(f"\n{'='*50}")
    console.print("📊 Test Summary", style="bold cyan")
    console.print('='*50)
    console.print(f"Total Tests: {total}")
    console.print(f"Passed: {passed}", style="green")
    console.print(f"Failed: {failed}", style="red" if failed > 0 else "dim")
    console.print(f"Duration: {duration:.2f}s")
    
    if failed == 0:
        console.print("\n✅ All tests passed!", style="green bold")
    else:
        console.print(f"\n❌ {failed} test(s) failed", style="red bold")


def get_recent_logs(client_manager: AWSClientManager, 
                   service: str, 
                   lines: int = 20) -> List[str]:
    """Get recent log entries for a service."""
    try:
        log_group = config.services.get_log_group(service)
        
        response = client_manager.logs.filter_log_events(
            logGroupName=log_group,
            limit=lines,
            interleaved=True
        )
        
        return [event['message'] for event in response.get('events', [])]
        
    except Exception:
        return []