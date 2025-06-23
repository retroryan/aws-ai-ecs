#!/usr/bin/env python3
"""
FastMCP server for OpenMeteo weather forecast tool.
Returns raw JSON from the Open-Meteo API for LLM interpretation.
"""

import json
from typing import Optional
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import shared utilities
from api_utils import get_coordinates, OpenMeteoClient, get_daily_params, get_hourly_params

# Initialize FastMCP server
server = FastMCP(name="openmeteo-forecast")
client = OpenMeteoClient()


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Simple health check endpoint for Docker health checks."""
    return JSONResponse({"status": "healthy", "service": "forecast-server"})


@server.tool
async def get_weather_forecast(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    days: int = 7
) -> dict:
    """Get weather forecast with coordinate optimization.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    
    Args:
        location: Location name (requires geocoding - slower)
        latitude: Direct latitude (-90 to 90) - PREFERRED
        longitude: Direct longitude (-180 to 180) - PREFERRED
        days: Forecast days (1-16)
    
    Returns:
        Structured forecast data with location info, current conditions, and daily/hourly data
    """
    try:
        # Validate days parameter
        days = min(max(days, 1), 16)

        # Coordinate priority: direct coords > location name
        if latitude is not None and longitude is not None:
            coords = {"latitude": latitude, "longitude": longitude, "name": location or f"{latitude:.4f},{longitude:.4f}"}
        elif location:
            coords = await get_coordinates(location)
            if not coords:
                return {
                    "error": f"Could not find location: {location}. Please try a major city name."
                }
        else:
            return {
                "error": "Either location name or coordinates (latitude, longitude) required"
            }

        # Get forecast data
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "forecast_days": days,
            "daily": ",".join(get_daily_params()),
            "hourly": ",".join(get_hourly_params()),
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        data = await client.get("forecast", params)
        
        # Add location info
        data["location_info"] = {
            "name": coords.get("name", location),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        # Add summary
        data["summary"] = f"Weather forecast for {coords.get('name', location)} ({days} days)"
        
        return data
        
    except Exception as e:
        return {
            "error": f"Error getting forecast: {str(e)}"
        }


if __name__ == "__main__":
    # Start the server with HTTP transport
    import os
    host = os.getenv("MCP_HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8081"))
    print(f"Starting forecast server on {host}:{port}")
    server.run(transport="streamable-http", host=host, port=port, path="/mcp")