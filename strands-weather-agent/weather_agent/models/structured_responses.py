"""
Structured response models for AWS Strands weather agent.

These models implement true structured output using AWS Strands native capabilities,
trusting foundation model intelligence for geographic knowledge rather than manual extraction.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class ExtractedLocation(BaseModel):
    """Location information extracted directly from LLM geographic knowledge."""
    name: str = Field(..., description="Full standardized location name (City, State/Province, Country)")
    latitude: float = Field(..., ge=-90, le=90, description="Precise latitude coordinate from LLM knowledge")
    longitude: float = Field(..., ge=-180, le=180, description="Precise longitude coordinate from LLM knowledge")
    timezone: str = Field(..., description="IANA timezone identifier (e.g., 'America/New_York')")
    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code (e.g., 'US', 'CA', 'GB')")
    confidence: float = Field(1.0, ge=0, le=1, description="LLM confidence in location identification")
    source: Literal["explicit", "inferred", "llm_knowledge"] = Field(
        "llm_knowledge", 
        description="Source of coordinates: 'explicit' from user, 'inferred' from context, 'llm_knowledge' from model"
    )
    needs_clarification: bool = Field(False, description="Whether location is ambiguous and needs user clarification")
    clarification_options: Optional[List[str]] = Field(
        None, 
        description="Alternative location options if ambiguous (e.g., ['Springfield, IL', 'Springfield, MA'])"
    )
    
    @field_validator('latitude', 'longitude')
    def validate_coordinates(cls, v):
        """Ensure coordinates are provided with reasonable precision."""
        if v is None:
            raise ValueError("Coordinate must be provided - trust LLM geographic knowledge")
        # Round to 4 decimal places for consistency
        return round(v, 4)
    
    def display_name(self) -> str:
        """Get formatted display name."""
        return self.name
    
    def has_high_confidence(self) -> bool:
        """Check if location has high confidence."""
        return self.confidence >= 0.8 and not self.needs_clarification


class WeatherDataSummary(BaseModel):
    """Summary of weather data from tool execution results."""
    current_temperature: Optional[float] = Field(None, description="Current temperature in Celsius from weather API")
    feels_like: Optional[float] = Field(None, description="Apparent temperature in Celsius")
    conditions: str = Field(..., description="Current weather conditions description")
    humidity: Optional[int] = Field(None, ge=0, le=100, description="Relative humidity percentage")
    wind_speed: Optional[float] = Field(None, ge=0, description="Wind speed in km/h")
    precipitation: Optional[float] = Field(None, ge=0, description="Precipitation amount in mm")
    
    forecast_summary: Optional[str] = Field(None, description="Natural language forecast summary")
    forecast_days: Optional[int] = Field(None, description="Number of forecast days provided")
    
    def has_current_data(self) -> bool:
        """Check if current weather data is available."""
        return self.current_temperature is not None


class AgriculturalAssessment(BaseModel):
    """Agricultural conditions and recommendations for farming activities."""
    soil_temperature_adequate: Optional[bool] = Field(
        None, 
        description="Whether current soil temperature is adequate for planting specific crops (based on weather data and seasonal analysis)"
    )
    frost_risk: Literal["low", "medium", "high", "none"] = Field(
        "none", 
        description="Assessment of frost risk in the next 7-14 days: 'none' = no risk, 'low' = minimal risk, 'medium' = moderate risk, 'high' = significant risk expected"
    )
    planting_window: Literal["optimal", "suboptimal", "poor", "not_recommended"] = Field(
        "not_recommended",
        description="Overall assessment of current planting conditions: 'optimal' = ideal conditions, 'suboptimal' = acceptable with care, 'poor' = challenging conditions, 'not_recommended' = avoid planting"
    )
    growing_degree_days: Optional[float] = Field(
        None, 
        description="Accumulated growing degree days (GDD) for the current season, calculated from temperature data to assess crop development potential"
    )
    moisture_conditions: Optional[str] = Field(
        None, 
        description="Assessment of soil moisture levels based on recent precipitation and weather patterns (e.g., 'adequate', 'dry', 'saturated')"
    )
    recommendations: List[str] = Field(
        default_factory=list, 
        description="Specific actionable agricultural recommendations based on current and forecasted weather conditions"
    )
    warnings: List[str] = Field(
        default_factory=list, 
        description="Important agricultural warnings or cautions about weather-related risks to crops or farming activities"
    )


class WeatherQueryResponse(BaseModel):
    """
    Comprehensive structured response for weather queries.
    
    This model combines LLM geographic intelligence with weather tool results,
    representing the final structured output from the agent.
    """
    # Query understanding
    query_type: Literal["current", "forecast", "historical", "agricultural", "general"] = Field(
        ..., 
        description="Classified type of weather query: 'current' = current conditions, 'forecast' = future predictions, 'historical' = past weather data, 'agricultural' = farming-related, 'general' = unspecified or mixed"
    )
    query_confidence: float = Field(
        1.0, 
        ge=0, 
        le=1, 
        description="Agent's confidence in correctly interpreting the user's query intent (0.0 = uncertain, 1.0 = highly confident)"
    )
    
    # Location intelligence (from LLM knowledge)
    locations: List[ExtractedLocation] = Field(
        ..., 
        min_items=1,
        description="Extracted locations with coordinates from LLM geographic knowledge"
    )
    
    # Weather data (from tool execution)
    weather_data: Optional[WeatherDataSummary] = Field(
        None,
        description="Weather data obtained from API tools"
    )
    
    # Agricultural context (if applicable)
    agricultural_assessment: Optional[AgriculturalAssessment] = Field(
        None,
        description="Agricultural conditions and recommendations if query is farming-related"
    )
    
    # Response metadata
    summary: str = Field(
        ..., 
        description="Comprehensive natural language summary of all weather information, combining location details, current conditions, forecasts, and any agricultural insights"
    )
    data_sources: List[str] = Field(
        default_factory=list, 
        description="List of MCP tools and external APIs used to gather weather data (e.g., ['forecast_server', 'historical_server', 'open-meteo-api'])"
    )
    warnings: List[str] = Field(
        default_factory=list, 
        description="Important warnings about data quality, API limitations, ambiguous locations, or weather-related alerts that users should be aware of"
    )
    processing_time_ms: Optional[int] = Field(
        None, 
        description="Total time taken to process the query and gather all weather data, measured in milliseconds for performance monitoring"
    )
    
    # Timestamps
    query_timestamp: datetime = Field(
        default_factory=datetime.utcnow, 
        description="UTC timestamp when the user query was received and processing began"
    )
    data_timestamp: Optional[datetime] = Field(
        None, 
        description="UTC timestamp indicating when the weather data was last updated by the source APIs"
    )
    
    def get_primary_location(self) -> ExtractedLocation:
        """Get the primary (first) location."""
        return self.locations[0]
    
    def needs_clarification(self) -> bool:
        """Check if any location needs clarification."""
        return any(loc.needs_clarification for loc in self.locations)
    
    def get_clarification_message(self) -> Optional[str]:
        """Generate clarification message if needed."""
        ambiguous_locations = [loc for loc in self.locations if loc.needs_clarification]
        if not ambiguous_locations:
            return None
        
        messages = []
        for loc in ambiguous_locations:
            if loc.clarification_options:
                options = ", ".join(loc.clarification_options)
                messages.append(f"Which '{loc.name}' did you mean? Options: {options}")
            else:
                messages.append(f"Please provide more specific information for '{loc.name}'")
        
        return " ".join(messages)
    
    def validation_warnings(self) -> List[str]:
        """Generate validation warnings."""
        warnings = []
        
        # Check for low confidence locations
        for loc in self.locations:
            if loc.confidence < 0.7:
                warnings.append(f"Low confidence ({loc.confidence:.1f}) for location: {loc.name}")
        
        # Check for missing weather data
        if self.query_type in ["current", "forecast"] and not self.weather_data:
            warnings.append("No weather data available for the requested location")
        
        # Check for agricultural queries without assessment
        if self.query_type == "agricultural" and not self.agricultural_assessment:
            warnings.append("Agricultural assessment not available")
        
        return warnings


class ValidationResult(BaseModel):
    """Result of response validation."""
    valid: bool = Field(..., description="Whether response passes validation")
    errors: List[str] = Field(default_factory=list, description="Critical errors that prevent usage")
    warnings: List[str] = Field(default_factory=list, description="Non-critical issues")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")
    
    def get_user_message(self) -> Optional[str]:
        """Generate user-friendly message about validation issues."""
        if self.valid and not self.warnings:
            return None
        
        messages = []
        
        if self.errors:
            messages.append("I encountered some issues with your request:")
            messages.extend(f"• {error}" for error in self.errors)
        
        if self.warnings:
            if not self.errors:
                messages.append("Please note:")
            messages.extend(f"• {warning}" for warning in self.warnings)
        
        if self.suggestions:
            messages.append("\nSuggestions:")
            messages.extend(f"• {suggestion}" for suggestion in self.suggestions)
        
        return "\n".join(messages)


class StreamingWeatherUpdate(BaseModel):
    """Model for streaming weather updates (future enhancement)."""
    update_type: Literal["location_extracted", "tool_called", "data_received", "processing_complete"] = Field(
        ...,
        description="Type of update in the streaming response"
    )
    location: Optional[ExtractedLocation] = Field(None, description="Extracted location if applicable")
    tool_name: Optional[str] = Field(None, description="Name of tool being called")
    partial_data: Optional[Dict[str, Any]] = Field(None, description="Partial data received")
    is_final: bool = Field(False, description="Whether this is the final update")
    timestamp: datetime = Field(default_factory=datetime.utcnow)