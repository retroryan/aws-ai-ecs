#!/usr/bin/env python3
"""
CloudWatch Logs Viewer for Strands Weather Agent.
View and tail logs from deployed ECS services.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

import click
import boto3
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils import log_info, log_warn, log_error, get_aws_region
from utils.aws_utils import aws_utils


console = Console()


class LogViewer:
    """CloudWatch logs viewer for ECS services"""
    
    def __init__(self, region: str):
        self.region = region
        self.logs = aws_utils.get_client('logs', region)
        self.log_group_prefix = "/ecs/strands-weather-agent"
        
    def list_log_groups(self) -> List[str]:
        """List available log groups"""
        try:
            response = self.logs.describe_log_groups(
                logGroupNamePrefix=self.log_group_prefix
            )
            return [lg['logGroupName'] for lg in response.get('logGroups', [])]
        except Exception as e:
            log_error(f"Failed to list log groups: {e}")
            return []
    
    def get_log_streams(self, log_group: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent log streams for a log group"""
        try:
            response = self.logs.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=limit
            )
            return response.get('logStreams', [])
        except Exception as e:
            log_error(f"Failed to get log streams: {e}")
            return []
    
    def tail_logs(self, log_group: str, follow: bool = True, 
                  filter_pattern: Optional[str] = None,
                  start_time: Optional[datetime] = None):
        """Tail logs from a log group"""
        
        if not start_time:
            start_time = datetime.now() - timedelta(minutes=5)
        
        console.print(f"📋 Tailing logs from: {log_group}", style="bold cyan")
        if filter_pattern:
            console.print(f"🔍 Filter: {filter_pattern}", style="yellow")
        console.print("Press Ctrl+C to stop", style="dim")
        console.print("-" * 80)
        
        last_token = None
        seen_events = set()
        
        try:
            while True:
                kwargs = {
                    'logGroupName': log_group,
                    'startTime': int(start_time.timestamp() * 1000),
                    'interleaved': True
                }
                
                if filter_pattern:
                    kwargs['filterPattern'] = filter_pattern
                
                if last_token:
                    kwargs['nextToken'] = last_token
                
                try:
                    response = self.logs.filter_log_events(**kwargs)
                    
                    events = response.get('events', [])
                    
                    # Filter out already seen events
                    new_events = []
                    for event in events:
                        event_id = f"{event['timestamp']}-{event['message']}"
                        if event_id not in seen_events:
                            seen_events.add(event_id)
                            new_events.append(event)
                    
                    # Display new events
                    for event in sorted(new_events, key=lambda x: x['timestamp']):
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].rstrip()
                        
                        # Color based on log level
                        if 'ERROR' in message or 'Exception' in message:
                            style = "red"
                        elif 'WARN' in message:
                            style = "yellow"
                        elif 'DEBUG' in message:
                            style = "dim"
                        else:
                            style = "white"
                        
                        console.print(f"[{timestamp.strftime('%H:%M:%S')}] {message}", 
                                    style=style)
                    
                    # Update token for pagination
                    last_token = response.get('nextToken')
                    
                    # Update start time for next iteration
                    if new_events:
                        start_time = datetime.fromtimestamp(
                            new_events[-1]['timestamp'] / 1000
                        )
                
                except Exception as e:
                    if 'ThrottlingException' in str(e):
                        time.sleep(1)
                    else:
                        log_error(f"Error fetching logs: {e}")
                        break
                
                if not follow:
                    break
                
                time.sleep(2)  # Poll interval
                
        except KeyboardInterrupt:
            console.print("\n✋ Stopped tailing logs", style="yellow")
    
    def get_recent_logs(self, log_group: str, lines: int = 100,
                       since: Optional[str] = None,
                       filter_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        
        # Parse time range
        if since:
            if since.endswith('h'):
                hours = int(since[:-1])
                start_time = datetime.now() - timedelta(hours=hours)
            elif since.endswith('m'):
                minutes = int(since[:-1])
                start_time = datetime.now() - timedelta(minutes=minutes)
            elif since.endswith('d'):
                days = int(since[:-1])
                start_time = datetime.now() - timedelta(days=days)
            else:
                start_time = datetime.now() - timedelta(hours=1)
        else:
            start_time = datetime.now() - timedelta(hours=1)
        
        kwargs = {
            'logGroupName': log_group,
            'startTime': int(start_time.timestamp() * 1000),
            'limit': lines,
            'interleaved': True
        }
        
        if filter_pattern:
            kwargs['filterPattern'] = filter_pattern
        
        try:
            response = self.logs.filter_log_events(**kwargs)
            return response.get('events', [])
        except Exception as e:
            log_error(f"Failed to get logs: {e}")
            return []
    
    def export_logs(self, log_group: str, output_file: str,
                   since: Optional[str] = None,
                   filter_pattern: Optional[str] = None):
        """Export logs to a file"""
        
        console.print(f"📥 Exporting logs to: {output_file}", style="cyan")
        
        events = self.get_recent_logs(
            log_group, 
            lines=10000,  # Get more for export
            since=since,
            filter_pattern=filter_pattern
        )
        
        with open(output_file, 'w') as f:
            for event in sorted(events, key=lambda x: x['timestamp']):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].rstrip()
                f.write(f"[{timestamp.isoformat()}] {message}\n")
        
        console.print(f"✅ Exported {len(events)} log entries", style="green")


