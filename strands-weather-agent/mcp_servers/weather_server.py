#!/usr/bin/env python3
"""
Unified MCP server for all weather and agricultural data.
"""

import os
import logging
from typing import Optional, Union
from datetime import datetime, date, timedelta
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

try:
    from api_utils import get_coordinates, OpenMeteoClient, get_daily_params, get_hourly_params, API_TYPE_FORECAST, API_TYPE_ARCHIVE
    from models import ForecastRequest, HistoricalRequest, AgriculturalRequest
except ImportError:
    from .api_utils import get_coordinates, OpenMeteoClient, get_daily_params, get_hourly_params, API_TYPE_FORECAST, API_TYPE_ARCHIVE
    from .models import ForecastRequest, HistoricalRequest, AgriculturalRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = FastMCP(name="weather-mcp")
client = OpenMeteoClient()


@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy", 
        "service": "weather-server",
        "tools": ["get_weather_forecast", "get_historical_weather", "get_agricultural_conditions"]
    })


@server.tool
async def get_weather_forecast(request: ForecastRequest) -> dict:
    """Get weather forecast with coordinate optimization.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    Pydantic automatically handles type conversion from strings to floats.
    
    Args:
        request: ForecastRequest with location/coordinates and days
    
    Returns:
        Structured forecast data with location info, current conditions, and daily/hourly data
    """
    try:
        if request.latitude is not None and request.longitude is not None:
            coords = {
                "latitude": request.latitude, 
                "longitude": request.longitude, 
                "name": request.location or f"{request.latitude:.4f},{request.longitude:.4f}"
            }
        elif request.location:
            coords = await get_coordinates(request.location)
            if not coords:
                return {
                    "error": f"Could not find location: {request.location}. Please try a major city name."
                }
        else:
            return {
                "error": "Either location name or coordinates (latitude, longitude) required"
            }

        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "forecast_days": request.days,
            "daily": ",".join(get_daily_params()),
            "hourly": ",".join(get_hourly_params()),
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        data = await client.get(API_TYPE_FORECAST, params)
        
        data["location_info"] = {
            "name": coords.get("name", request.location),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        data["summary"] = f"Weather forecast for {coords.get('name', request.location)} ({request.days} days)"
        
        return data
        
    except Exception as e:
        return {
            "error": f"Error getting forecast: {str(e)}"
        }


@server.tool
async def get_historical_weather(request: HistoricalRequest) -> dict:
    """Get historical weather with coordinate optimization.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    Pydantic automatically handles type conversion and date validation.
    
    Args:
        request: HistoricalRequest with dates and location/coordinates
    
    Returns:
        Structured historical weather data with daily aggregates
    """
    try:
        start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(request.end_date, "%Y-%m-%d").date()
        
        min_date = date.today() - timedelta(days=5)
        if end > min_date:
            return {
                "error": f"Historical data only available before {min_date}. Use forecast API for recent dates."
            }

        if request.latitude is not None and request.longitude is not None:
            coords = {
                "latitude": request.latitude, 
                "longitude": request.longitude, 
                "name": request.location or f"{request.latitude:.4f},{request.longitude:.4f}"
            }
        elif request.location:
            coords = await get_coordinates(request.location)
            if not coords:
                return {
                    "error": f"Could not find location: {request.location}. Please try a major city name."
                }
        else:
            return {
                "error": "Either location name or coordinates (latitude, longitude) required"
            }

        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "daily": ",".join(get_daily_params()),
            "timezone": "auto"
        }
        
        data = await client.get(API_TYPE_ARCHIVE, params)
        
        data["location_info"] = {
            "name": coords.get("name", request.location or f"{coords['latitude']},{coords['longitude']}"),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        data["summary"] = f"Historical weather for {coords.get('name', request.location)} from {request.start_date} to {request.end_date}"
        
        return data
        
    except Exception as e:
        return {
            "error": f"Error getting historical data: {str(e)}"
        }


@server.tool
async def get_agricultural_conditions(request: AgriculturalRequest) -> dict:
    """Get agricultural conditions with coordinate optimization.
    
    Performance tip: Providing latitude/longitude is 3x faster than location name.
    Pydantic automatically handles type conversion from strings to floats.
    
    Args:
        request: AgriculturalRequest with location/coordinates and days
    
    Returns:
        Structured agricultural data with soil moisture, evapotranspiration, and growing conditions
    """
    try:
        if request.latitude is not None and request.longitude is not None:
            coords = {
                "latitude": request.latitude, 
                "longitude": request.longitude, 
                "name": request.location or f"{request.latitude:.4f},{request.longitude:.4f}"
            }
        elif request.location:
            coords = await get_coordinates(request.location)
            if not coords:
                return {
                    "error": f"Could not find location: {request.location}. Please try a major city or farm name."
                }
        else:
            return {
                "error": "Either location name or coordinates (latitude, longitude) required"
            }

        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "forecast_days": request.days,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration,vapor_pressure_deficit_max",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,soil_temperature_0cm,soil_temperature_6cm,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
            "timezone": "auto"
        }
        
        data = await client.get(API_TYPE_FORECAST, params)
        
        data["location_info"] = {
            "name": coords.get("name", request.location),
            "coordinates": {
                "latitude": coords["latitude"],
                "longitude": coords["longitude"]
            }
        }
        
        data["summary"] = f"Agricultural conditions for {coords.get('name', request.location)} ({request.days} days) - Focus: Soil moisture, evapotranspiration, and growing conditions"
        
        return data
        
    except Exception as e:
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
        default=int(os.getenv("MCP_PORT", "7778")),
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