#!/usr/bin/env python3
"""
Check deployment status for Strands Weather Agent infrastructure.
"""

import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import click
import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from infrastructure.config import get_config
from infrastructure.utils.logging import log_info, log_warn, log_error, print_section
from infrastructure.utils.console import spinner, print_success, print_error, print_warning
from infrastructure.aws.ecs import ECSUtils


console = Console()


class DeploymentStatus:
    """Check deployment status and health."""
    
    def __init__(self):
        """Initialize status checker."""
        self.config = get_config()
        self.region = self.config.aws.region
        self.ecs_utils = ECSUtils(self.region)
        
        # Initialize boto3 clients
        self.cfn = boto3.client('cloudformation', region_name=self.region)
        self.ecs = boto3.client('ecs', region_name=self.region)
        self.logs = boto3.client('logs', region_name=self.region)
    
    def get_stack_info(self, stack_name: str) -> Dict[str, Any]:
        """Get CloudFormation stack information."""
        try:
            response = self.cfn.describe_stacks(StackName=stack_name)
            if response['Stacks']:
                stack = response['Stacks'][0]
                outputs = {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])}
                return {
                    'status': stack['StackStatus'],
                    'outputs': outputs,
                    'exists': True
                }
        except ClientError as e:
            if 'does not exist' in str(e):
                return {'exists': False, 'status': 'NOT_DEPLOYED'}
            raise
        
        return {'exists': False, 'status': 'ERROR'}
    
    def get_service_status(self, cluster_name: str, service_name: str) -> Dict[str, Any]:
        """Get ECS service status."""
        try:
            response = self.ecs.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            if response['services']:
                service = response['services'][0]
                return {
                    'desired': service.get('desiredCount', 0),
                    'running': service.get('runningCount', 0),
                    'pending': service.get('pendingCount', 0),
                    'status': service.get('status', 'UNKNOWN')
                }
        except Exception:
            pass
        
        return {'status': 'NOT_FOUND', 'desired': 0, 'running': 0, 'pending': 0}
    
    def count_stopped_tasks(self, cluster_name: str, service_name: str) -> int:
        """Count recently stopped tasks for a service."""
        try:
            response = self.ecs.list_tasks(
                cluster=cluster_name,
                serviceName=service_name,
                desiredStatus='STOPPED',
                maxResults=10
            )
            return len(response.get('taskArns', []))
        except Exception:
            return 0
    
    def check_recent_errors(self, log_group: str, minutes: int = 5) -> int:
        """Check for recent errors in CloudWatch logs."""
        try:
            start_time = datetime.now() - timedelta(minutes=minutes)
            response = self.logs.filter_log_events(
                logGroupName=log_group,
                startTime=int(start_time.timestamp() * 1000),
                filterPattern='ERROR'
            )
            return len(response.get('events', []))
        except Exception:
            return -1  # Indicates error checking logs
    
    def test_health_endpoint(self, lb_dns: str) -> tuple[bool, str]:
        """Test the health endpoint."""
        import requests
        
        try:
            response = requests.get(f"http://{lb_dns}/health", timeout=5)
            return response.status_code == 200, str(response.status_code)
        except Exception as e:
            return False, str(e)
    
    def display_base_stack_status(self):
        """Display base infrastructure stack status."""
        print_section("Base Infrastructure Stack")
        
        stack_info = self.get_stack_info(self.config.stacks.base_stack_name)
        
        if not stack_info['exists']:
            console.print("  Status: [red]NOT DEPLOYED[/red]")
            return None
        
        status = stack_info['status']
        status_color = 'green' if 'COMPLETE' in status else 'yellow'
        console.print(f"  Status: [{status_color}]{status}[/{status_color}]")
        
        if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
            outputs = stack_info['outputs']
            lb_dns = outputs.get('ALBDNSName', 'N/A')
            vpc_id = outputs.get('VPCId', 'N/A')
            cluster_name = outputs.get('ClusterName', 'N/A')
            
            console.print(f"  Load Balancer: [cyan]http://{lb_dns}[/cyan]")
            console.print(f"  VPC ID: {vpc_id}")
            console.print(f"  ECS Cluster: {cluster_name}")
            
            return {
                'lb_dns': lb_dns,
                'cluster_name': cluster_name,
                'outputs': outputs
            }
        
        return None
    
    def display_services_stack_status(self, base_info: Optional[Dict[str, Any]]):
        """Display services stack status."""
        print_section("Services Stack")
        
        stack_info = self.get_stack_info(self.config.stacks.services_stack_name)
        
        if not stack_info['exists']:
            console.print("  Status: [red]NOT DEPLOYED[/red]")
            return None
        
        status = stack_info['status']
        status_color = 'green' if 'COMPLETE' in status else 'yellow'
        console.print(f"  Status: [{status_color}]{status}[/{status_color}]")
        
        if status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE'] and base_info:
            outputs = stack_info['outputs']
            cluster_name = base_info['cluster_name']
            
            # Get service names
            services = {
                'Weather Agent': outputs.get('MainServiceName', f"{self.config.stacks.services_stack_name}-main"),
                'Weather Server': outputs.get('WeatherServiceName', f"{self.config.stacks.services_stack_name}-weather")
            }
            
            # Display ECS Services Status
            print_section("ECS Services Status")
            
            table = Table(show_header=True, header_style="bold")
            table.add_column("Service", style="cyan")
            table.add_column("Status")
            table.add_column("Desired", justify="center")
            table.add_column("Running", justify="center")
            table.add_column("Pending", justify="center")
            table.add_column("Stopped", justify="center")
            
            for service_name, service_arn in services.items():
                status = self.get_service_status(cluster_name, service_arn)
                stopped = self.count_stopped_tasks(cluster_name, service_arn)
                
                # Determine status color
                if status['running'] == status['desired'] and status['desired'] > 0:
                    status_color = "green"
                    status_text = "HEALTHY"
                elif status['running'] > 0:
                    status_color = "yellow"
                    status_text = "PARTIAL"
                else:
                    status_color = "red"
                    status_text = "UNHEALTHY"
                
                table.add_row(
                    service_name,
                    f"[{status_color}]{status_text}[/{status_color}]",
                    str(status['desired']),
                    str(status['running']),
                    str(status['pending']),
                    str(stopped) if stopped > 0 else "-"
                )
            
            console.print(table)
            
            # Check health endpoint
            if base_info and 'lb_dns' in base_info:
                print_section("Service Health Check")
                
                with spinner("Testing weather agent endpoint..."):
                    healthy, status_code = self.test_health_endpoint(base_info['lb_dns'])
                
                if healthy:
                    console.print("  Weather Agent: [green]HEALTHY[/green] ✓")
                else:
                    console.print(f"  Weather Agent: [red]UNHEALTHY[/red] ({status_code})")
                
                console.print("\n  MCP Server: Internal service (not exposed via Load Balancer)")
                console.print("  Access via Service Connect:")
                console.print(f"    - Weather Server: weather.{self.config.stacks.base_stack_name}:7778")
            
            # Check recent errors
            print_section("Recent Log Errors (last 5 minutes)")
            
            log_groups = {
                'Weather Agent': outputs.get('MainLogGroup', '/ecs/strands-weather-agent-main'),
                'Weather Server': outputs.get('WeatherLogGroup', '/ecs/strands-weather-agent-weather')
            }
            
            for service_name, log_group in log_groups.items():
                error_count = self.check_recent_errors(log_group)
                if error_count > 0:
                    console.print(f"  {service_name}: [red]{error_count} errors found[/red]")
                elif error_count == 0:
                    console.print(f"  {service_name}: [green]No errors[/green]")
                else:
                    console.print(f"  {service_name}: [yellow]Unable to check logs[/yellow]")
            
            return {
                'services': services,
                'log_groups': log_groups,
                'lb_dns': base_info.get('lb_dns')
            }
        
        return None
    
    def display_next_steps(self, deployment_info: Optional[Dict[str, Any]]):
        """Display next steps for the user."""
        print_section("Next Steps")
        
        if deployment_info and 'lb_dns' in deployment_info:
            lb_dns = deployment_info['lb_dns']
            
            console.print("Test the API:")
            console.print(f'  curl -X POST "http://{lb_dns}/query" \\')
            console.print('      -H "Content-Type: application/json" \\')
            console.print('      -d \'{"query": "What is the weather in Chicago?"}\'')
            console.print()
            
            console.print("Test health endpoint:")
            console.print(f'  curl "http://{lb_dns}/health"')
            console.print()
            
            if 'log_groups' in deployment_info:
                console.print("View logs:")
                for service, log_group in deployment_info['log_groups'].items():
                    console.print(f"  aws logs tail {log_group} --follow")
        else:
            console.print("Deploy the infrastructure first:")
            console.print("  python deploy.py all")
    
    def run(self):
        """Run the status check."""
        log_info(f"Checking infrastructure status in region: {self.region}")
        
        # Check base stack
        base_info = self.display_base_stack_status()
        
        # Check services stack
        services_info = self.display_services_stack_status(base_info)
        
        # Display next steps
        deployment_info = {}
        if base_info:
            deployment_info.update(base_info)
        if services_info:
            deployment_info.update(services_info)
        
        self.display_next_steps(deployment_info)


@click.command()
@click.option('--region', help='AWS region', envvar='AWS_REGION')
def main(region: Optional[str] = None):
    """Check deployment status for Strands Weather Agent infrastructure."""
    try:
        # Override region if provided
        if region:
            config = get_config()
            config.aws.region = region
        
        status_checker = DeploymentStatus()
        status_checker.run()
        
    except KeyboardInterrupt:
        print_warning("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Status check failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()