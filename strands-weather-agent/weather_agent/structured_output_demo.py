#!/usr/bin/env python3
"""
Demonstration of AWS Strands structured output for weather queries.
Run from weather_agent directory.

This example shows how the agent uses LLM geographic intelligence to:
1. Extract precise coordinates from location names
2. Call weather tools with coordinates directly
3. Return structured, validated responses
"""

import asyncio
import json
from .mcp_agent import MCPWeatherAgent
from .models.structured_responses import WeatherQueryResponse


async def demo_basic_weather():
    """Demonstrate basic weather query with structured output."""
    print("=== Basic Weather Query Demo ===\n")
    
    agent = MCPWeatherAgent(debug_logging=True)
    
    # Test connectivity first
    connectivity = await agent.test_connectivity()
    print(f"MCP Server Status: {connectivity}\n")
    
    # Query weather for a major city
    query = "What's the weather like in Chicago?"
    print(f"Query: {query}")
    
    response = await agent.query_structured(query)
    
    # Display structured response
    print(f"\nStructured Response:")
    print(f"- Query Type: {response.query_type}")
    print(f"- Query Confidence: {response.query_confidence}")
    
    # Display extracted location with LLM coordinates
    location = response.get_primary_location()
    print(f"\nExtracted Location (from LLM knowledge):")
    print(f"- Name: {location.name}")
    print(f"- Coordinates: {location.latitude}, {location.longitude}")
    print(f"- Timezone: {location.timezone}")
    print(f"- Country: {location.country_code}")
    print(f"- Confidence: {location.confidence}")
    print(f"- Source: {location.source}")
    
    # Display weather data if available
    if response.weather_data:
        print(f"\nWeather Data (from tools):")
        print(f"- Current Temp: {response.weather_data.current_temperature}°C")
        print(f"- Conditions: {response.weather_data.conditions}")
        print(f"- Humidity: {response.weather_data.humidity}%")
    
    print(f"\nSummary: {response.summary}")
    
    # Validate response
    validation = agent.validate_response(response)
    if validation.valid:
        print("\n✅ Response validation: PASSED")
    else:
        print(f"\n❌ Response validation: FAILED")
        print(validation.get_user_message())


async def demo_multiple_locations():
    """Demonstrate handling multiple locations."""
    print("\n\n=== Multiple Locations Demo ===\n")
    
    agent = MCPWeatherAgent(debug_logging=False)
    
    query = "Compare the weather between New York and London"
    print(f"Query: {query}")
    
    response = await agent.query_structured(query)
    
    print(f"\nExtracted {len(response.locations)} locations:")
    for i, loc in enumerate(response.locations, 1):
        print(f"\nLocation {i}:")
        print(f"- Name: {loc.name}")
        print(f"- Coordinates: {loc.latitude}, {loc.longitude}")
        print(f"- Timezone: {loc.timezone}")
        print(f"- Confidence: {loc.confidence}")


async def demo_ambiguous_location():
    """Demonstrate handling ambiguous locations."""
    print("\n\n=== Ambiguous Location Demo ===\n")
    
    agent = MCPWeatherAgent(debug_logging=False)
    
    query = "What's the weather in Springfield?"
    print(f"Query: {query}")
    
    response = await agent.query_structured(query)
    
    location = response.get_primary_location()
    print(f"\nLocation: {location.name}")
    print(f"Needs Clarification: {location.needs_clarification}")
    
    if location.needs_clarification and location.clarification_options:
        print(f"Clarification Options:")
        for option in location.clarification_options:
            print(f"- {option}")
    
    # Show clarification message
    if response.needs_clarification():
        print(f"\nClarification Message: {response.get_clarification_message()}")


async def demo_agricultural_query():
    """Demonstrate agricultural query with structured output."""
    print("\n\n=== Agricultural Query Demo ===\n")
    
    agent = MCPWeatherAgent(debug_logging=False)
    
    query = "Are conditions good for planting corn in Des Moines, Iowa?"
    print(f"Query: {query}")
    
    response = await agent.query_structured(query)
    
    print(f"\nQuery Type: {response.query_type}")
    
    location = response.get_primary_location()
    print(f"\nLocation:")
    print(f"- Name: {location.name}")
    print(f"- Coordinates: {location.latitude}, {location.longitude}")
    
    if response.agricultural_assessment:
        print(f"\nAgricultural Assessment:")
        print(f"- Planting Window: {response.agricultural_assessment.planting_window}")
        print(f"- Frost Risk: {response.agricultural_assessment.frost_risk}")
        print(f"- Soil Temperature Adequate: {response.agricultural_assessment.soil_temperature_adequate}")
        
        if response.agricultural_assessment.recommendations:
            print(f"\nRecommendations:")
            for rec in response.agricultural_assessment.recommendations:
                print(f"- {rec}")


async def demo_coordinate_extraction():
    """Demonstrate extraction of explicit coordinates."""
    print("\n\n=== Coordinate Extraction Demo ===\n")
    
    agent = MCPWeatherAgent(debug_logging=False)
    
    # Test various coordinate formats
    queries = [
        "Weather at 40.7128, -74.0060",
        "What's the temperature at latitude 51.5074 and longitude -0.1278?",
        "Forecast for coordinates: lat 35.6762, lon 139.6503"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        response = await agent.query_structured(query)
        
        location = response.get_primary_location()
        print(f"- Extracted: {location.latitude}, {location.longitude}")
        print(f"- Source: {location.source}")
        print(f"- Name: {location.name}")


async def demo_out_of_scope():
    """Demonstrate handling of out-of-scope queries."""
    print("\n\n=== Out of Scope Query Demo ===\n")
    
    agent = MCPWeatherAgent(debug_logging=False)
    
    query = "What's the latest stock market news?"
    print(f"Query: {query}")
    
    response = await agent.query_structured(query)
    
    print(f"\nResponse Summary: {response.summary}")
    print(f"Query Confidence: {response.query_confidence}")


async def main():
    """Run all demos."""
    print("AWS Strands Structured Output Demo")
    print("=" * 50)
    
    try:
        # Run demos in sequence
        await demo_basic_weather()
        await demo_multiple_locations()
        await demo_ambiguous_location()
        await demo_agricultural_query()
        await demo_coordinate_extraction()
        await demo_out_of_scope()
        
        print("\n\n✅ All demos completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())