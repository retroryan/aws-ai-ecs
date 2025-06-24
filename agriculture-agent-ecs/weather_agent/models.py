"""
Data models for the weather agent system.

This module contains all Pydantic models used throughout the weather agent,
including structured output models for LangGraph and query classification.
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


# Structured Output Models for LangGraph
class WeatherCondition(BaseModel):
    """Current weather condition."""
    temperature: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity: Optional[int] = Field(None, description="Relative humidity percentage")
    precipitation: Optional[float] = Field(None, description="Current precipitation in mm")
    wind_speed: Optional[float] = Field(None, description="Wind speed in km/h")
    conditions: Optional[str] = Field(None, description="Weather description")


class DailyForecast(BaseModel):
    """Daily weather forecast."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    temperature_max: Optional[float] = Field(None, description="Maximum temperature in Celsius")
    temperature_min: Optional[float] = Field(None, description="Minimum temperature in Celsius")
    precipitation_sum: Optional[float] = Field(None, description="Total precipitation in mm")
    conditions: Optional[str] = Field(None, description="Weather conditions summary")


class OpenMeteoResponse(BaseModel):
    """Structured response consolidating Open-Meteo data."""
    location: str = Field(..., description="Location name")
    coordinates: Optional[Any] = Field(None, description="Latitude and longitude")
    timezone: Optional[str] = Field(None, description="Timezone")
    current_conditions: Optional[WeatherCondition] = Field(None, description="Current weather")
    daily_forecast: Optional[List[DailyForecast]] = Field(None, description="Daily forecast data")
    summary: str = Field(..., description="Natural language summary")
    data_source: str = Field(default="Open-Meteo API", description="Data source")


class AgricultureAssessment(BaseModel):
    """Agricultural conditions assessment."""
    location: str = Field(..., description="Location name")
    soil_temperature: Optional[float] = Field(None, description="Soil temperature in Celsius")
    soil_moisture: Optional[float] = Field(None, description="Soil moisture content")
    evapotranspiration: Optional[float] = Field(None, description="Daily evapotranspiration in mm")
    planting_conditions: str = Field(..., description="Assessment of planting conditions")
    recommendations: List[str] = Field(default_factory=list, description="Farming recommendations")
    summary: str = Field(..., description="Natural language summary")


# Query Classification Models (from the /models/ directory)
class QueryType(str, Enum):
    """Types of weather queries."""
    FORECAST = "forecast"
    HISTORICAL = "historical"
    AGRICULTURAL = "agricultural"
    GENERAL = "general"
    COMPARISON = "comparison"
    ALERT = "alert"


class Coordinates(BaseModel):
    """Geographic coordinates."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class LocationInfo(BaseModel):
    """Complete location information including coordinates."""
    raw_location: str = Field(..., description="Original location string from query")
    normalized_name: str = Field(..., description="Normalized location name")
    coordinates: Optional[Coordinates] = Field(None, description="Geographic coordinates if determined")
    location_type: str = Field(default="city", description="Type of location (city, region, etc.)")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in location identification")


class TimeRange(BaseModel):
    """Time range for queries."""
    start_date: Optional[str] = Field(None, description="Start date in ISO format")
    end_date: Optional[str] = Field(None, description="End date in ISO format")
    relative_reference: Optional[str] = Field(None, description="Relative time reference (e.g., 'next week')")
    is_historical: bool = Field(False, description="Whether this is a historical query")


class WeatherParameter(str, Enum):
    """Available weather parameters."""
    TEMPERATURE = "temperature"
    PRECIPITATION = "precipitation"
    HUMIDITY = "humidity"
    WIND = "wind"
    PRESSURE = "pressure"
    UV_INDEX = "uv_index"
    VISIBILITY = "visibility"
    GENERAL = "general"


class EnhancedQueryClassification(BaseModel):
    """Enhanced classification of user weather queries."""
    query_type: QueryType = Field(..., description="Type of weather query")
    locations: List[LocationInfo] = Field(..., description="Extracted location information")
    time_range: Optional[TimeRange] = Field(None, description="Time range for the query")
    weather_parameters: List[WeatherParameter] = Field(default_factory=list, description="Specific weather parameters requested")
    intent_summary: str = Field(..., description="Brief summary of user intent")
    requires_clarification: bool = Field(False, description="Whether the query needs clarification")
    clarification_reason: Optional[str] = Field(None, description="Reason why clarification is needed")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Overall confidence in classification")