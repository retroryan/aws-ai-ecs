"""
Mock tools for testing the weather agent without MCP servers.

These tools simulate the behavior of MCP weather servers for testing purposes.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import random


class MockTool:
    """Base class for mock tools."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.input_schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def __call__(self, **kwargs) -> Any:
        """Execute the tool."""
        raise NotImplementedError


class MockCurrentWeatherTool(MockTool):
    """Mock tool for getting current weather."""
    
    def __init__(self):
        super().__init__(
            name="get_current_weather",
            description="Get current weather for a location"
        )
        self.input_schema = {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"}
            },
            "required": ["latitude", "longitude"]
        }
    
    def __call__(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Return mock current weather data."""
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": f"Location at {latitude:.2f}, {longitude:.2f}"
            },
            "current": {
                "temperature": round(random.uniform(10, 30), 1),
                "feels_like": round(random.uniform(8, 32), 1),
                "humidity": random.randint(30, 80),
                "wind_speed": round(random.uniform(0, 20), 1),
                "wind_direction": random.randint(0, 360),
                "weather_code": random.choice([0, 1, 2, 3]),  # Clear to cloudy
                "description": random.choice(["Clear", "Partly cloudy", "Cloudy", "Overcast"]),
                "timestamp": datetime.utcnow().isoformat()
            }
        }


class MockForecastTool(MockTool):
    """Mock tool for getting weather forecast."""
    
    def __init__(self):
        super().__init__(
            name="get_forecast",
            description="Get weather forecast for a location"
        )
        self.input_schema = {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "days": {"type": "integer", "minimum": 1, "maximum": 7}
            },
            "required": ["latitude", "longitude"]
        }
    
    def __call__(self, latitude: float, longitude: float, days: int = 3) -> Dict[str, Any]:
        """Return mock forecast data."""
        forecast_days = []
        base_date = datetime.utcnow()
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            forecast_days.append({
                "date": date.strftime("%Y-%m-%d"),
                "temperature_max": round(random.uniform(15, 35), 1),
                "temperature_min": round(random.uniform(5, 25), 1),
                "precipitation_probability": random.randint(0, 100),
                "weather_code": random.choice([0, 1, 2, 3, 61]),
                "description": random.choice(["Sunny", "Partly cloudy", "Cloudy", "Rainy"])
            })
        
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": f"Location at {latitude:.2f}, {longitude:.2f}"
            },
            "forecast": forecast_days
        }


class MockHistoricalWeatherTool(MockTool):
    """Mock tool for getting historical weather."""
    
    def __init__(self):
        super().__init__(
            name="get_historical_weather",
            description="Get historical weather data"
        )
        self.input_schema = {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            },
            "required": ["latitude", "longitude", "start_date", "end_date"]
        }
    
    def __call__(self, latitude: float, longitude: float, start_date: str, end_date: str) -> Dict[str, Any]:
        """Return mock historical weather data."""
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": f"Location at {latitude:.2f}, {longitude:.2f}"
            },
            "historical": {
                "start_date": start_date,
                "end_date": end_date,
                "average_temperature": round(random.uniform(10, 25), 1),
                "max_temperature": round(random.uniform(20, 35), 1),
                "min_temperature": round(random.uniform(0, 15), 1),
                "total_precipitation": round(random.uniform(0, 100), 1),
                "data_points": random.randint(20, 30)
            }
        }


class MockAgriculturalTool(MockTool):
    """Mock tool for agricultural assessments."""
    
    def __init__(self):
        super().__init__(
            name="get_agricultural_conditions",
            description="Get agricultural conditions and recommendations"
        )
        self.input_schema = {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "crop_type": {"type": "string"}
            },
            "required": ["latitude", "longitude"]
        }
    
    def __call__(self, latitude: float, longitude: float, crop_type: Optional[str] = None) -> Dict[str, Any]:
        """Return mock agricultural data."""
        crop = crop_type or "general crops"
        conditions = random.choice(["Excellent", "Good", "Fair", "Poor"])
        
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": f"Location at {latitude:.2f}, {longitude:.2f}"
            },
            "agricultural": {
                "crop_type": crop,
                "conditions": conditions,
                "soil_moisture": random.randint(20, 80),
                "temperature_suitable": random.choice([True, False]),
                "frost_risk": random.choice(["Low", "Medium", "High"]),
                "recommendations": [
                    f"Current conditions are {conditions.lower()} for {crop}",
                    "Monitor soil moisture levels",
                    "Consider frost protection if needed"
                ]
            }
        }


def create_mock_tools() -> List[MockTool]:
    """Create a list of mock tools for testing."""
    return [
        MockCurrentWeatherTool(),
        MockForecastTool(),
        MockHistoricalWeatherTool(),
        MockAgriculturalTool()
    ]