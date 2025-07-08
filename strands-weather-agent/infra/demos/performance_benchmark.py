#!/usr/bin/env python3
"""
Performance Benchmark Demo for Strands Weather Agent
This script runs performance benchmarks to measure throughput, latency, and scalability.
"""

import json
import time
import statistics
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Tuple
import requests
import os
import sys
from pathlib import Path

# Add parent directory to path if needed
sys.path.append(str(Path(__file__).parent.parent))

# Color support
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


class PerformanceBenchmark:
    """Performance benchmarking for the Weather Agent"""
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.session = requests.Session()
        
    def print_header(self, text: str) -> None:
        """Print a formatted header"""
        print(f"\n{'=' * 70}")
        print(f"{Colors.MAGENTA}⚡ {text}{Colors.RESET}")
        print('=' * 70)
        
    def make_query(self, query: str, session_id: str = None) -> Tuple[Dict[str, Any], float]:
        """Make a query and return response with timing"""
        payload = {"query": query}
        if session_id:
            payload["session_id"] = session_id
            
        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.api_url}/query",
                json=payload,
                timeout=30
            )
            end_time = time.time()
            
            if response.status_code == 200:
                return response.json(), end_time - start_time
            else:
                return {"error": f"Status {response.status_code}"}, end_time - start_time
        except Exception as e:
            end_time = time.time()
            return {"error": str(e)}, end_time - start_time
    
    def run_latency_test(self, num_queries: int = 10) -> Dict[str, Any]:
        """Test query latency with various query types"""
        self.print_header("Latency Benchmark")
        
        queries = [
            "What's the weather in New York?",
            "Give me a 5-day forecast for Seattle",
            "Compare weather in Chicago and Miami",
            "Are conditions good for planting corn in Iowa?",
            "What were the temperatures in Boston last week?",
        ]
        
        results = []
        total_tokens = 0
        
        print(f"Running {num_queries} queries to measure latency...")
        print("")
        
        for i in range(num_queries):
            query = queries[i % len(queries)]
            response, elapsed = self.make_query(query)
            
            if "error" not in response:
                metrics = response.get("metrics", {})
                model_latency = metrics.get("latency_seconds", 0)
                tokens = metrics.get("total_tokens", 0)
                
                results.append({
                    "total_time": elapsed,
                    "model_time": model_latency,
                    "overhead": elapsed - model_latency,
                    "tokens": tokens
                })
                
                total_tokens += tokens
                
                print(f"  Query {i+1}/{num_queries}: {elapsed:.2f}s total ({model_latency:.2f}s model)")
            else:
                print(f"  Query {i+1}/{num_queries}: {Colors.RED}Failed{Colors.RESET}")
        
        if results:
            # Calculate statistics
            total_times = [r["total_time"] for r in results]
            model_times = [r["model_time"] for r in results]
            overheads = [r["overhead"] for r in results]
            
            print(f"\n{Colors.CYAN}Latency Statistics:{Colors.RESET}")
            print(f"  Total Response Time:")
            print(f"    Min: {min(total_times):.2f}s")
            print(f"    Max: {max(total_times):.2f}s")
            print(f"    Mean: {statistics.mean(total_times):.2f}s")
            print(f"    Median: {statistics.median(total_times):.2f}s")
            
            print(f"\n  Model Processing Time:")
            print(f"    Min: {min(model_times):.2f}s")
            print(f"    Max: {max(model_times):.2f}s")
            print(f"    Mean: {statistics.mean(model_times):.2f}s")
            print(f"    Median: {statistics.median(model_times):.2f}s")
            
            print(f"\n  API Overhead:")
            print(f"    Min: {min(overheads):.2f}s")
            print(f"    Max: {max(overheads):.2f}s")
            print(f"    Mean: {statistics.mean(overheads):.2f}s")
            
            return {
                "num_queries": len(results),
                "avg_latency": statistics.mean(total_times),
                "total_tokens": total_tokens
            }
        
        return {"num_queries": 0, "avg_latency": 0, "total_tokens": 0}
    
    def run_throughput_test(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """Test sustained throughput over time"""
        self.print_header("Throughput Benchmark")
        
        print(f"Running continuous queries for {duration_seconds} seconds...")
        print("")
        
        queries = [
            "What's the current temperature in San Francisco?",
            "Is it raining in London?",
            "What's the humidity in Tokyo?",
        ]
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        completed_queries = 0
        total_tokens = 0
        errors = 0
        
        # Create a session for reuse
        session_id = None
        
        while time.time() < end_time:
            query = queries[completed_queries % len(queries)]
            response, elapsed = self.make_query(query, session_id)
            
            if "error" not in response:
                completed_queries += 1
                if not session_id:
                    session_id = response.get("session_id")
                
                metrics = response.get("metrics", {})
                total_tokens += metrics.get("total_tokens", 0)
                
                # Progress indicator
                if completed_queries % 5 == 0:
                    elapsed_time = time.time() - start_time
                    qps = completed_queries / elapsed_time
                    print(f"  Progress: {completed_queries} queries, {qps:.1f} queries/sec")
            else:
                errors += 1
        
        total_duration = time.time() - start_time
        
        print(f"\n{Colors.CYAN}Throughput Results:{Colors.RESET}")
        print(f"  Duration: {total_duration:.1f}s")
        print(f"  Completed Queries: {completed_queries}")
        print(f"  Failed Queries: {errors}")
        print(f"  Queries per Second: {completed_queries / total_duration:.2f}")
        print(f"  Total Tokens: {total_tokens:,}")
        print(f"  Tokens per Second: {int(total_tokens / total_duration)}")
        
        return {
            "duration": total_duration,
            "queries": completed_queries,
            "qps": completed_queries / total_duration,
            "tokens_per_sec": total_tokens / total_duration
        }
    
    def run_concurrent_test(self, num_concurrent: int = 5, queries_per_client: int = 3) -> Dict[str, Any]:
        """Test concurrent query handling"""
        self.print_header("Concurrency Benchmark")
        
        print(f"Running {num_concurrent} concurrent clients, {queries_per_client} queries each...")
        print("")
        
        queries = [
            "What's the weather forecast for Chicago?",
            "Give me agricultural conditions in Nebraska",
            "Compare temperatures in Miami and Seattle",
        ]
        
        def client_task(client_id: int) -> Dict[str, Any]:
            """Task for each concurrent client"""
            client_results = []
            session_id = None
            
            for i in range(queries_per_client):
                query = queries[(client_id + i) % len(queries)]
                response, elapsed = self.make_query(query, session_id)
                
                if "error" not in response:
                    if not session_id:
                        session_id = response.get("session_id")
                    
                    metrics = response.get("metrics", {})
                    client_results.append({
                        "elapsed": elapsed,
                        "tokens": metrics.get("total_tokens", 0),
                        "model_time": metrics.get("latency_seconds", 0)
                    })
            
            return {
                "client_id": client_id,
                "results": client_results,
                "session_id": session_id
            }
        
        # Run concurrent clients
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(client_task, i) for i in range(num_concurrent)]
            client_results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        all_results = []
        unique_sessions = set()
        
        for client in client_results:
            all_results.extend(client["results"])
            if client["session_id"]:
                unique_sessions.add(client["session_id"])
        
        if all_results:
            response_times = [r["elapsed"] for r in all_results]
            total_tokens = sum(r["tokens"] for r in all_results)
            
            print(f"\n{Colors.CYAN}Concurrency Results:{Colors.RESET}")
            print(f"  Total Duration: {total_time:.2f}s")
            print(f"  Concurrent Clients: {num_concurrent}")
            print(f"  Total Queries: {len(all_results)}")
            print(f"  Unique Sessions: {len(unique_sessions)}")
            print(f"  Queries per Second: {len(all_results) / total_time:.2f}")
            print(f"\n  Response Times:")
            print(f"    Min: {min(response_times):.2f}s")
            print(f"    Max: {max(response_times):.2f}s")
            print(f"    Mean: {statistics.mean(response_times):.2f}s")
            print(f"    Median: {statistics.median(response_times):.2f}s")
            
            return {
                "total_queries": len(all_results),
                "duration": total_time,
                "avg_response_time": statistics.mean(response_times),
                "total_tokens": total_tokens
            }
        
        return {"total_queries": 0, "duration": total_time, "avg_response_time": 0, "total_tokens": 0}
    
    def run_stress_test(self, max_qps: int = 10, duration: int = 20) -> Dict[str, Any]:
        """Gradually increase load to find breaking point"""
        self.print_header("Stress Test")
        
        print(f"Ramping up to {max_qps} queries/second over {duration} seconds...")
        print("")
        
        results = []
        current_qps = 1
        
        while current_qps <= max_qps:
            print(f"\n{Colors.YELLOW}Testing at {current_qps} queries/second...{Colors.RESET}")
            
            # Run for 5 seconds at this rate
            test_duration = 5
            start_time = time.time()
            end_time = start_time + test_duration
            
            completed = 0
            errors = 0
            total_latency = 0
            
            while time.time() < end_time:
                # Control rate
                expected_queries = int((time.time() - start_time) * current_qps)
                
                if completed < expected_queries:
                    query = "What's the weather in Boston?"
                    response, elapsed = self.make_query(query)
                    
                    if "error" not in response:
                        completed += 1
                        total_latency += elapsed
                    else:
                        errors += 1
                else:
                    time.sleep(0.01)  # Small sleep to avoid busy waiting
            
            actual_duration = time.time() - start_time
            actual_qps = completed / actual_duration
            avg_latency = total_latency / completed if completed > 0 else 0
            
            print(f"  Target QPS: {current_qps}")
            print(f"  Actual QPS: {actual_qps:.2f}")
            print(f"  Success Rate: {completed / (completed + errors) * 100:.1f}%")
            print(f"  Avg Latency: {avg_latency:.2f}s")
            
            results.append({
                "target_qps": current_qps,
                "actual_qps": actual_qps,
                "success_rate": completed / (completed + errors) if (completed + errors) > 0 else 0,
                "avg_latency": avg_latency
            })
            
            # Stop if we can't keep up
            if actual_qps < current_qps * 0.8 or errors > completed * 0.2:
                print(f"\n{Colors.RED}System saturated at {current_qps} QPS{Colors.RESET}")
                break
            
            current_qps += 1
        
        return {"max_sustainable_qps": current_qps - 1, "results": results}
    
    def run_all_benchmarks(self) -> None:
        """Run all performance benchmarks"""
        self.print_header("AWS Strands Weather Agent - Performance Benchmarks")
        
        print(f"\nAPI Endpoint: {self.api_url}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check API health first
        try:
            resp = self.session.get(f"{self.api_url}/health", timeout=5)
            if resp.status_code != 200:
                print(f"\n{Colors.RED}API health check failed!{Colors.RESET}")
                return
        except Exception as e:
            print(f"\n{Colors.RED}Cannot connect to API: {e}{Colors.RESET}")
            return
        
        all_results = {}
        
        # 1. Latency Test
        latency_results = self.run_latency_test(20)
        all_results["latency"] = latency_results
        time.sleep(2)
        
        # 2. Throughput Test
        throughput_results = self.run_throughput_test(30)
        all_results["throughput"] = throughput_results
        time.sleep(2)
        
        # 3. Concurrency Test
        concurrency_results = self.run_concurrent_test(10, 5)
        all_results["concurrency"] = concurrency_results
        time.sleep(2)
        
        # 4. Stress Test (optional - can be intense)
        print(f"\n{Colors.YELLOW}Run stress test? This may impact service availability (y/n): {Colors.RESET}", end="")
        if input().lower() == 'y':
            stress_results = self.run_stress_test(15, 30)
            all_results["stress"] = stress_results
        
        # Final Summary
        self.print_header("Performance Summary")
        
        print("\n📊 Key Metrics:")
        print(f"  Average Latency: {all_results['latency']['avg_latency']:.2f}s")
        print(f"  Sustained Throughput: {all_results['throughput']['qps']:.2f} queries/sec")
        print(f"  Token Throughput: {int(all_results['throughput']['tokens_per_sec'])} tokens/sec")
        print(f"  Concurrent Handling: {all_results['concurrency']['total_queries']} queries in {all_results['concurrency']['duration']:.1f}s")
        
        # Calculate total tokens
        total_tokens = (
            all_results['latency']['total_tokens'] +
            all_results['throughput']['queries'] * 150 +  # Estimate
            all_results['concurrency']['total_tokens']
        )
        
        print(f"\n💰 Token Usage:")
        print(f"  Total Tokens Used: {total_tokens:,}")
        
        print(f"\n🎯 Recommendations:")
        if all_results['latency']['avg_latency'] > 2:
            print("  - Consider using a faster model or optimizing prompts")
        if all_results['throughput']['qps'] < 1:
            print("  - Scale up ECS tasks for better throughput")
        if all_results['concurrency']['avg_response_time'] > all_results['latency']['avg_latency'] * 2:
            print("  - Add more concurrent capacity for better parallel handling")
        
        print(f"\n✅ Benchmark completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def get_api_url() -> str:
    """Get API URL from environment or CloudFormation"""
    # Try environment variable first
    api_url = os.getenv("API_URL")
    if api_url:
        return api_url
    
    # Try to get from CloudFormation
    try:
        import boto3
        cfn = boto3.client("cloudformation", region_name="us-east-1")
        
        # Check base stack for ALB URL
        response = cfn.describe_stacks(StackName="strands-weather-agent-base")
        for output in response["Stacks"][0].get("Outputs", []):
            if output["OutputKey"] == "ALBDNSName":
                return f"http://{output['OutputValue']}"
    except Exception:
        pass
    
    # Default to localhost
    return "http://localhost:7777"


def main():
    """Main entry point"""
    api_url = get_api_url()
    
    benchmark = PerformanceBenchmark(api_url)
    benchmark.run_all_benchmarks()


if __name__ == "__main__":
    main()