#!/usr/bin/env python3
"""
Comprehensive tests for MCP Agent.
Run from weather_agent directory.

This consolidated test suite covers:
- Agent initialization and setup
- Query processing and tool selection
- Structured output processing
- Error handling and edge cases
- Integration with real MCP servers
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from weather_agent.mcp_agent import MCPWeatherAgent
from weather_agent.models.structured_responses import WeatherQueryResponse, ValidationResult


# Test utilities
class TestResultsTracker:
    """Track test results and provide summary."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_test(self, name: str, passed: bool, details: str = ""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "details": details
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def print_summary(self):
        print("\n" + "="*60)
        print("CONSOLIDATED MCP AGENT TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/(self.passed + self.failed)*100):.1f}%")
        
        if self.failed > 0:
            print("\nFailed Tests:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"  ❌ {test['name']}")
                    if test["details"]:
                        print(f"     {test['details']}")
        
        print(f"\n🎯 {'All tests passed!' if self.failed == 0 else 'Some tests failed - check details above'}")


# Global test results
results = TestResultsTracker()


async def test_agent_initialization():
    """Test agent initialization and setup."""
    print("\n🧪 Testing Agent Initialization...")
    print("-" * 50)
    
    try:
        agent = MCPWeatherAgent()
        results.add_test("Agent Creation", True, "MCPWeatherAgent instance created")
        
        # Test connectivity to MCP servers
        connectivity = await agent.test_connectivity()
        if any(connectivity.values()):
            connected_count = sum(1 for v in connectivity.values() if v)
            results.add_test("MCP Server Connectivity", True, f"Connected to {connected_count} MCP servers")
            
            for server, connected in connectivity.items():
                if connected:
                    print(f"✅ Connected to {server} server")
                else:
                    print(f"❌ Failed to connect to {server} server")
        else:
            results.add_test("MCP Server Connectivity", False, "No MCP servers available")
        
        # Check model configuration
        info = agent.get_agent_info()
        if info["model"]:
            results.add_test("Bedrock Model", True, f"Using model: {info['model']}")
        else:
            results.add_test("Bedrock Model", False, "No model configured")
        
        # Check debug logging setting
        results.add_test("Debug Logging", True, f"Debug logging: {info['debug_logging']}")
        
        return True
        
    except Exception as e:
        results.add_test("Agent Initialization", False, str(e))
        print(f"❌ Initialization error: {e}")
        return False


async def test_basic_query():
    """Test basic query functionality."""
    print("\n🧪 Testing Basic Query Processing...")
    print("-" * 50)
    
    try:
        agent = MCPWeatherAgent()
        
        # Test simple weather query
        query = "What's the weather forecast for Des Moines, Iowa?"
        print(f"Query: {query}")
        
        response = await agent.query(query)
        
        if response and len(response) > 100:
            results.add_test("Basic Weather Query", True, f"Response length: {len(response)} chars")
            print(f"✅ Got response: {response[:100]}...")
        else:
            results.add_test("Basic Weather Query", False, f"Short/empty response: {response[:50] if response else 'None'}")
        
        return True
        
    except Exception as e:
        results.add_test("Basic Query", False, str(e))
        print(f"❌ Query error: {e}")
        return False


async def test_structured_output():
    """Test structured output functionality with AWS Strands."""
    print("\n🧪 Testing Structured Output with AWS Strands...")
    print("-" * 50)
    
    try:
        agent = MCPWeatherAgent(debug_logging=True)
        
        # Test connectivity first
        connectivity = await agent.test_connectivity()
        if not any(connectivity.values()):
            results.add_test("MCP Server Connectivity", False, "No servers available")
            return False
        results.add_test("MCP Server Connectivity", True, f"Connected to {sum(1 for v in connectivity.values() if v)} servers")
        
        # Test structured weather forecast
        print("\n1. Testing structured weather forecast...")
        forecast_query = "What's the weather forecast for Iowa City, Iowa?"
        
        structured_response = await agent.query_structured(forecast_query)
        
        if isinstance(structured_response, WeatherQueryResponse):
            results.add_test("Structured Response Type", True, "Returned WeatherQueryResponse")
            
            # Check locations
            if structured_response.locations:
                loc = structured_response.get_primary_location()
                results.add_test("Location Extraction", True, f"Location: {loc.name} ({loc.latitude}, {loc.longitude})")
                
                # Check coordinate precision
                if loc.latitude and loc.longitude:
                    results.add_test("Coordinate Precision", True, f"Coordinates provided: {loc.latitude}, {loc.longitude}")
                else:
                    results.add_test("Coordinate Precision", False, "Missing coordinates")
            else:
                results.add_test("Location Extraction", False, "No locations extracted")
            
            # Check summary
            if structured_response.summary:
                results.add_test("Response Summary", True, f"Summary length: {len(structured_response.summary)}")
            else:
                results.add_test("Response Summary", False, "Missing summary")
            
            # Check weather data
            if structured_response.weather_data:
                results.add_test("Weather Data", True, "Weather data retrieved")
            else:
                results.add_test("Weather Data", False, "No weather data")
            
        else:
            results.add_test("Structured Response Type", False, f"Wrong type: {type(structured_response)}")
        
        # Test structured agricultural assessment  
        print("\n2. Testing structured agricultural assessment...")
        ag_query = "Are conditions good for planting corn in Nebraska?"
        
        ag_response = await agent.query_structured(ag_query)
        
        if isinstance(ag_response, WeatherQueryResponse):
            results.add_test("Agricultural Response Type", True, "Returned WeatherQueryResponse")
            
            # Check query type detection
            if ag_response.query_type == "agricultural":
                results.add_test("Query Type Detection", True, "Correctly identified as agricultural")
            else:
                results.add_test("Query Type Detection", False, f"Wrong query type: {ag_response.query_type}")
            
            # Check agricultural assessment
            if ag_response.agricultural_assessment:
                assessment = ag_response.agricultural_assessment
                results.add_test("Agricultural Assessment", True, f"Planting window: {assessment.planting_window}")
                
                if assessment.recommendations:
                    count = len(assessment.recommendations)
                    results.add_test("Recommendations", True, f"{count} recommendations provided")
                else:
                    results.add_test("Recommendations", False, "No recommendations")
            else:
                results.add_test("Agricultural Assessment", False, "No agricultural assessment")
            
        else:
            results.add_test("Agricultural Response Type", False, f"Wrong type: {type(ag_response)}")
        
        # Test response validation
        validation = agent.validate_response(ag_response)
        if validation.valid:
            results.add_test("Response Validation", True, "Response passed validation")
        else:
            results.add_test("Response Validation", False, f"Validation errors: {validation.errors}")
        
        return True
        
    except Exception as e:
        results.add_test("Structured Output", False, str(e))
        print(f"❌ Structured output error: {e}")
        return False


async def test_error_handling():
    """Test error handling scenarios."""
    print("\n🧪 Testing Error Handling...")
    print("-" * 50)
    
    try:
        agent = MCPWeatherAgent()
        
        # Test with out-of-scope query
        print("\n1. Testing out-of-scope query...")
        out_of_scope_query = "Tell me about the stock market"
        response = await agent.query(out_of_scope_query)
        
        if response and "weather" in response.lower() and "agricultural" in response.lower():
            results.add_test("Out-of-Scope Query Handling", True, "Correctly redirected to weather/agricultural topics")
        else:
            results.add_test("Out-of-Scope Query Handling", False, "Failed to handle out-of-scope query properly")
        
        # Test with very long query
        print("\n2. Testing long query...")
        long_query = "What's the weather " + "very " * 100 + "detailed forecast for Des Moines?"
        response = await agent.query(long_query)
        
        if response:
            results.add_test("Long Query Handling", True, "Handled long query")
        else:
            results.add_test("Long Query Handling", False, "Failed to handle long query")
        
        # Test structured output with ambiguous location
        print("\n3. Testing ambiguous location handling...")
        try:
            ambiguous_response = await agent.query_structured(
                "What's the weather in Springfield?"
            )
            
            if isinstance(ambiguous_response, WeatherQueryResponse):
                if ambiguous_response.needs_clarification():
                    results.add_test("Ambiguous Location Detection", True, "Detected ambiguous location")
                    clarification = ambiguous_response.get_clarification_message()
                    if clarification:
                        results.add_test("Clarification Message", True, "Provided clarification options")
                    else:
                        results.add_test("Clarification Message", False, "No clarification message")
                else:
                    # Agent made a best guess
                    results.add_test("Ambiguous Location Handling", True, "Agent selected a specific Springfield")
            else:
                results.add_test("Ambiguous Location Response", False, "Wrong response type")
        except Exception as e:
            results.add_test("Ambiguous Location Handling", False, f"Exception: {str(e)}")
        
        return True
        
    except Exception as e:
        results.add_test("Error Handling", False, str(e))
        print(f"❌ Error handling test failed: {e}")
        return False


async def test_mcp_client_identification():
    """Test MCP client identification and management."""
    print("\n🧪 Testing MCP Client Identification...")
    print("-" * 50)
    
    try:
        agent = MCPWeatherAgent()
        
        # Test 1: Check that clients are created
        num_clients = len(agent.mcp_clients)
        results.add_test("MCP Clients Created", num_clients > 0, f"Created {num_clients} clients")
        print(f"📊 Number of MCP clients: {num_clients}")
        
        # Test 2: Verify client list structure
        # Currently returns List[MCPClient], test if this causes issues
        if hasattr(agent.mcp_clients, '__iter__'):
            results.add_test("MCP Clients Iterable", True, "Clients can be iterated")
        else:
            results.add_test("MCP Clients Iterable", False, "Clients not iterable")
        
        # Test 3: Test connectivity with indexed access
        # This simulates the current implementation
        connectivity = await agent.test_connectivity()
        connected_count = sum(1 for v in connectivity.values() if v)
        results.add_test("MCP Client Connectivity", connected_count > 0, 
                        f"{connected_count}/{len(connectivity)} servers connected")
        
        # Test 4: Demonstrate potential issue with list approach
        # If we need to identify which client failed, we can't easily map back
        server_names = ["forecast", "historical", "agricultural"]
        if len(agent.mcp_clients) == len(server_names):
            results.add_test("Client-Server Mapping", True, 
                           "Client count matches expected servers")
        else:
            results.add_test("Client-Server Mapping", False,
                           f"Mismatch: {len(agent.mcp_clients)} clients vs {len(server_names)} servers")
        
        # Test 5: Demonstrate the improvement with dict approach
        # This would be the improved version:
        # if isinstance(agent.mcp_clients, dict):
        #     for name, client in agent.mcp_clients.items():
        #         print(f"  - {name}: {type(client).__name__}")
        
        print("\n📝 Current implementation uses List[MCPClient]")
        print("   - Pros: Simple, works for current use case")
        print("   - Cons: Can't identify which server a client belongs to")
        print("   - Risk: Low (current code doesn't need server identification)")
        
        return True
        
    except Exception as e:
        results.add_test("MCP Client Identification", False, str(e))
        print(f"❌ MCP client test failed: {e}")
        return False


async def test_tool_integration():
    """Test integration with MCP tools."""
    print("\n🧪 Testing MCP Tool Integration...")
    print("-" * 50)
    
    try:
        agent = MCPWeatherAgent()
        
        # Test queries that should trigger different tools
        test_cases = [
            ("Get forecast for Dallas, Texas", "forecast"),
            ("Show historical weather for Seattle last month", "historical"),
            ("Are soil conditions good for planting in Iowa?", "agricultural")
        ]
        
        for query, expected_tool_type in test_cases:
            print(f"\nTesting: {query}")
            response = await agent.query(query)
            
            if response and len(response) > 50:
                results.add_test(f"Tool Integration ({expected_tool_type})", True, f"Got response: {len(response)} chars")
                print(f"✅ {expected_tool_type} tool integration working")
            else:
                results.add_test(f"Tool Integration ({expected_tool_type})", False, "No meaningful response")
                print(f"❌ {expected_tool_type} tool integration failed")
        
        return True
        
    except Exception as e:
        results.add_test("Tool Integration", False, str(e))
        print(f"❌ Tool integration error: {e}")
        return False


async def main():
    """Run all consolidated agent tests."""
    print("🚀 Comprehensive MCP Agent Test Suite")
    print("=" * 60)
    print("Testing agent functionality, memory, structured output, and integration")
    
    # Check for required environment variables
    if not os.getenv("BEDROCK_MODEL_ID"):
        print("\n⚠️ Warning: BEDROCK_MODEL_ID not set. Using default model.")
    
    # Run all test categories
    print("\n📋 Running Basic Tests...")
    await test_agent_initialization()
    await test_basic_query()
    
    print("\n📋 Running Advanced Features...")
    await test_structured_output()
    
    print("\n📋 Running Integration Tests...")
    await test_mcp_client_identification()
    await test_tool_integration()
    await test_error_handling()
    
    # Print consolidated results
    results.print_summary()
    
    return results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)