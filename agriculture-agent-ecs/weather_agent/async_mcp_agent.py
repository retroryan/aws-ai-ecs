"""
Async wrapper for the synchronous MCP Weather Agent

This provides an async interface for FastAPI while using the synchronous agent underneath.
"""

import asyncio
from typing import Optional, Union
from .mcp_agent import MCPWeatherAgent
from .models import OpenMeteoResponse, AgricultureAssessment


class AsyncMCPWeatherAgent:
    """
    Async wrapper for MCPWeatherAgent to work with FastAPI.
    
    This wrapper runs synchronous operations in an executor to avoid blocking
    the event loop while maintaining a clean async interface for FastAPI.
    """
    
    def __init__(self):
        self.sync_agent = MCPWeatherAgent()
        self._executor = None
    
    async def initialize(self):
        """Initialize MCP connections asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.sync_agent.initialize)
    
    async def query(self, user_query: str, thread_id: str = None) -> str:
        """Process a query asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            self.sync_agent.query, 
            user_query, 
            thread_id
        )
    
    async def query_structured(
        self, 
        user_query: str, 
        response_format: str = "forecast", 
        thread_id: str = None
    ) -> Union[OpenMeteoResponse, AgricultureAssessment]:
        """Process a query and return structured output asynchronously."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.sync_agent.query_structured,
            user_query,
            response_format,
            thread_id
        )
    
    def clear_history(self):
        """Clear conversation history."""
        self.sync_agent.clear_history()
    
    async def cleanup(self):
        """Clean up resources."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, self.sync_agent.cleanup)