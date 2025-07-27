#!/usr/bin/env python3
"""
Consolidated coordinate tests for the AWS Strands Weather Agent.

This file combines all coordinate-related tests from:
- test_coordinate_handling.py
- test_coordinate_usage.py  
- test_coordinates.py
- test_simple_coordinate.py
- test_diverse_cities.py

Tests the agent's ability to:
1. Extract coordinates from LLM geographic knowledge
2. Handle user-provided coordinates
3. Fall back to geocoding when needed
4. Process global city locations
5. Demonstrate performance improvements
"""

import asyncio
import sys
import os
import time
import pytest
from typing import List, Tuple, Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weather_agent.mcp_agent import MCPWeatherAgent
from weather_agent.models.structured_responses import WeatherQueryResponse, ExtractedLocation


# Test data for global cities
GLOBAL_CITIES = [
    # Format: (city_name, expected_lat, expected_lon, timezone, country_code)
    ("New York, NY", 40.7128, -74.0060, "America/New_York", "US"),
    ("Los Angeles, CA", 34.0522, -118.2437, "America/Los_Angeles", "US"),
    ("Chicago, IL", 41.8781, -87.6298, "America/Chicago", "US"),
    ("London, UK", 51.5074, -0.1278, "Europe/London", "GB"),
    ("Paris, France", 48.8566, 2.3522, "Europe/Paris", "FR"),
    ("Tokyo, Japan", 35.6762, 139.6503, "Asia/Tokyo", "JP"),
    ("Sydney, Australia", -33.8688, 151.2093, "Australia/Sydney", "AU"),
    ("São Paulo, Brazil", -23.5505, -46.6333, "America/Sao_Paulo", "BR"),
    ("Mumbai, India", 19.0760, 72.8777, "Asia/Kolkata", "IN"),
    ("Cairo, Egypt", 30.0444, 31.2357, "Africa/Cairo", "EG"),
    ("Berlin, Germany", 52.5200, 13.4050, "Europe/Berlin", "DE"),
    ("Moscow, Russia", 55.7558, 37.6173, "Europe/Moscow", "RU"),
    ("Singapore", 1.3521, 103.8198, "Asia/Singapore", "SG"),
    ("Dubai, UAE", 25.2048, 55.2708, "Asia/Dubai", "AE"),
    ("Cape Town, South Africa", -33.9249, 18.4241, "Africa/Johannesburg", "ZA")
]

# Ambiguous city names for testing
AMBIGUOUS_CITIES = [
    "Springfield",  # Multiple in US
    "Portland",     # Oregon vs Maine
    "Cambridge",    # UK vs Massachusetts
    "Richmond",     # Virginia vs UK
    "Alexandria"    # Egypt vs Virginia
]

# Cities with special characters for Unicode testing
SPECIAL_CHAR_CITIES = [
    ("Zürich, Switzerland", 47.3769, 8.5417, "Europe/Zurich", "CH"),
    ("København, Denmark", 55.6761, 12.5683, "Europe/Copenhagen", "DK"),
    ("München, Germany", 48.1351, 11.5820, "Europe/Berlin", "DE"),
    ("São Paulo, Brazil", -23.5505, -46.6333, "America/Sao_Paulo", "BR"),
    ("Montréal, Canada", 45.5017, -73.5673, "America/Toronto", "CA")
]


@pytest.fixture
async def weather_agent():
    """Create and initialize a weather agent for testing."""
    agent = MCPWeatherAgent(debug_logging=False)
    # Note: Actual initialization happens within query context
    yield agent
    # Cleanup handled by context managers


