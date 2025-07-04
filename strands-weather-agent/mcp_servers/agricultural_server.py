#!/usr/bin/env python3
"""
FastMCP server for agricultural weather conditions.
Returns raw JSON from the Open-Meteo API for LLM interpretation.
"""

from typing import Optional
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import shared utilities
from api_utils import get_coordinates, OpenMeteoClient

# Initialize FastMCP server
server = FastMCP(name="openmeteo-agricultural")
client = OpenMeteoClient()


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Simple health check endpoint for Docker health checks."""
    return JSONResponse({"status": "healthy", "service": "agricultural-server"})


@server.tool
async def get_agricultural_conditions(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    days: int = 7
) -> dict:
    """Get agricultural conditions with coordinate optimization.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    
    Args:
        location: Farm location (requires geocoding - slower)
        latitude: Direct latitude (-90 to 90) - PREFERRED
        longitude: Direct longitude (-180 to 180) - PREFERRED
        days: Forecast days (1-7)
    
    Returns:
        Structured agricultural data with soil moisture, evapotranspiration, and growing conditions
    """
    try:
        # Validate days parameter
        days = min(max(days, 1), 7)

        # Coordinate priority: direct coords > location name
        if latitude is not None and longitude is not None:
            coords = {"latitude": latitude, "longitude": longitude, "name": location or f"{latitude:.4f},{longitude:.4f}"}
        elif location:
            coords = await get_coordinates(location)
            if not coords:
                return {
                    "error": f"Could not find location: {location}. Please try a major city or farm name."
                }
        else:
            return {
                "error": "Either location name or coordinates (latitude, longitude) required"
            }

        # Get agricultural data with soil and ET parameters
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "forecast_days": days,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration,vapor_pressure_deficit_max",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,soil_temperature_0cm,soil_temperature_6cm,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
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
        data["summary"] = f"Agricultural conditions for {coords.get('name', location)} ({days} days) - Focus: Soil moisture, evapotranspiration, and growing conditions"
        
        return data
        
    except Exception as e:
        return {
            "error": f"Error getting agricultural conditions: {str(e)}"
        }


if __name__ == "__main__":
    # Start the server with HTTP transport
    import os
    host = os.getenv("MCP_HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8083"))
    print(f"Starting agricultural server on {host}:{port}")
    server.run(transport="streamable-http", host=host, port=port, path="/mcp")