def get_service_log_group(service: Optional[str]) -> str:
    """Get log group name for a service"""
    if service:
        return f"/ecs/strands-weather-agent-{service}"
    return "/ecs/strands-weather-agent"


@click.command()
@click.option('--tail', '-t', is_flag=True, help='Tail logs in real-time')
@click.option('--follow', '-f', is_flag=True, help='Follow log output (same as --tail)')
@click.option('--service', '-s', type=click.Choice(['main', 'forecast', 'historical', 'agricultural', 'all']),
              help='Service to view logs for')
@click.option('--filter', '-F', 'filter_pattern', help='Filter pattern for logs')
@click.option('--since', help='Time range (e.g., 1h, 30m, 2d)')
@click.option('--lines', '-n', default=100, help='Number of lines to show')
@click.option('--export', 'export_file', help='Export logs to file')
@click.option('--region', help='AWS region', default=None)
@click.option('--list', 'list_groups', is_flag=True, help='List available log groups')
def main(tail: bool, follow: bool, service: Optional[str], 
         filter_pattern: Optional[str], since: Optional[str],
         lines: int, export_file: Optional[str], region: Optional[str],
         list_groups: bool):
    """View and tail CloudWatch logs for Strands Weather Agent services."""
    
    # Get region
    region = region or get_aws_region()
    viewer = LogViewer(region)
    
    # List log groups if requested
    if list_groups:
        console.print("📋 Available log groups:", style="bold cyan")
        groups = viewer.list_log_groups()
        for group in groups:
            console.print(f"  - {group}")
        return
    
    # Determine if we're tailing
    is_tail = tail or follow
    
    # Handle service selection
    if service == 'all':
        # View logs from all services
        log_groups = viewer.list_log_groups()
    else:
        log_group = get_service_log_group(service)
        log_groups = [log_group]
    
    # Validate log groups exist
    available_groups = viewer.list_log_groups()
    log_groups = [lg for lg in log_groups if lg in available_groups]
    
    if not log_groups:
        console.print("❌ No log groups found. Make sure services are deployed.", style="red")
        console.print("Available log groups:", style="yellow")
        for group in available_groups:
            console.print(f"  - {group}")
        return
    
    # Export logs if requested
    if export_file:
        for log_group in log_groups:
            output_file = export_file
            if len(log_groups) > 1:
                # Add service name to filename for multiple services
                service_name = log_group.split('-')[-1]
                base, ext = Path(export_file).stem, Path(export_file).suffix
                output_file = f"{base}_{service_name}{ext}"
            
            viewer.export_logs(log_group, output_file, since, filter_pattern)
        return
    
    # Tail or show recent logs
    if is_tail:
        # Can only tail one log group at a time
        if len(log_groups) > 1:
            console.print("⚠️  Can only tail one service at a time. Tailing 'main' service.", 
                         style="yellow")
            log_group = get_service_log_group('main')
        else:
            log_group = log_groups[0]
        
        viewer.tail_logs(log_group, follow=True, filter_pattern=filter_pattern)
    else:
        # Show recent logs
        for log_group in log_groups:
            console.print(f"\n📋 Logs from: {log_group}", style="bold cyan")
            console.print("-" * 80)
            
            events = viewer.get_recent_logs(
                log_group, 
                lines=lines, 
                since=since,
                filter_pattern=filter_pattern
            )
            
            if not events:
                console.print("No log entries found", style="dim")
                continue
            
            for event in sorted(events, key=lambda x: x['timestamp']):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].rstrip()
                
                # Color based on log level
                if 'ERROR' in message or 'Exception' in message:
                    style = "red"
                elif 'WARN' in message:
                    style = "yellow"
                elif 'DEBUG' in message:
                    style = "dim"
                else:
                    style = "white"
                
                console.print(f"[{timestamp.strftime('%H:%M:%S')}] {message}", 
                            style=style)


if __name__ == '__main__':
    main()