class TestCoordinateExtraction:
    """Test the agent's ability to extract coordinates from queries."""
    
    @pytest.mark.asyncio
    async def test_llm_coordinate_knowledge(self, weather_agent):
        """Test that LLM provides coordinates from its knowledge."""
        test_cases = [
            ("What's the weather in New York?", 40.7128, -74.0060),
            ("Current conditions in Tokyo", 35.6762, 139.6503),
            ("Tell me about London weather", 51.5074, -0.1278),
        ]
        
        for query, expected_lat, expected_lon in test_cases:
            response = await weather_agent.query(query)
            assert len(response.locations) > 0
            
            location = response.locations[0]
            assert abs(location.latitude - expected_lat) < 0.1
            assert abs(location.longitude - expected_lon) < 0.1
            assert location.source == "llm_knowledge"
            assert location.confidence >= 0.8
    
    @pytest.mark.asyncio
    async def test_explicit_coordinates(self, weather_agent):
        """Test handling of user-provided coordinates."""
        queries = [
            "What's the weather at 40.7128, -74.0060?",
            "Weather for latitude 51.5074, longitude -0.1278",
            "Conditions at lat: 35.6762, lon: 139.6503"
        ]
        
        for query in queries:
            response = await weather_agent.query(query)
            assert len(response.locations) > 0
            assert response.locations[0].source in ["explicit", "llm_knowledge"]
    
    @pytest.mark.asyncio
    async def test_ambiguous_locations(self, weather_agent):
        """Test handling of ambiguous city names."""
        for city in AMBIGUOUS_CITIES[:3]:  # Test first 3
            response = await weather_agent.query(f"Weather in {city}")
            
            # Should either have clarification options or lower confidence
            location = response.locations[0]
            if location.needs_clarification:
                assert location.clarification_options is not None
                assert len(location.clarification_options) > 0
            else:
                # If no clarification, confidence should be lower
                assert location.confidence < 0.8


class TestGlobalCityCoverage:
    """Test coverage of cities around the world."""
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("city_info", GLOBAL_CITIES[:5])  # Test subset
    async def test_global_city_coordinates(self, weather_agent, city_info):
        """Test coordinate extraction for global cities."""
        city_name, expected_lat, expected_lon, timezone, country_code = city_info
        
        response = await weather_agent.query(f"What's the weather in {city_name}?")
        
        assert len(response.locations) > 0
        location = response.locations[0]
        
        # Check coordinates (allow some variance)
        assert abs(location.latitude - expected_lat) < 0.5
        assert abs(location.longitude - expected_lon) < 0.5
        
        # Check metadata
        assert location.country_code == country_code
        assert location.confidence >= 0.7
    
    @pytest.mark.asyncio
    async def test_agricultural_coordinates(self, weather_agent):
        """Test coordinate handling for agricultural queries."""
        queries = [
            "What are the planting conditions in Des Moines, Iowa?",
            "Check frost risk at 42.0, -94.0 for my corn field",
            "Agricultural forecast for the Corn Belt region"
        ]
        
        for query in queries:
            response = await weather_agent.query(query)
            assert response.query_type == "agricultural"
            assert len(response.locations) > 0
            
            # Agricultural queries should have assessment
            if "frost" in query or "planting" in query:
                assert response.agricultural_assessment is not None


