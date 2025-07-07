#!/usr/bin/env python3
"""
Run All Demos for Strands Weather Agent
This script runs all demos in sequence, showcasing the full capabilities
of the AWS Strands Weather Agent with comprehensive metrics and telemetry.
"""

import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports if needed
sys.path.append(str(Path(__file__).parent.parent))

# Color definitions
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    
    class Colors:
        GREEN = Fore.GREEN
        RED = Fore.RED
        YELLOW = Fore.YELLOW
        BLUE = Fore.BLUE
        CYAN = Fore.CYAN
        MAGENTA = Fore.MAGENTA
        RESET = Style.RESET_ALL
except ImportError:
    class Colors:
        GREEN = ""
        RED = ""
        YELLOW = ""
        BLUE = ""
        CYAN = ""
        MAGENTA = ""
        RESET = ""


class DemoRunner:
    """Run all demos for the Strands Weather Agent"""
    
    def __init__(self):
        self.demos_dir = Path(__file__).parent
        self.start_time = datetime.now()
        
    def print_header(self, text: str) -> None:
        """Print a formatted header"""
        print(f"\n{'=' * 80}")
        print(f"{Colors.MAGENTA}🚀 {text}{Colors.RESET}")
        print('=' * 80)
        
    def print_section(self, text: str) -> None:
        """Print a section header"""
        print(f"\n{Colors.CYAN}{'─' * 60}{Colors.RESET}")
        print(f"{Colors.CYAN}📌 {text}{Colors.RESET}")
        print(f"{Colors.CYAN}{'─' * 60}{Colors.RESET}")
        
    def check_environment(self) -> bool:
        """Check if environment is properly configured"""
        self.print_section("Environment Check")
        
        all_good = True
        
        # Check for cloud.env
        cloud_env_path = self.demos_dir.parent / "cloud.env"
        if cloud_env_path.exists():
            print(f"{Colors.GREEN}✓{Colors.RESET} cloud.env found")
            # Load it to check for Langfuse
            from dotenv import load_dotenv
            load_dotenv(cloud_env_path)
            
            if os.getenv("LANGFUSE_PUBLIC_KEY"):
                print(f"{Colors.GREEN}✓{Colors.RESET} Langfuse credentials configured")
            else:
                print(f"{Colors.YELLOW}⚠{Colors.RESET}  Langfuse credentials not configured (telemetry disabled)")
        else:
            print(f"{Colors.YELLOW}⚠{Colors.RESET}  cloud.env not found (telemetry will be disabled)")
        
        # Check for AWS credentials
        try:
            import boto3
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print(f"{Colors.GREEN}✓{Colors.RESET} AWS credentials configured")
            print(f"   Account: {identity['Account']}")
            print(f"   User/Role: {identity['Arn'].split('/')[-1]}")
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} AWS credentials not configured")
            print(f"   Error: {e}")
            all_good = False
        
        # Check for API availability
        api_url = os.getenv("API_URL", "http://localhost:7777")
        try:
            import requests
            resp = requests.get(f"{api_url}/health", timeout=5)
            if resp.status_code == 200:
                print(f"{Colors.GREEN}✓{Colors.RESET} API available at {api_url}")
            else:
                print(f"{Colors.YELLOW}⚠{Colors.RESET}  API returned status {resp.status_code}")
        except Exception:
            print(f"{Colors.YELLOW}⚠{Colors.RESET}  API not accessible at {api_url}")
            print("   (Demos will attempt to find deployed service)")
        
        return all_good
    
    def run_demo(self, script_name: str, description: str) -> bool:
        """Run a single demo script"""
        self.print_section(description)
        
        script_path = self.demos_dir / script_name
        if not script_path.exists():
            print(f"{Colors.RED}✗{Colors.RESET} Script not found: {script_name}")
            return False
        
        try:
            print(f"Running {script_name}...")
            print("")
            
            # Run the demo
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                print(f"\n{Colors.GREEN}✓{Colors.RESET} {description} completed successfully")
                return True
            else:
                print(f"\n{Colors.RED}✗{Colors.RESET} {description} failed with exit code {result.returncode}")
                return False
                
        except Exception as e:
            print(f"\n{Colors.RED}✗{Colors.RESET} Error running {script_name}: {e}")
            return False
    
    def run_all_demos(self) -> None:
        """Run all demos in sequence"""
        self.print_header("AWS Strands Weather Agent - Complete Demo Suite")
        
        print(f"\nStarting comprehensive demo at {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("\nThis demo suite will showcase:")
        print("  1. Multi-turn conversations with session management")
        print("  2. Telemetry integration with Langfuse")
        print("  3. Performance metrics and token usage")
        print("  4. MCP server integration")
        print("  5. Agricultural and weather forecasting capabilities")
        
        # Check environment
        if not self.check_environment():
            print(f"\n{Colors.YELLOW}⚠{Colors.RESET}  Some environment checks failed")
            print("Continue anyway? (y/n): ", end="")
            if input().lower() != 'y':
                print("Demo cancelled.")
                return
        
        # Run demos
        demos = [
            ("multi-turn-demo.py", "Multi-Turn Conversation Demo"),
            ("demo_telemetry.py", "Telemetry Integration Demo"),
        ]
        
        # Ask about performance benchmark
        print(f"\n{Colors.YELLOW}Include performance benchmark? This will run additional load tests (y/n): {Colors.RESET}", end="")
        if input().lower() == 'y':
            demos.append(("performance_benchmark.py", "Performance Benchmark Demo"))
        
        results = []
        for script, description in demos:
            # Add a pause between demos for clarity
            if results:
                print(f"\n{Colors.CYAN}Pausing for 3 seconds before next demo...{Colors.RESET}")
                time.sleep(3)
            
            success = self.run_demo(script, description)
            results.append((description, success))
        
        # Final summary
        self.print_header("Demo Suite Summary")
        
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print(f"\nTotal execution time: {duration:.1f} seconds")
        print(f"\nDemo Results:")
        
        all_passed = True
        for description, success in results:
            status = f"{Colors.GREEN}✓ PASSED{Colors.RESET}" if success else f"{Colors.RED}✗ FAILED{Colors.RESET}"
            print(f"  {status} - {description}")
            if not success:
                all_passed = False
        
        if all_passed:
            print(f"\n{Colors.GREEN}🎉 All demos completed successfully!{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Some demos failed. Check the output above for details.{Colors.RESET}")
        
        # Next steps
        print("\n📚 Next Steps:")
        print("  1. Check your Langfuse dashboard for telemetry traces")
        print("  2. Review the metrics summaries from each demo")
        print("  3. Try the API directly with the documentation")
        print("  4. Deploy to AWS for production testing")
        
        # Useful commands
        print("\n🛠️  Useful Commands:")
        print("  - Local testing: python main.py")
        print("  - Docker testing: ./scripts/start_docker.sh && ./scripts/test_docker.sh")
        print("  - AWS deployment: python infra-py/deploy.py all")
        print("  - API documentation: http://localhost:7777/docs")
        
        print(f"\n{Colors.CYAN}Demo suite completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}")


def main():
    """Main entry point"""
    runner = DemoRunner()
    
    try:
        runner.run_all_demos()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Demo interrupted by user.{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()