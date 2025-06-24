"""
Weather Agent Package - MCP Weather Demo

Simple demonstration of MCP servers with stdio subprocess communication.
"""

from .mcp_agent import MCPWeatherAgent, create_weather_agent

__version__ = "1.0.0"

__all__ = [
    "MCPWeatherAgent",
    "create_weather_agent"
]