class TestPerformanceComparison:
    """Test performance improvements with direct coordinates."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_coordinate_performance(self, weather_agent):
        """Compare performance of coordinate vs location name queries."""
        # Test with location name (may require geocoding)
        start = time.time()
        response1 = await weather_agent.query("Weather in Chicago")
        name_time = time.time() - start
        
        # Test with coordinates (no geocoding needed)
        start = time.time()
        response2 = await weather_agent.query(
            "Weather at 41.8781, -87.6298"
        )
        coord_time = time.time() - start
        
        # Both should return Chicago weather
        assert len(response1.locations) > 0
        assert len(response2.locations) > 0
        
        # Log performance difference
        if name_time > coord_time:
            improvement = name_time / coord_time
            print(f"\n🚀 Coordinates {improvement:.1f}x faster than location names")
        
        # Coordinates should generally be faster or equal
        assert coord_time <= name_time * 1.5  # Allow some variance


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_coordinates(self, weather_agent):
        """Test handling of invalid coordinates."""
        invalid_queries = [
            "Weather at latitude 91, longitude 0",  # Invalid latitude
            "Weather at 0, 181",  # Invalid longitude
            "Weather at lat: -91, lon: 0"  # Invalid latitude
        ]
        
        for query in invalid_queries:
            response = await weather_agent.query(query)
            # Should either correct or warn about invalid coordinates
            validation = weather_agent.validate_response(response)
            assert len(validation.errors) > 0 or len(validation.warnings) > 0
    
    @pytest.mark.asyncio
    async def test_empty_location_with_coordinates(self, weather_agent):
        """Test empty location string with valid coordinates."""
        response = await weather_agent.query(
            "Weather at location '' with coordinates 40.7128, -74.0060"
        )
        
        # Should handle empty location gracefully
        assert len(response.locations) > 0
        location = response.locations[0]
        assert abs(location.latitude - 40.7128) < 0.001
        assert abs(location.longitude - (-74.0060)) < 0.001
    
    @pytest.mark.asyncio
    async def test_custom_location_names(self, weather_agent):
        """Test preservation of custom location names with coordinates."""
        custom_queries = [
            "Weather at 'My Farm' (41.5908, -93.6208)",
            "Conditions at 'Secret Spot' latitude 35.6762, longitude 139.6503",
            "Temperature at 'Home Base' 51.5074, -0.1278"
        ]
        
        for query in custom_queries:
            response = await weather_agent.query(query)
            assert len(response.locations) > 0
            # Custom names might be preserved or replaced with geographic names
    
    @pytest.mark.asyncio
    async def test_fictional_locations(self, weather_agent):
        """Test handling of fictional or non-existent locations."""
        fictional = [
            "Weather in Atlantis",
            "What's the temperature in Hogwarts?",
            "Forecast for Middle Earth"
        ]
        
        for query in fictional:
            response = await weather_agent.query(query)
            # Should indicate low confidence or need clarification
            if len(response.locations) > 0:
                location = response.locations[0]
                assert location.confidence < 0.5 or location.needs_clarification
    
    @pytest.mark.asyncio
    async def test_multiple_locations(self, weather_agent):
        """Test queries with multiple locations."""
        query = "Compare weather between New York and London"
        response = await weather_agent.query(query)
        
        # Should extract both locations
        assert len(response.locations) >= 2
        
        # Check both locations are identified
        location_names = [loc.name.lower() for loc in response.locations]
        assert any("new york" in name for name in location_names)
        assert any("london" in name for name in location_names)
    
    @pytest.mark.asyncio
    async def test_special_character_cities(self, weather_agent):
        """Test cities with special Unicode characters."""
        for city_info in SPECIAL_CHAR_CITIES[:3]:  # Test first 3
            city_name, expected_lat, expected_lon, _, _ = city_info
            
            response = await weather_agent.query(
                f"What's the weather in {city_name}?"
            )
            
            assert len(response.locations) > 0
            location = response.locations[0]
            
            # Should handle special characters correctly
            assert abs(location.latitude - expected_lat) < 0.5
            assert abs(location.longitude - expected_lon) < 0.5
            assert location.confidence >= 0.7


class TestDirectMCPServer:
    """Test MCP servers directly without agent layer."""
    
    @pytest.mark.asyncio
    async def test_forecast_server_coordinates(self):
        """Test forecast server's coordinate handling directly."""
        import httpx
        from mcp import Client
        from mcp.client.stdio import stdio_client
        
        # This test requires the forecast server to be running
        try:
            # Check if server is running
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:7778/health")
                if response.status_code != 200:
                    pytest.skip("Forecast server not running")
        except:
            pytest.skip("Forecast server not running")
        
        # Test would go here - marking as placeholder
        # Direct MCP protocol testing is complex and requires server running
        pass


