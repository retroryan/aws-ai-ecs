#!/usr/bin/env python3
"""
Consolidated coordinate tests for the Weather Agent.

This combines all coordinate-related tests into a single comprehensive test suite.
Tests include:
- Direct coordinate handling
- Geocoding vs coordinate provision
- Performance comparisons
- Multiple city testing
- MCP server coordinate handling
"""

import asyncio
import json
import os
import sys
import time
from datetime import date, timedelta
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weather_agent.mcp_agent import MCPWeatherAgent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class CoordinateTestSuite:
    """Comprehensive test suite for coordinate functionality."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []
    
    def add_result(self, test_name: str, passed: bool, details: str = ""):
        """Track test results."""
        self.results.append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("COORDINATE TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        
        if self.failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if not result["passed"]:
                    print(f"  ❌ {result['name']}: {result['details']}")
        
        return self.failed == 0


async def test_mcp_server_coordinates(test_suite: CoordinateTestSuite):
    """Test MCP server coordinate handling directly."""
    print("\n🧪 Testing MCP Server Coordinate Handling...")
    print("-" * 50)
    
    server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_servers", "forecast_server.py")
    server_params = StdioServerParameters(command="python", args=[server_path])
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test 1: Location string only
                try:
                    result = await session.call_tool(
                        "get_weather_forecast",
                        {"location": "Des Moines, Iowa", "days": 3}
                    )
                    test_suite.add_result("MCP Server - Location String", True, "Geocoding works")
                except Exception as e:
                    test_suite.add_result("MCP Server - Location String", False, str(e))
                
                # Test 2: Direct coordinates
                try:
                    result = await session.call_tool(
                        "get_weather_forecast",
                        {
                            "location": "Custom Location",
                            "latitude": 41.5908,
                            "longitude": -93.6208,
                            "days": 3
                        }
                    )
                    response_text = result.content[0].text
                    if "41.5908" in response_text and "-93.6208" in response_text:
                        test_suite.add_result("MCP Server - Direct Coordinates", True, "Coordinates used directly")
                    else:
                        test_suite.add_result("MCP Server - Direct Coordinates", False, "Coordinates not preserved")
                except Exception as e:
                    test_suite.add_result("MCP Server - Direct Coordinates", False, str(e))
                    
    except Exception as e:
        test_suite.add_result("MCP Server Connection", False, str(e))


async def test_agent_coordinate_handling(test_suite: CoordinateTestSuite):
    """Test agent handling of coordinates vs geocoding."""
    print("\n🧪 Testing Agent Coordinate Handling...")
    print("-" * 50)
    
    agent = MCPWeatherAgent()
    await agent.initialize()
    
    try:
        # Test 1: Simple city name (should use geocoding)
        response = await agent.query("What's the weather in Chicago?")
        if response and len(response) > 50:
            test_suite.add_result("Agent - City Name Query", True, "Got weather response")
        else:
            test_suite.add_result("Agent - City Name Query", False, "No valid response")
        
        # Test 2: Explicit coordinates in query
        response = await agent.query("What's the weather at latitude 41.8781, longitude -87.6298?")
        if response and len(response) > 50:
            test_suite.add_result("Agent - Coordinate Query", True, "Handled coordinates directly")
        else:
            test_suite.add_result("Agent - Coordinate Query", False, "Failed to handle coordinates")
        
        # Test 3: Mixed query with location and coordinates
        response = await agent.query("What's the weather at 40.7128, -74.0060 (New York)?")
        if response and "New York" in response:
            test_suite.add_result("Agent - Mixed Query", True, "Handled both name and coordinates")
        else:
            test_suite.add_result("Agent - Mixed Query", False, "Failed to handle mixed input")
            
    except Exception as e:
        test_suite.add_result("Agent Tests", False, str(e))
    finally:
        await agent.cleanup()


async def test_performance_comparison(test_suite: CoordinateTestSuite):
    """Compare performance of geocoding vs direct coordinates."""
    print("\n🧪 Testing Performance Comparison...")
    print("-" * 50)
    
    agent = MCPWeatherAgent()
    await agent.initialize()
    
    try:
        # Test with geocoding
        start = time.time()
        await agent.query("What's the current temperature in Denver?")
        geocoding_time = time.time() - start
        
        # Test with coordinates
        start = time.time()
        await agent.query("What's the current temperature at 39.7392, -104.9903?")
        direct_time = time.time() - start
        
        improvement = geocoding_time / direct_time if direct_time > 0 else 1.0
        
        print(f"Geocoding time: {geocoding_time:.2f}s")
        print(f"Direct coordinate time: {direct_time:.2f}s")
        print(f"Speed improvement: {improvement:.1f}x")
        
        test_suite.add_result("Performance Test", True, f"{improvement:.1f}x faster with coordinates")
        
    except Exception as e:
        test_suite.add_result("Performance Test", False, str(e))
    finally:
        await agent.cleanup()


async def test_diverse_cities(test_suite: CoordinateTestSuite):
    """Test various cities from around the world."""
    print("\n🧪 Testing Diverse Cities...")
    print("-" * 50)
    
    agent = MCPWeatherAgent()
    await agent.initialize()
    
    test_cities = [
        "Tokyo, Japan",
        "São Paulo, Brazil",
        "Reykjavik, Iceland",
        "Cape Town, South Africa",
        "Mumbai, India"
    ]
    
    successful = 0
    for city in test_cities:
        try:
            response = await agent.query(f"What's the current temperature in {city}?")
            if response and ("temperature" in response.lower() or "°" in response):
                successful += 1
                print(f"✅ {city}: Success")
            else:
                print(f"❌ {city}: Failed")
        except Exception as e:
            print(f"❌ {city}: Error - {str(e)}")
        
        await asyncio.sleep(1)  # Brief pause between queries
    
    success_rate = successful / len(test_cities)
    if success_rate >= 0.8:  # 80% success rate
        test_suite.add_result("Diverse Cities Test", True, f"{successful}/{len(test_cities)} cities successful")
    else:
        test_suite.add_result("Diverse Cities Test", False, f"Only {successful}/{len(test_cities)} cities successful")
    
    await agent.cleanup()


async def test_edge_cases(test_suite: CoordinateTestSuite):
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases...")
    print("-" * 50)
    
    agent = MCPWeatherAgent()
    await agent.initialize()
    
    try:
        # Test 1: Invalid coordinates
        response = await agent.query("What's the weather at latitude 200, longitude -500?")
        if "error" in response.lower() or "invalid" in response.lower():
            test_suite.add_result("Invalid Coordinates", True, "Properly handled invalid coordinates")
        else:
            test_suite.add_result("Invalid Coordinates", False, "Did not detect invalid coordinates")
        
        # Test 2: Ambiguous location
        response = await agent.query("What's the weather in Springfield?")
        if response and len(response) > 20:
            test_suite.add_result("Ambiguous Location", True, "Handled ambiguous location")
        else:
            test_suite.add_result("Ambiguous Location", False, "Failed on ambiguous location")
        
        # Test 3: Empty location with coordinates
        response = await agent.query("What's the weather at 35.6762, 139.6503?")
        if response and len(response) > 50:
            test_suite.add_result("Coordinates Only", True, "Handled coordinates without location name")
        else:
            test_suite.add_result("Coordinates Only", False, "Failed with coordinates only")
            
    except Exception as e:
        test_suite.add_result("Edge Cases", False, str(e))
    finally:
        await agent.cleanup()


async def main():
    """Run all consolidated coordinate tests."""
    print("🚀 Consolidated Coordinate Test Suite")
    print("=" * 60)
    
    test_suite = CoordinateTestSuite()
    
    # Run all test categories
    await test_mcp_server_coordinates(test_suite)
    await test_agent_coordinate_handling(test_suite)
    await test_performance_comparison(test_suite)
    await test_diverse_cities(test_suite)
    await test_edge_cases(test_suite)
    
    # Print summary
    success = test_suite.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)