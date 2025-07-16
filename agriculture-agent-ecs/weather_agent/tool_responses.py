"""
Pydantic models for tool responses from MCP servers.
These models provide type-safe access to tool response data.

Note: LangGraph serializes tool responses as JSON strings in ToolMessage.content,
so we need to parse these strings to create structured models.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import json


class ToolResponse(BaseModel):
    """Base model for all tool responses."""
    tool_name: str = Field(..., description="Name of the tool that generated this response")
    success: bool = Field(True, description="Whether the tool call succeeded")
    error: Optional[str] = Field(None, description="Error message if call failed")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Raw response data")


class WeatherForecastResponse(ToolResponse):
    """Response from get_weather_forecast tool."""
    location: Optional[Dict[str, Any]] = Field(None, description="Location information")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Lat/lon coordinates")
    timezone: Optional[str] = Field(None, description="Timezone")
    current: Optional[Dict[str, Any]] = Field(None, description="Current weather data")
    daily: Optional[Dict[str, Any]] = Field(None, description="Daily forecast data")
    
    @validator('location', pre=True)
    def normalize_location(cls, v):
        """Handle location being either a string or dict."""
        if isinstance(v, str):
            return {"name": v}
        return v


class HistoricalWeatherResponse(ToolResponse):
    """Response from get_historical_weather tool."""
    location: Optional[str] = Field(None, description="Location name")
    date_range: Optional[Dict[str, str]] = Field(None, description="Start and end dates")
    daily: Optional[Dict[str, List[Any]]] = Field(None, description="Historical daily data")


class AgriculturalConditionsResponse(ToolResponse):
    """Response from get_agricultural_conditions tool."""
    location: Optional[str] = Field(None, description="Location name")
    assessment_date: Optional[str] = Field(None, description="Date of assessment")
    temperature: Optional[float] = Field(None, description="Current temperature")
    soil_temperature_0_to_10cm: Optional[float] = Field(None, description="Soil temperature")
    soil_moisture_0_to_10cm: Optional[float] = Field(None, description="Soil moisture")
    precipitation: Optional[float] = Field(None, description="Precipitation amount")
    evapotranspiration: Optional[float] = Field(None, description="Evapotranspiration rate")
    conditions: Optional[str] = Field(None, description="Overall conditions")
    frost_risk: Optional[str] = Field(None, description="Frost risk level")
    growing_degree_days: Optional[float] = Field(None, description="Growing degree days")
    recommendations: Optional[List[str]] = Field(None, description="Agricultural recommendations")
    crop_recommendations: Optional[List[str]] = Field(None, description="Crop-specific recommendations")


class ToolCallInfo(BaseModel):
    """Information about a tool call made by the agent."""
    tool_name: str = Field(..., description="Name of the tool called")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the tool")
    call_id: Optional[str] = Field(None, description="Unique ID of the tool call")


class ConversationState(BaseModel):
    """Clean representation of conversation state with tool responses."""
    thread_id: str = Field(..., description="Conversation thread ID")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation messages")
    tool_calls: List[ToolCallInfo] = Field(default_factory=list, description="Tool calls made")
    tool_responses: List[ToolResponse] = Field(default_factory=list, description="Parsed tool responses")
    
    def get_tool_response(self, tool_name: str) -> Optional[ToolResponse]:
        """Get the most recent response for a specific tool."""
        for response in reversed(self.tool_responses):
            if response.tool_name == tool_name:
                return response
        return None
    
    def get_all_tool_responses(self, tool_name: str) -> List[ToolResponse]:
        """Get all responses for a specific tool."""
        return [r for r in self.tool_responses if r.tool_name == tool_name]


def parse_tool_content(content: Any) -> Dict[str, Any]:
    """
    Parse tool content from LangGraph ToolMessage.
    
    LangGraph serializes tool responses as JSON strings, so we need to handle:
    1. String content that is JSON
    2. Dict content (shouldn't happen with MCP, but handle it)
    3. Other content types
    """
    if isinstance(content, str):
        # Try to parse as JSON
        content = content.strip()
        if content.startswith('{') and content.endswith('}'):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Not valid JSON, return as raw
                return {"raw_response": content}
        else:
            # Not JSON format
            return {"raw_response": content}
    elif isinstance(content, dict):
        # Already a dict (shouldn't happen with MCP tools, but handle it)
        return content
    else:
        # Other types - convert to string
        return {"raw_response": str(content)}


def create_tool_response(tool_name: str, content: Any) -> ToolResponse:
    """
    Create an appropriate ToolResponse object based on tool name and content.
    
    Args:
        tool_name: Name of the tool that generated the response
        content: Raw content from ToolMessage (usually a JSON string)
    
    Returns:
        Appropriate ToolResponse subclass instance
    """
    # Parse the content
    try:
        data = parse_tool_content(content)
        
        # Create appropriate response model based on tool name
        if tool_name == "get_weather_forecast":
            return WeatherForecastResponse(
                tool_name=tool_name,
                raw_response=data,
                **data
            )
        elif tool_name == "get_historical_weather":
            return HistoricalWeatherResponse(
                tool_name=tool_name,
                raw_response=data,
                **data
            )
        elif tool_name == "get_agricultural_conditions":
            # Handle both possible recommendation field names
            if "crop_recommendations" in data and "recommendations" not in data:
                data["recommendations"] = data["crop_recommendations"]
            return AgriculturalConditionsResponse(
                tool_name=tool_name,
                raw_response=data,
                **data
            )
        else:
            # Unknown tool - use base class
            return ToolResponse(
                tool_name=tool_name,
                raw_response=data
            )
    
    except Exception as e:
        # Error parsing - create error response
        return ToolResponse(
            tool_name=tool_name,
            success=False,
            error=str(e),
            raw_response={"error": str(e), "original_content": str(content)}
        )