"""
Custom exception types for Weather Agent.

These exceptions provide specific error handling for different failure modes,
following best practices for error boundaries and graceful degradation.
"""


class WeatherAgentError(Exception):
    """Base exception for all weather agent errors."""
    pass


class MCPConnectionError(WeatherAgentError):
    """
    Raised when MCP server connection fails.
    
    Attributes:
        server_name: Name of the server that failed
        original_error: The underlying exception
    """
    def __init__(self, server_name: str, original_error: Exception):
        self.server_name = server_name
        self.original_error = original_error
        super().__init__(
            f"Failed to connect to MCP server '{server_name}': {original_error}"
        )


class StructuredOutputError(WeatherAgentError):
    """
    Raised when structured output parsing or generation fails.
    
    This can happen when:
    - The LLM doesn't return valid JSON
    - Required fields are missing
    - Data types don't match schema
    """
    pass


class ModelInvocationError(WeatherAgentError):
    """
    Raised when Bedrock model invocation fails.
    
    Common causes:
    - Rate limiting / throttling
    - Model access not enabled
    - Invalid model ID
    - Network issues
    """
    pass


class SessionError(WeatherAgentError):
    """
    Raised when session management operations fail.
    
    This includes:
    - Failed to load session data
    - Failed to save session data
    - Corrupted session files
    """
    pass


class ValidationError(WeatherAgentError):
    """
    Raised when response validation fails.
    
    This is different from Pydantic's ValidationError and is used
    for business logic validation of weather responses.
    """
    pass