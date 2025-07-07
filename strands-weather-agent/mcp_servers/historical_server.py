#!/usr/bin/env python3
"""
FastMCP server for OpenMeteo historical weather data.
Returns raw JSON from the Open-Meteo API for LLM interpretation.
"""

from typing import Optional, Union
from datetime import datetime, date, timedelta
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import shared utilities
from api_utils import get_coordinates, OpenMeteoClient, get_daily_params, get_hourly_params, API_TYPE_ARCHIVE, parse_coordinate

# Initialize FastMCP server
server = FastMCP(name="openmeteo-historical")
client = OpenMeteoClient()


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Simple health check endpoint for Docker health checks."""
    return JSONResponse({"status": "healthy", "service": "historical-server"})


@server.tool
async def get_historical_weather(
    start_date: str,
    end_date: str,
    location: Optional[str] = None,
    latitude: Optional[Union[str, float]] = None,
    longitude: Optional[Union[str, float]] = None
) -> dict:
    """Get historical weather with coordinate optimization.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        location: Location name (requires geocoding - slower)
        latitude: Direct latitude (-90 to 90) - PREFERRED (accepts string or float)
        longitude: Direct longitude (-180 to 180) - PREFERRED (accepts string or float)
    
    Returns:
        Structured historical weather data with daily aggregates
    """
    try:
        # Parse dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return {
                "error": "Invalid date format. Use YYYY-MM-DD."
            }
        
        if end < start:
            return {
                "error": "End date must be after start date."
            }
        
        min_date = date.today() - timedelta(days=5)
        if end > min_date:
            return {
                "error": f"Historical data only available before {min_date}. Use forecast API for recent dates."
            }

        # Parse coordinates if they are strings
        lat = parse_coordinate(latitude)
        lon = parse_coordinate(longitude)

        # Coordinate priority: direct coords > location name
        if lat is not None and lon is not None:
            coords = {"latitude": lat, "longitude": lon, "name": location or f"{lat:.4f},{lon:.4f}"}
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

        # Get historical data
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": ",".join(get_daily_params()),
            "timezone": "auto"
        }
        
        data = await client.get(API_TYPE_ARCHIVE, params)
        
        # Add location info
        data["location_info"] = {
            "name": coords.get("name", location or f"{latitude},{longitude}"),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        # Add summary
        data["summary"] = f"Historical weather for {coords.get('name', location)} from {start_date} to {end_date}"
        
        return data
        
    except Exception as e:
        return {
            "error": f"Error getting historical data: {str(e)}"
        }


if __name__ == "__main__":
    # Start the server with HTTP transport
    import os
    host = os.getenv("MCP_HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "7779"))
    print(f"Starting historical server on {host}:{port}")
    server.run(transport="streamable-http", host=host, port=port, path="/mcp")