# Integration test functions (for non-pytest execution)
async def test_coordinates_simple():
    """Simple coordinate test for direct execution."""
    agent = MCPWeatherAgent(debug_logging=True)
    
    print("\n" + "="*60)
    print("🧪 Testing Coordinate Features")
    print("="*60 + "\n")
    
    # Test cases
    test_cases = [
        {
            "name": "1. LLM Geographic Knowledge",
            "query": "What's the weather in Des Moines, Iowa?",
            "expected": "Should use LLM knowledge for coordinates"
        },
        {
            "name": "2. User-Provided Coordinates",
            "query": "What's the weather at latitude 41.5868, longitude -93.6250?",
            "expected": "Should use provided coordinates directly"
        },
        {
            "name": "3. Ambiguous Location",
            "query": "What's the weather in Springfield?",
            "expected": "Should request clarification or show options"
        },
        {
            "name": "4. Agricultural Coordinates",
            "query": "Check planting conditions at 42.0, -94.0 (my corn field)",
            "expected": "Should provide agricultural assessment"
        },
        {
            "name": "5. Global City Test",
            "query": "What's the weather in Tokyo, Japan?",
            "expected": "Should extract Tokyo coordinates from LLM knowledge"
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected']}")
        print("-" * 60)
        
        try:
            # Use structured output for better visibility
            response = await agent.query(test['query'])
            print(f"✅ Query Type: {response.query_type}")
            print(f"✅ Locations Found: {len(response.locations)}")
            
            for loc in response.locations:
                print(f"   - {loc.name}: ({loc.latitude}, {loc.longitude})")
                print(f"     Source: {loc.source}, Confidence: {loc.confidence}")
                if loc.needs_clarification:
                    print(f"     Clarification needed: {loc.clarification_options}")
            
            print(f"✅ Summary: {response.summary[:200]}...")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    # Performance comparison
    print("\n\n" + "="*60)
    print("⏱️  Performance Comparison")
    print("="*60 + "\n")
    
    # Test with location name
    start = time.time()
    response1 = await agent.query("Weather in Berlin, Germany")
    name_time = time.time() - start
    print(f"With location name: {name_time:.2f} seconds")
    print(f"  Source: {response1.locations[0].source if response1.locations else 'unknown'}")
    
    # Test with coordinates
    start = time.time()
    response2 = await agent.query("Weather at 52.5200, 13.4050")
    coord_time = time.time() - start
    print(f"With coordinates: {coord_time:.2f} seconds")
    print(f"  Source: {response2.locations[0].source if response2.locations else 'unknown'}")
    
    if name_time > coord_time:
        print(f"\n🚀 Coordinates {name_time/coord_time:.1f}x faster!")
    else:
        print(f"\n📊 Similar performance (LLM provided coordinates quickly)")


async def run_all_coordinate_tests():
    """Run all coordinate tests comprehensively."""
    print("\n" + "="*60)
    print("🌍 Comprehensive Coordinate Testing")
    print("="*60 + "\n")
    
    agent = MCPWeatherAgent(debug_logging=False)
    
    # Test 1: Global city coverage
    print("\n📍 Testing Global City Coverage...")
    for city_info in GLOBAL_CITIES[:5]:  # Test first 5 cities
        city_name = city_info[0]
        response = await agent.query(f"Weather in {city_name}")
        if response.locations:
            loc = response.locations[0]
            print(f"✅ {city_name}: ({loc.latitude}, {loc.longitude}) - {loc.timezone}")
        else:
            print(f"❌ {city_name}: No location extracted")
    
    # Test 2: Ambiguous locations
    print("\n🤔 Testing Ambiguous Locations...")
    for city in AMBIGUOUS_CITIES[:3]:
        response = await agent.query(f"Weather in {city}")
        if response.locations:
            loc = response.locations[0]
            if loc.needs_clarification:
                print(f"✅ {city}: Needs clarification - {loc.clarification_options}")
            else:
                print(f"📍 {city}: Resolved to {loc.name} (confidence: {loc.confidence})")
    
    # Test 3: Special characters
    print("\n🌏 Testing Special Character Cities...")
    for city_info in SPECIAL_CHAR_CITIES[:3]:
        city_name = city_info[0]
        response = await agent.query(f"Weather in {city_name}")
        if response.locations:
            loc = response.locations[0]
            print(f"✅ {city_name}: Successfully handled")
        else:
            print(f"❌ {city_name}: Failed to extract location")
    
    # Test 4: Success rate calculation
    print("\n📊 Calculating Success Rate...")
    total_tests = 0
    successful_tests = 0
    
    test_queries = [
        "Weather in New York",
        "Temperature in Paris",
        "Is it raining in London?",
        "Weather at 40.7128, -74.0060",
        "Conditions in Springfield"
    ]
    
    for query in test_queries:
        total_tests += 1
        try:
            response = await agent.query(query)
            if response.locations and response.locations[0].latitude:
                successful_tests += 1
        except:
            pass
    
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"Success Rate: {successful_tests}/{total_tests} ({success_rate:.1f}%)")
    
    # Test 5: Validation  
    print("\n✔️  Testing Response Validation...")
    response = await agent.query("Weather at invalid coordinates 91, 181")
    validation = agent.validate_response(response)
    if validation.errors or validation.warnings:
        print(f"✅ Validation caught issues: {validation.errors or validation.warnings}")
    else:
        print("❌ Validation missed invalid coordinates")
    
    print("\n✅ All coordinate tests completed!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--simple":
        # Run simple test
        asyncio.run(test_coordinates_simple())
    elif len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Run comprehensive tests
        asyncio.run(run_all_coordinate_tests())
    else:
        # Run pytest if available, otherwise simple test
        try:
            import pytest
            sys.exit(pytest.main([__file__, "-v"]))
        except ImportError:
            print("pytest not available, running simple tests...")
            asyncio.run(test_coordinates_simple())