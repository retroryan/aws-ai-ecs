#!/usr/bin/env python3
"""
Comprehensive Debug Test Suite for Coordinate Formatting Issue
Runs the same tests against different deployments and logs results
"""

import asyncio
import aiohttp
import json
import time
import os
import sys
from datetime import datetime
from pathlib import Path
import argparse

class DebugTestSuite:
    def __init__(self, base_url, output_dir, environment_name):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.environment_name = environment_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.output_dir / f"debug_{environment_name}_{timestamp}.json"
        self.results = {
            "environment": environment_name,
            "base_url": base_url,
            "timestamp": timestamp,
            "tests": []
        }
    
    async def run_all_tests(self):
        """Run all debug tests"""
        print(f"\n🧪 Running Debug Test Suite for {self.environment_name}")
        print(f"📝 Logging to: {self.log_file}")
        print("=" * 60)
        
        # Test 1: Health and connectivity
        await self.test_health()
        
        # Test 2: MCP server status
        await self.test_mcp_status()
        
        # Test 3: Coordinate formatting tests
        await self.test_coordinate_formats()
        
        # Test 4: Known problematic queries
        await self.test_problematic_queries()
        
        # Test 5: Response timing analysis
        await self.test_response_timing()
        
        # Test 6: Agricultural query (timeout test)
        await self.test_agricultural_timeout()
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
    
    async def test_health(self):
        """Test basic health endpoint"""
        test_result = {
            "test_name": "health_check",
            "start_time": time.time()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    test_result["status_code"] = response.status
                    test_result["response"] = await response.json()
                    test_result["success"] = response.status == 200
        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["tests"].append(test_result)
        
        print(f"✅ Health Check: {'PASSED' if test_result.get('success') else 'FAILED'}")
    
    async def test_mcp_status(self):
        """Test MCP server connectivity"""
        test_result = {
            "test_name": "mcp_status",
            "start_time": time.time()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/mcp/status", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    test_result["status_code"] = response.status
                    test_result["response"] = await response.json()
                    test_result["success"] = response.status == 200
                    
                    # Check connected servers
                    if test_result["success"]:
                        status = test_result["response"]
                        test_result["connected_servers"] = status.get("connected_count", 0)
                        test_result["total_servers"] = status.get("total_count", 0)
        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["tests"].append(test_result)
        
        print(f"🔌 MCP Status: {'PASSED' if test_result.get('success') else 'FAILED'}")
        if test_result.get("success"):
            print(f"   Connected: {test_result.get('connected_servers', 0)}/{test_result.get('total_servers', 0)}")
    
    async def test_coordinate_formats(self):
        """Test different coordinate format queries"""
        coordinate_queries = [
            {
                "name": "simple_city",
                "query": "What's the weather in Paris?",
                "description": "Simple city name without known coordinates"
            },
            {
                "name": "known_city_seattle",
                "query": "What's the weather in Seattle?",
                "description": "City that triggers coordinate lookup"
            },
            {
                "name": "explicit_coords_text",
                "query": "What's the weather at latitude 47.6062 and longitude -122.3321?",
                "description": "Explicit coordinates in text"
            },
            {
                "name": "coords_in_parentheses",
                "query": "Weather in Seattle (47.6062, -122.3321)",
                "description": "City with coordinates in parentheses"
            },
            {
                "name": "decimal_coords",
                "query": "Weather at 47.6062 latitude, -122.3321 longitude",
                "description": "Coordinates with decimal precision"
            },
            {
                "name": "integer_coords",
                "query": "Weather at latitude 48 longitude -122",
                "description": "Integer coordinates"
            }
        ]
        
        for query_test in coordinate_queries:
            await self.run_query_test(query_test)
    
    async def test_problematic_queries(self):
        """Test queries known to cause issues"""
        problematic_queries = [
            {
                "name": "boston_faster_response",
                "query": "What's the weather in Boston?",
                "description": "Boston triggers 'faster response' behavior"
            },
            {
                "name": "chicago_forecast",
                "query": "Give me a 5-day forecast for Chicago",
                "description": "Multi-day forecast request"
            },
            {
                "name": "location_list",
                "query": "Compare weather in Seattle, Boston, and Chicago",
                "description": "Multiple locations in one query"
            }
        ]
        
        for query_test in problematic_queries:
            await self.run_query_test(query_test)
    
    async def run_query_test(self, query_info):
        """Run a single query test"""
        test_result = {
            "test_name": f"query_{query_info['name']}",
            "query": query_info["query"],
            "description": query_info["description"],
            "start_time": time.time()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"query": query_info["query"]}
                async with session.post(
                    f"{self.base_url}/query", 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    test_result["status_code"] = response.status
                    result = await response.json()
                    test_result["response"] = result
                    test_result["success"] = response.status == 200
                    
                    # Analyze response for formatting errors
                    if test_result["success"]:
                        response_text = result.get("response", "")
                        test_result["has_formatting_error"] = "apologize for the formatting error" in response_text
                        test_result["has_technical_error"] = "apologize for the technical error" in response_text
                        test_result["mentions_coordinates"] = "coordinates" in response_text.lower()
                        test_result["mentions_faster_response"] = "faster response" in response_text
                        test_result["retry_detected"] = "Let me try again" in response_text
                        
                        # Extract error patterns
                        if test_result["has_formatting_error"] or test_result["has_technical_error"]:
                            # Find what comes before the error
                            error_pos = response_text.find("apologize")
                            if error_pos > 0:
                                test_result["text_before_error"] = response_text[max(0, error_pos-100):error_pos]
                        
                        # Measure response length
                        test_result["response_length"] = len(response_text)
                        test_result["session_id"] = result.get("session_id")
                        
        except asyncio.TimeoutError:
            test_result["error"] = "Timeout (30s)"
            test_result["success"] = False
            test_result["timeout"] = True
        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["tests"].append(test_result)
        
        # Print result
        status = "PASSED" if test_result.get("success") and not test_result.get("has_formatting_error") else "FAILED"
        print(f"\n📍 {query_info['name']}: {status}")
        print(f"   Query: {query_info['query'][:50]}...")
        print(f"   Duration: {test_result['duration']:.2f}s")
        if test_result.get("has_formatting_error"):
            print("   ⚠️  Formatting error detected")
        if test_result.get("retry_detected"):
            print("   🔄 Retry pattern detected")
    
    async def test_response_timing(self):
        """Test response times for different query types"""
        timing_test = {
            "test_name": "response_timing",
            "queries": []
        }
        
        queries = [
            ("simple", "What's the temperature?"),
            ("city", "Weather in London"),
            ("coordinate", "Weather at 51.5074, -0.1278"),
            ("complex", "Should I bring an umbrella to Paris tomorrow?")
        ]
        
        print("\n⏱️  Testing Response Times...")
        
        for query_type, query in queries:
            start = time.time()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/query",
                        json={"query": query},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        await response.json()
                        duration = time.time() - start
                        timing_test["queries"].append({
                            "type": query_type,
                            "query": query,
                            "duration": duration,
                            "success": True
                        })
                        print(f"   {query_type}: {duration:.2f}s")
            except Exception as e:
                timing_test["queries"].append({
                    "type": query_type,
                    "query": query,
                    "error": str(e),
                    "success": False
                })
                print(f"   {query_type}: FAILED - {str(e)}")
        
        self.results["tests"].append(timing_test)
    
    async def test_agricultural_timeout(self):
        """Test the agricultural query that times out"""
        test_result = {
            "test_name": "agricultural_timeout",
            "query": "Are conditions good for planting corn in Iowa?",
            "start_time": time.time()
        }
        
        print("\n🌽 Testing Agricultural Query (known timeout)...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/query",
                    json={"query": test_result["query"]},
                    timeout=aiohttp.ClientTimeout(total=35)  # Slightly longer than API timeout
                ) as response:
                    test_result["status_code"] = response.status
                    result = await response.json()
                    test_result["response"] = result
                    test_result["success"] = True
                    print("   ✅ Completed successfully")
        except asyncio.TimeoutError:
            test_result["error"] = "Timeout"
            test_result["success"] = False
            print("   ❌ Timeout as expected")
        except Exception as e:
            test_result["error"] = str(e)
            test_result["success"] = False
            print(f"   ❌ Error: {str(e)}")
        
        test_result["duration"] = time.time() - test_result["start_time"]
        self.results["tests"].append(test_result)
    
    def save_results(self):
        """Save test results to JSON file"""
        with open(self.log_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to: {self.log_file}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for t in self.results["tests"] if t.get("success") and not t.get("has_formatting_error"))
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        
        # Count formatting errors
        formatting_errors = sum(1 for t in self.results["tests"] 
                               if t.get("has_formatting_error") or t.get("has_technical_error"))
        if formatting_errors > 0:
            print(f"Formatting Errors: {formatting_errors}")
        
        # Count timeouts
        timeouts = sum(1 for t in self.results["tests"] if t.get("timeout"))
        if timeouts > 0:
            print(f"Timeouts: {timeouts}")
        
        print("\n💡 Key Findings:")
        # Analyze patterns
        coord_mentions = sum(1 for t in self.results["tests"] if t.get("mentions_coordinates"))
        retry_patterns = sum(1 for t in self.results["tests"] if t.get("retry_detected"))
        
        if coord_mentions > 0:
            print(f"- {coord_mentions} responses mentioned coordinates")
        if retry_patterns > 0:
            print(f"- {retry_patterns} responses showed retry behavior")


async def main():
    parser = argparse.ArgumentParser(description="Debug test suite for coordinate formatting issue")
    parser.add_argument("environment", choices=["docker", "aws", "local"], 
                       help="Environment to test")
    parser.add_argument("--url", help="Override base URL")
    parser.add_argument("--output-dir", default="logs", help="Output directory for logs")
    
    args = parser.parse_args()
    
    # Determine base URL
    if args.url:
        base_url = args.url
    elif args.environment == "docker":
        base_url = "http://localhost:7777"
    elif args.environment == "aws":
        # You'll need to update this with your ALB URL
        base_url = "http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com"
    else:  # local
        base_url = "http://localhost:7777"
    
    # Run tests
    test_suite = DebugTestSuite(base_url, args.output_dir, args.environment)
    await test_suite.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())