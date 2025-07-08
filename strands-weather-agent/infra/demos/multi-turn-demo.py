#!/usr/bin/env python3
"""
Multi-Turn Conversation Demo for Strands Weather Agent
This script demonstrates stateful conversations with the Weather Agent API
showing session persistence across multiple queries.
"""

import json
import time
import sys
import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
try:
    from colorama import init, Fore, Style
    # Initialize colorama for cross-platform color support
    init(autoreset=True)
except ImportError:
    # Fallback if colorama is not installed
    class Fore:
        GREEN = ""
        RED = ""
        YELLOW = ""
        BLUE = ""
        CYAN = ""
        RESET = ""
    
    class Style:
        RESET_ALL = ""

# Color definitions
class Colors:
    GREEN = Fore.GREEN
    RED = Fore.RED
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    CYAN = Fore.CYAN
    RESET = Style.RESET_ALL

def get_api_url() -> str:
    """Get API URL from environment or CloudFormation stack."""
    # Try environment variable first
    api_url = os.getenv("API_URL")
    if api_url:
        return api_url
    
    # Try to get from CloudFormation stack
    try:
        import boto3
        cfn = boto3.client("cloudformation", region_name="us-east-1")
        
        # Check services stack for ALB URL
        response = cfn.describe_stacks(StackName="strands-weather-agent-services")
        for output in response["Stacks"][0].get("Outputs", []):
            if output["OutputKey"] == "ApplicationURL":
                return output["OutputValue"]
        
        # Check base stack for ALB URL
        response = cfn.describe_stacks(StackName="strands-weather-agent-base")
        for output in response["Stacks"][0].get("Outputs", []):
            if output["OutputKey"] == "ALBDNSName":
                return f"http://{output['OutputValue']}"
                
    except Exception:
        pass
    
    # Default to localhost
    return "http://localhost:7777"

