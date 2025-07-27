#!/usr/bin/env python3
"""
Unified MCP server for all weather and agricultural data.
Consolidates forecast, historical, and agricultural servers into one.
"""

import os
import logging
from typing import Optional
from datetime import datetime, date, timedelta
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

# Import shared utilities
from api_utils import get_coordinates, OpenMeteoClient, get_daily_params, get_hourly_params

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
server = FastMCP(name="weather-mcp")
client = OpenMeteoClient()


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint for Docker health checks."""
    return JSONResponse({
        "status": "healthy", 
        "service": "weather-server",
        "tools": ["get_weather_forecast", "get_historical_weather", "get_agricultural_conditions"]
    })


@server.tool
async def get_weather_forecast(
    location: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    days: int = 7
) -> dict:
    """Get weather forecast data from Open-Meteo API as JSON.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    
    Args:
        location: Location name (e.g., 'Des Moines, Iowa')
        latitude: Latitude (optional, overrides location if provided)
        longitude: Longitude (optional, overrides location if provided)
        days: Number of forecast days (1-16)
    
    Returns:
        Weather forecast data as JSON with location info, current conditions, and daily/hourly data
    """
    try:
        # Validate days parameter
        days = min(max(days, 1), 16)

        # Use coordinates if provided, else geocode
        if latitude is not None and longitude is not None:
            coords = {"latitude": latitude, "longitude": longitude, "name": location or f"{latitude},{longitude}"}
        else:
            coords = await get_coordinates(location)
            if not coords:
                return {
                    "error": f"Could not find location: {location}. Please try a major city name."
                }

        # Get weather data with all parameters
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
        
        # Add location info to response
        data["location_info"] = {
            "name": coords.get("name", location),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        data["summary"] = f"Weather forecast for {coords.get('name', location)} ({days} days)"
        
        return data
        
    except Exception as e:
        logger.error(f"Error in get_weather_forecast: {str(e)}")
        return {
            "error": f"Error getting forecast: {str(e)}"
        }


@server.tool
async def get_historical_weather(
    start_date: str,
    end_date: str,
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> dict:
    """Get historical weather data from Open-Meteo API as JSON.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        location: Location name (e.g., 'Des Moines, Iowa')
        latitude: Latitude (optional, overrides location if provided)
        longitude: Longitude (optional, overrides location if provided)
    
    Returns:
        Historical weather data as JSON with daily aggregates
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
                "error": "End date must be after or equal to start date."
            }
        
        # Check that dates are in the past (at least 5 days ago)
        min_date = date.today() - timedelta(days=5)
        if end > min_date:
            return {
                "error": f"Historical data only available before {min_date}. Use forecast API for recent dates."
            }

        # Get location coordinates
        if latitude is not None and longitude is not None:
            coords = {"latitude": latitude, "longitude": longitude, "name": location or f"{latitude},{longitude}"}
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
        
        data = await client.get("archive", params)
        
        # Add location info to response
        data["location_info"] = {
            "name": coords.get("name", location or f"{coords['latitude']},{coords['longitude']}"),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        data["summary"] = f"Historical weather for {coords.get('name', location)} from {start_date} to {end_date}"
        
        return data
        
    except Exception as e:
        logger.error(f"Error in get_historical_weather: {str(e)}")
        return {
            "error": f"Error getting historical data: {str(e)}"
        }


@server.tool
async def get_agricultural_conditions(
    location: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    days: int = 7
) -> dict:
    """Get agricultural weather conditions including soil moisture and evapotranspiration as JSON.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    
    Args:
        location: Farm location (e.g., 'Ames, Iowa')
        latitude: Latitude (optional, overrides location if provided)
        longitude: Longitude (optional, overrides location if provided)
        days: Number of forecast days (1-7)
    
    Returns:
        Agricultural weather conditions data as JSON with soil moisture, evapotranspiration, and growing conditions
    """
    try:
        # Validate days parameter
        days = min(max(days, 1), 7)

        # Use coordinates if provided, else geocode
        if latitude is not None and longitude is not None:
            coords = {"latitude": latitude, "longitude": longitude, "name": location or f"{latitude},{longitude}"}
        else:
            coords = await get_coordinates(location)
            if not coords:
                return {
                    "error": f"Could not find location: {location}. Please try a major city or farm name."
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
        
        # Add location info to response
        data["location_info"] = {
            "name": coords.get("name", location),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        data["summary"] = f"Agricultural conditions for {coords.get('name', location)} ({days} days) - Focus: Soil moisture, evapotranspiration, and growing conditions"
        
        return data
        
    except Exception as e:
        logger.error(f"Error in get_agricultural_conditions: {str(e)}")
        return {
            "error": f"Error getting agricultural conditions: {str(e)}"
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Unified MCP Weather Server")
    parser.add_argument(
        "--transport",
        "-t",
        choices=["stdio", "http", "sse", "streamable-http"],
        default="streamable-http",
        help="Transport protocol to use (default: streamable-http)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv(
            "MCP_HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1"
        ),
        help="Host to bind to (for HTTP transports)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "7071")),  # Use same port as old forecast server
        help="Port to bind to (for HTTP transports)",
    )
    parser.add_argument(
        "--path",
        default="/mcp",
        help="URL path for HTTP transports (default: /mcp)",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        print(f"Starting unified weather server on {args.host}:{args.port}{args.path}")
        print("Available tools:")
        print("  - get_weather_forecast")
        print("  - get_historical_weather")
        print("  - get_agricultural_conditions")
        server.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
            path=args.path,
        )