"""
Test structured output implementation for weather agent.

Tests the native AWS Strands structured output capabilities with
geographic intelligence and response validation.
"""

import pytest
import asyncio
from weather_agent.mcp_agent import MCPWeatherAgent
from weather_agent.models.structured_responses import (
    WeatherQueryResponse, ExtractedLocation, ValidationResult
)


@pytest.mark.asyncio
async def test_structured_output_basic():
    """Test basic structured output functionality."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    # Test basic weather query
    response = await agent.query_structured("What's the weather in Chicago?")
    
    # Validate response type
    assert isinstance(response, WeatherQueryResponse)
    assert response.query_type in ["current", "forecast"]
    
    # Validate location extraction
    assert len(response.locations) >= 1
    chicago = response.get_primary_location()
    assert "Chicago" in chicago.name
    assert chicago.latitude is not None
    assert chicago.longitude is not None
    assert abs(chicago.latitude - 41.8781) < 0.1  # Close to expected
    assert abs(chicago.longitude - (-87.6298)) < 0.1
    assert chicago.timezone == "America/Chicago"
    assert chicago.country_code == "US"
    assert chicago.confidence >= 0.8
    
    # Validate summary
    assert response.summary
    assert len(response.summary) > 0


@pytest.mark.asyncio
async def test_geographic_intelligence():
    """Test LLM geographic knowledge for various locations."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    test_cases = [
        ("New York", 40.7128, -74.0060, "America/New_York"),
        ("London", 51.5074, -0.1278, "Europe/London"),
        ("Tokyo", 35.6762, 139.6503, "Asia/Tokyo"),
        ("Sydney", -33.8688, 151.2093, "Australia/Sydney"),
    ]
    
    for city, expected_lat, expected_lon, expected_tz in test_cases:
        response = await agent.query_structured(f"Weather in {city}")
        location = response.get_primary_location()
        
        assert city in location.name
        assert abs(location.latitude - expected_lat) < 0.1
        assert abs(location.longitude - expected_lon) < 0.1
        assert location.timezone == expected_tz
        assert location.confidence >= 0.8


@pytest.mark.asyncio
async def test_ambiguous_location_handling():
    """Test handling of ambiguous location names."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    # Query for ambiguous location
    response = await agent.query_structured("What's the weather in Springfield?")
    
    # Should either have clarification needed or multiple options
    location = response.get_primary_location()
    
    # Either needs clarification
    if location.needs_clarification:
        assert location.clarification_options is not None
        assert len(location.clarification_options) > 0
        assert any("IL" in opt or "Illinois" in opt for opt in location.clarification_options)
        assert any("MA" in opt or "Massachusetts" in opt for opt in location.clarification_options)
    else:
        # Or has lower confidence
        assert location.confidence < 0.8


@pytest.mark.asyncio
async def test_agricultural_query():
    """Test agricultural query with structured output."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    response = await agent.query_structured(
        "Are conditions good for planting corn in Iowa?"
    )
    
    assert response.query_type == "agricultural"
    assert len(response.locations) >= 1
    
    iowa_location = response.get_primary_location()
    assert "Iowa" in iowa_location.name
    assert iowa_location.latitude is not None
    assert iowa_location.longitude is not None
    
    # Should have agricultural assessment if available
    if response.agricultural_assessment:
        assert response.agricultural_assessment.planting_window is not None
        assert response.agricultural_assessment.frost_risk is not None


@pytest.mark.asyncio
async def test_coordinate_extraction():
    """Test extraction of explicit coordinates from queries."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    # Test explicit coordinates
    response = await agent.query_structured(
        "What's the weather at latitude 40.7128 and longitude -74.0060?"
    )
    
    location = response.get_primary_location()
    assert abs(location.latitude - 40.7128) < 0.001
    assert abs(location.longitude - (-74.0060)) < 0.001
    assert location.source in ["explicit", "llm_knowledge"]
    assert location.confidence >= 0.9


@pytest.mark.asyncio
async def test_response_validation():
    """Test response validation functionality."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    response = await agent.query_structured("Weather in Paris, France")
    
    # Validate the response
    validation = agent.validate_response(response)
    assert isinstance(validation, ValidationResult)
    
    # Should be valid for clear location
    assert validation.valid
    assert len(validation.errors) == 0
    
    # May have warnings depending on data availability
    if validation.warnings:
        print(f"Validation warnings: {validation.warnings}")


@pytest.mark.asyncio
async def test_out_of_scope_query():
    """Test handling of non-weather queries."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    response = await agent.query_structured("What's the latest news?")
    
    # Should indicate it's out of scope
    assert "weather" in response.summary.lower() or "agricultural" in response.summary.lower()
    assert response.query_confidence < 0.5 or "only provide" in response.summary


@pytest.mark.asyncio 
async def test_multiple_locations():
    """Test handling queries with multiple locations."""
    agent = MCPWeatherAgent(debug_logging=False)
    
    response = await agent.query_structured(
        "Compare weather between New York and Los Angeles"
    )
    
    # Should extract both locations
    assert len(response.locations) >= 2
    
    # Find NYC and LA
    location_names = [loc.name.lower() for loc in response.locations]
    assert any("new york" in name for name in location_names)
    assert any("los angeles" in name or "la" in name for name in location_names)
    
    # All locations should have coordinates
    for location in response.locations:
        assert location.latitude is not None
        assert location.longitude is not None
        assert location.confidence > 0.7


if __name__ == "__main__":
    # Run basic test
    asyncio.run(test_structured_output_basic())
    print("✅ Basic structured output test passed!")