class WeatherAgentDemo:
    """Demo class for testing multi-turn conversations."""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.session = requests.Session()
        
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
        
    def make_query(self, query: str, session_id: Optional[str] = None, 
                   create_session: bool = True) -> Dict[str, Any]:
        """Make a query to the Weather Agent API."""
        payload = {"query": query, "create_session": create_session}
        if session_id:
            payload["session_id"] = session_id
            
        try:
            response = self.session.post(
                f"{self.api_url}/query",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}Error making query: {e}{Colors.RESET}")
            return {}
    
    def make_structured_query(self, query: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Make a structured query to the Weather Agent API."""
        payload = {"query": query}
        if session_id:
            payload["session_id"] = session_id
            
        try:
            response = self.session.post(
                f"{self.api_url}/query/structured",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}Error making structured query: {e}{Colors.RESET}")
            return {}
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        try:
            response = self.session.get(
                f"{self.api_url}/session/{session_id}",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            response = self.session.delete(
                f"{self.api_url}/session/{session_id}",
                timeout=10
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            return False
    
    def display_result(self, turn: int, query: str, response: Dict[str, Any]) -> None:
        """Display query results in a formatted way."""
        self.total_queries += 1
        
        response_text = response.get("response", "No response")
        session_id = response.get("session_id", "No session")
        session_new = response.get("session_new", False)
        conversation_turn = response.get("conversation_turn", 0)
        metrics = response.get("metrics", {})
        trace_url = response.get("trace_url", "")
        
        # Track session IDs
        if session_id and session_id != "No session" and session_id != "null":
            if session_id not in self.all_session_ids:
                self.all_session_ids.append(session_id)
        
        print(f"{Colors.CYAN}Turn {turn}:{Colors.RESET}")
        print(f"{Colors.BLUE}Query:{Colors.RESET} {query}")
        print(f"{Colors.GREEN}Response:{Colors.RESET} {response_text}")
        session_display = session_id[:8] + "..." if len(session_id) > 8 else session_id
        print(f"{Colors.YELLOW}Session:{Colors.RESET} {session_display} | New: {session_new} | Turn: {conversation_turn}")
        
        # Display metrics if available
        if metrics:
            print("\n📊 Performance Metrics:")
            total_tokens = metrics.get("total_tokens", 0)
            input_tokens = metrics.get("input_tokens", 0)
            output_tokens = metrics.get("output_tokens", 0)
            latency_seconds = metrics.get("latency_seconds", 0)
            throughput = metrics.get("throughput_tokens_per_second", 0)
            model = metrics.get("model", "unknown")
            cycles = metrics.get("cycles", 0)
            
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
        if trace_url:
            print(f"\n🔗 Trace: {trace_url}")
        
        print()
    
    def test_session_info(self, session_id: str) -> None:
        """Test session info endpoint."""
        print(f"{Colors.CYAN}Session Info Test:{Colors.RESET}")
        
        session_info = self.get_session_info(session_id)
        if session_info:
            print(f"{Colors.GREEN}✓{Colors.RESET} Session info retrieved successfully")
            print(json.dumps({
                "session_id": session_info.get("session_id"),
                "turns": session_info.get("conversation_turns"),
                "created": session_info.get("created_at"),
                "expires": session_info.get("expires_at")
            }, indent=2))
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Failed to retrieve session info")
        print()
    
    def measure_query_time(self, query: str, session_id: Optional[str] = None) -> Tuple[Dict[str, Any], float]:
        """Measure the time taken for a query."""
        start_time = time.time()
        response = self.make_query(query, session_id)
        end_time = time.time()
        return response, end_time - start_time
    
    def run_demo(self) -> None:
        """Run the complete multi-turn conversation demo."""
        print("🔄 Multi-Turn Conversation Demo")
        print("===============================")
        print(f"API URL: {self.api_url}")
        print()
        
        # Test 1: Basic Multi-Turn Conversation
        print("1. Testing Basic Multi-Turn Conversation")
        print("----------------------------------------")
        print("Scenario: Ask about weather in a city, then follow up with temporal questions")
        print()
        
        response1 = self.make_query("What's the weather like in Seattle?")
        self.display_result(1, "What's the weather like in Seattle?", response1)
        session_id = response1.get("session_id")
        
        if session_id:
            response2 = self.make_query("How about tomorrow?", session_id)
            self.display_result(2, "How about tomorrow?", response2)
            
            response3 = self.make_query("Will it rain this weekend?", session_id)
            self.display_result(3, "Will it rain this weekend?", response3)
            
            self.test_session_info(session_id)
        
        # Test 2: Location Context Persistence
        print("2. Testing Location Context Persistence")
        print("--------------------------------------")
        print("Scenario: Compare weather in multiple cities using context")
        print()
        
        response1 = self.make_query("Compare the weather in New York and Los Angeles")
        self.display_result(1, "Compare the weather in New York and Los Angeles", response1)
        session_id2 = response1.get("session_id")
        
        if session_id2:
            response2 = self.make_query("What about just New York next week?", session_id2)
            self.display_result(2, "What about just New York next week?", response2)
            
            response3 = self.make_query("And Los Angeles?", session_id2)
            self.display_result(3, "And Los Angeles?", response3)
        
        # Test 3: Agricultural Context
        print("3. Testing Agricultural Context")
        print("------------------------------")
        print("Scenario: Agricultural queries with location context")
        print()
        
        response1 = self.make_query("Are conditions good for planting corn in Iowa?")
        self.display_result(1, "Are conditions good for planting corn in Iowa?", response1)
        session_id3 = response1.get("session_id")
        
        if session_id3:
            response2 = self.make_query("What about soybeans?", session_id3)
            self.display_result(2, "What about soybeans?", response2)
            
            response3 = self.make_query("Is there any frost risk in the next week?", session_id3)
            self.display_result(3, "Is there any frost risk in the next week?", response3)
        
        # Test 4: Session Management
        print("4. Testing Session Management")
        print("----------------------------")
        print()
        
        # Test invalid session
        print(f"{Colors.CYAN}Testing invalid session handling:{Colors.RESET}")
        invalid_response = self.make_query("What's the weather?", "invalid-session-id-12345", False)
        if not invalid_response or "error" in invalid_response or "detail" in invalid_response:
            print(f"{Colors.GREEN}✓{Colors.RESET} Invalid session properly rejected")
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Invalid session not handled correctly")
        print()
        
        # Test session deletion
        if session_id:
            print(f"{Colors.CYAN}Testing session deletion:{Colors.RESET}")
            if self.delete_session(session_id):
                print(f"{Colors.GREEN}✓{Colors.RESET} Session deleted successfully")
                
                # Verify session is gone
                if not self.get_session_info(session_id):
                    print(f"{Colors.GREEN}✓{Colors.RESET} Deleted session no longer accessible")
            else:
                print(f"{Colors.RED}✗{Colors.RESET} Failed to delete session")
        print()
        
        # Test 5: Structured Output with Sessions
        print("5. Testing Structured Output with Sessions")
        print("-----------------------------------------")
        print()
        
        structured_response = self.make_structured_query("Weather forecast for Chicago")
        if structured_response and "session_id" in structured_response:
            print(f"{Colors.GREEN}✓{Colors.RESET} Structured endpoint includes session info")
            struct_session_id = structured_response["session_id"]
            
            # Follow-up structured query
            followup_response = self.make_structured_query("How about the weekend?", struct_session_id)
            if followup_response and "conversation_turn" in followup_response:
                turn = followup_response["conversation_turn"]
                print(f"{Colors.GREEN}✓{Colors.RESET} Structured follow-up worked (turn: {turn})")
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Structured endpoint missing session info")
        print()
        
        # Test 6: Performance Test
        print("6. Performance Test")
        print("------------------")
        print("Testing response time with session context")
        print()
        
        # Create a session and time queries
        perf_response1, time1 = self.measure_query_time("What's the temperature in Boston?")
        perf_session = perf_response1.get("session_id")
        
        # Extract metrics from first query
        metrics1 = perf_response1.get("metrics", {})
        if metrics1:
            print(f"{Colors.CYAN}First Query Metrics:{Colors.RESET}")
            print(f"  API round-trip time: {Colors.YELLOW}{time1:.3f}s{Colors.RESET}")
            print(f"  Model processing time: {Colors.YELLOW}{metrics1.get('latency_seconds', 0):.3f}s{Colors.RESET}")
            print(f"  Tokens processed: {Colors.YELLOW}{metrics1.get('total_tokens', 0)}{Colors.RESET}")
            print(f"  Throughput: {Colors.YELLOW}{int(metrics1.get('throughput_tokens_per_second', 0))} tokens/sec{Colors.RESET}")
        
        if perf_session:
            perf_response2, time2 = self.measure_query_time("And humidity?", perf_session)
            
            # Extract metrics from second query
            metrics2 = perf_response2.get("metrics", {})
            if metrics2:
                print(f"\n{Colors.CYAN}Follow-up Query Metrics:{Colors.RESET}")
                print(f"  API round-trip time: {Colors.YELLOW}{time2:.3f}s{Colors.RESET}")
                print(f"  Model processing time: {Colors.YELLOW}{metrics2.get('latency_seconds', 0):.3f}s{Colors.RESET}")
                print(f"  Tokens processed: {Colors.YELLOW}{metrics2.get('total_tokens', 0)}{Colors.RESET}")
                print(f"  Throughput: {Colors.YELLOW}{int(metrics2.get('throughput_tokens_per_second', 0))} tokens/sec{Colors.RESET}")
            
            # Comparison
            print(f"\n{Colors.CYAN}Performance Comparison:{Colors.RESET}")
            if time2 < time1:
                print(f"  {Colors.GREEN}✓{Colors.RESET} Follow-up API call was faster")
            else:
                print(f"  {Colors.YELLOW}ℹ{Colors.RESET} Follow-up API call took similar time")
            
            # Compare token counts if available
            if metrics1 and metrics2:
                tokens1 = metrics1.get("total_tokens", 0)
                tokens2 = metrics2.get("total_tokens", 0)
                if tokens2 < tokens1:
                    print(f"  {Colors.GREEN}✓{Colors.RESET} Follow-up used fewer tokens (context efficiency)")
        
        print()
        
        # Summary
        print("Summary")
        print("-------")
        print(f"{Colors.GREEN}✅ Multi-turn conversation demo completed!{Colors.RESET}")
        print()
        
        # Display comprehensive metrics summary
        if self.successful_queries > 0:
            print("📊 OVERALL METRICS SUMMARY")
            print("==========================")
            print()
            print("Query Statistics:")
            print(f"  Total Queries: {self.total_queries}")
            print(f"  Successful Queries: {self.successful_queries}")
            print(f"  Unique Sessions: {len(self.all_session_ids)}")
            print()
            print("Token Usage:")
            print(f"  Total Tokens: {self.total_tokens_all:,}")
            print(f"  Input Tokens: {self.total_input_tokens:,}")
            print(f"  Output Tokens: {self.total_output_tokens:,}")
            
            # Calculate averages
            avg_tokens = self.total_tokens_all // self.successful_queries if self.successful_queries > 0 else 0
            avg_input = self.total_input_tokens // self.successful_queries if self.successful_queries > 0 else 0
            avg_output = self.total_output_tokens // self.successful_queries if self.successful_queries > 0 else 0
            avg_latency = self.total_latency / self.successful_queries if self.successful_queries > 0 else 0
            
            print(f"  Average per Query: {avg_tokens:,} tokens ({avg_input:,} in, {avg_output:,} out)")
            print()
            print("Performance:")
            print(f"  Total Processing Time: {self.total_latency:.1f}s")
            print(f"  Average Latency: {avg_latency:.2f}s per query")
            if self.total_latency > 0:
                avg_throughput = int(self.total_tokens_all / self.total_latency)
                print(f"  Overall Throughput: {avg_throughput:,} tokens/second")
            print(f"  Total Agent Cycles: {self.total_cycles}")
            print(f"  Model: {self.model_used}")
            
            # Check if Langfuse is enabled
            langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            if langfuse_public_key and langfuse_secret_key:
                print()
                print("Telemetry:")
                print(f"  Langfuse Host: {os.getenv('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')}")
                print(f"  Traces Generated: {self.successful_queries}")
                print(f"  Sessions Tracked: {len(self.all_session_ids)}")
            
            print()
        
        print("Key findings:")
        print("- Sessions persist across multiple queries")
        print("- Context is maintained for follow-up questions")
        print("- Invalid sessions are properly handled")
        print("- Both regular and structured endpoints support sessions")
        print()
        print("To test further:")
        print("- Wait 60+ minutes to test session expiration")
        print("- Run concurrent tests to verify session isolation")
        print("- Monitor memory usage with many active sessions")
        print()
        print(f"API Documentation: {self.api_url}/docs")
        print()

def main():
    """Main entry point."""
    # Get API URL
    api_url = get_api_url()
    
    # Check if API is accessible
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}Error: Cannot connect to API at {api_url}{Colors.RESET}")
        print(f"Details: {e}")
        print("\nMake sure the Weather Agent is running:")
        print("- Local: python main.py")
        print("- Docker: ./scripts/start_docker.sh")
        print("- AWS: python infra/deploy.py status")
        sys.exit(1)
    
    # Run the demo
    demo = WeatherAgentDemo(api_url)
    demo.run_demo()

if __name__ == "__main__":
    main()