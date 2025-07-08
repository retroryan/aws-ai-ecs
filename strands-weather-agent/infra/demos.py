#!/usr/bin/env python3
"""
Interactive Demo Menu for Strands Weather Agent.
Provides a user-friendly menu to run various demonstration scripts.
"""

import sys
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.text import Text
from rich import box

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from utils import log_info, log_warn, log_error


console = Console()


class Demo:
    """Represents a demo script with metadata"""
    
    def __init__(self, name: str, file: str, description: str, 
                 requirements: List[str], features: List[str]):
        self.name = name
        self.file = file
        self.description = description
        self.requirements = requirements
        self.features = features


class DemoRunner:
    """Manages and runs demonstration scripts"""
    
    def __init__(self):
        self.demos = [
            Demo(
                name="Telemetry Demo",
                file="demos/demo_telemetry.py",
                description="Showcase Langfuse telemetry integration and performance metrics",
                requirements=[
                    "AWS deployment OR local services running",
                    "Optional: Langfuse credentials in cloud.env"
                ],
                features=[
                    "Real-time telemetry collection",
                    "Performance metrics display",
                    "Multi-query session tracking",
                    "Trace URL generation",
                    "Token usage and cost tracking"
                ]
            ),
            Demo(
                name="Multi-turn Conversation Demo",
                file="demos/multi-turn-demo.py",
                description="Demonstrate stateful multi-turn conversations with session persistence",
                requirements=[
                    "AWS deployment OR local services running",
                    "API_URL environment variable (optional)"
                ],
                features=[
                    "Session persistence across queries",
                    "Context retention demonstration",
                    "Interactive conversation flow",
                    "Performance tracking per turn",
                    "Colorized output for better readability"
                ]
            )
        ]
        
    def check_deployment_status(self) -> Dict[str, bool]:
        """Check if services are deployed"""
        status = {
            "aws": False,
            "local": False,
            "api_url": None
        }
        
        # Check AWS deployment
        try:
            import boto3
            cfn = boto3.client('cloudformation')
            
            # Check base stack
            try:
                base_stack = cfn.describe_stacks(StackName="strands-weather-agent-base")
                if base_stack['Stacks'][0]['StackStatus'] in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                    # Get ALB URL
                    for output in base_stack['Stacks'][0]['Outputs']:
                        if output['OutputKey'] == 'ALBDNSName':
                            status['api_url'] = f"http://{output['OutputValue']}"
                            status['aws'] = True
            except:
                pass
                
            # Check services stack
            try:
                services_stack = cfn.describe_stacks(StackName="strands-weather-agent-services")
                if services_stack['Stacks'][0]['StackStatus'] not in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
                    status['aws'] = False
            except:
                status['aws'] = False
                
        except:
            pass
        
        # Check local services
        try:
            import requests
            response = requests.get("http://localhost:7777/health", timeout=2)
            if response.status_code == 200:
                status['local'] = True
                if not status['api_url']:
                    status['api_url'] = "http://localhost:7777"
        except:
            pass
        
        return status
    
    def display_welcome(self):
        """Display welcome banner"""
        title = Text("Strands Weather Agent Demos", style="bold cyan")
        subtitle = Text("Interactive demonstrations of key features", style="dim")
        
        panel = Panel(
            Text.from_markup(
                f"[bold cyan]Strands Weather Agent Demos[/bold cyan]\n"
                f"[dim]Interactive demonstrations of key features[/dim]"
            ),
            box=box.DOUBLE,
            padding=(1, 2),
            style="cyan"
        )
        console.print(panel)
        console.print()
    
    def display_status(self, status: Dict[str, bool]):
        """Display deployment status"""
        console.print("📊 Deployment Status:", style="bold")
        
        if status['aws']:
            console.print("  ✅ AWS Deployment: Active", style="green")
            console.print(f"     URL: {status['api_url']}", style="dim")
        else:
            console.print("  ❌ AWS Deployment: Not found", style="red")
        
        if status['local']:
            console.print("  ✅ Local Services: Running", style="green")
            console.print("     URL: http://localhost:7777", style="dim")
        else:
            console.print("  ❌ Local Services: Not running", style="red")
        
        if not status['aws'] and not status['local']:
            console.print("\n⚠️  No services detected. Please deploy or start local services first.", 
                         style="yellow")
            console.print("  AWS: python deploy.py all", style="dim")
            console.print("  Local: Run start scripts in parent directory", style="dim")
        
        console.print()
    
    def display_menu(self) -> Optional[int]:
        """Display demo menu and get user selection"""
        table = Table(
            title="Available Demos",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        
        table.add_column("#", style="cyan", width=3)
        table.add_column("Demo Name", style="white")
        table.add_column("Description", style="dim")
        
        for i, demo in enumerate(self.demos, 1):
            table.add_row(
                str(i),
                demo.name,
                demo.description
            )
        
        console.print(table)
        console.print()
        
        # Get user choice
        choices = list(range(1, len(self.demos) + 1))
        choices_str = f"[1-{len(self.demos)}]"
        
        choice = IntPrompt.ask(
            f"Select a demo to run {choices_str} (0 to exit)",
            choices=choices + [0],
            show_choices=False
        )
        
        return choice if choice != 0 else None
    
    def display_demo_details(self, demo: Demo):
        """Display detailed information about a demo"""
        console.print(f"\n🎯 {demo.name}", style="bold cyan")
        console.print("=" * 50)
        
        console.print("\n📝 Description:", style="bold")
        console.print(f"   {demo.description}")
        
        console.print("\n📋 Requirements:", style="bold")
        for req in demo.requirements:
            console.print(f"   • {req}")
        
        console.print("\n✨ Features:", style="bold")
        for feature in demo.features:
            console.print(f"   • {feature}")
        
        console.print()
    
    def run_demo(self, demo: Demo, api_url: Optional[str] = None) -> bool:
        """Run a specific demo"""
        demo_path = Path(__file__).parent / demo.file
        
        if not demo_path.exists():
            console.print(f"❌ Demo file not found: {demo_path}", style="red")
            return False
        
        # Set API URL if available
        env = os.environ.copy()
        if api_url:
            env['API_URL'] = api_url
        
        console.print(f"\n🚀 Starting {demo.name}...", style="green")
        console.print("-" * 50)
        
        try:
            # Run the demo
            result = subprocess.run(
                [sys.executable, str(demo_path)],
                env=env,
                text=True
            )
            
            if result.returncode == 0:
                console.print(f"\n✅ {demo.name} completed successfully!", style="green")
                return True
            else:
                console.print(f"\n❌ {demo.name} failed with exit code {result.returncode}", 
                            style="red")
                return False
                
        except KeyboardInterrupt:
            console.print(f"\n⚠️  {demo.name} interrupted by user", style="yellow")
            return False
        except Exception as e:
            console.print(f"\n❌ Error running demo: {e}", style="red")
            return False
    
    def run_interactive(self):
        """Run interactive demo menu"""
        self.display_welcome()
        
        # Check deployment status
        status = self.check_deployment_status()
        self.display_status(status)
        
        # Main menu loop
        while True:
            choice = self.display_menu()
            
            if choice is None:
                console.print("\n👋 Exiting demo menu. Goodbye!", style="cyan")
                break
            
            # Get selected demo
            demo = self.demos[choice - 1]
            
            # Display demo details
            self.display_demo_details(demo)
            
            # Confirm running
            if Prompt.ask("Run this demo?", choices=["y", "n"], default="y") == "y":
                self.run_demo(demo, status.get('api_url'))
                
                # Ask if user wants to run another demo
                console.print()
                if Prompt.ask("Run another demo?", choices=["y", "n"], default="y") == "n":
                    console.print("\n👋 Thanks for trying the demos!", style="cyan")
                    break
            
            console.print()  # Add spacing before next menu


@click.command()
@click.option('--telemetry', is_flag=True, help='Run telemetry demo directly')
@click.option('--multi-turn', is_flag=True, help='Run multi-turn demo directly')
@click.option('--api-url', help='Override API URL for demos')
def main(telemetry: bool, multi_turn: bool, api_url: Optional[str]):
    """Interactive demo menu for Strands Weather Agent.
    
    Run without options for interactive menu, or use flags to run specific demos directly.
    """
    
    runner = DemoRunner()
    
    # Handle direct demo execution
    if telemetry:
        demo = runner.demos[0]  # Telemetry demo
        console.print(f"🚀 Running {demo.name} directly...", style="cyan")
        runner.run_demo(demo, api_url)
        return
    
    if multi_turn:
        demo = runner.demos[1]  # Multi-turn demo
        console.print(f"🚀 Running {demo.name} directly...", style="cyan")
        runner.run_demo(demo, api_url)
        return
    
    # Run interactive menu
    runner.run_interactive()


if __name__ == '__main__':
    import os
    main()