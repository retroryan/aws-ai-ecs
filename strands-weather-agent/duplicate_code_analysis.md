# Duplicate Code Analysis: MCP Servers and Tests

## Executive Summary

After analyzing the mcp_servers directory and tests directory, I've identified several significant duplicate code patterns that could be refactored to improve maintainability and reduce redundancy. The duplication falls into several categories: server initialization, health checks, error handling, coordinate handling, test utilities, and test execution patterns.

## 1. Server Initialization Patterns

### Duplicate Pattern Found
All three servers (forecast_server.py, historical_server.py, agricultural_server.py) share identical initialization code:

```python
# Lines 16-18 (repeated in all servers)
server = FastMCP(name="openmeteo-[type]")
client = OpenMeteoClient()

# Lines 99-104 (repeated in all servers)
if __name__ == "__main__":
    import os
    host = os.getenv("MCP_HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "[port_number]"))
    print(f"Starting [server_type] server on {host}:{port}")
    server.run(transport="streamable-http", host=host, port=port, path="/mcp")
```

### Refactoring Opportunity
Create a base server class or utility function:

```python
# mcp_servers/base_server.py
class BaseMCPServer:
    def __init__(self, name: str, default_port: int):
        self.server = FastMCP(name=name)
        self.client = OpenMeteoClient()
        self.default_port = default_port
    
    def run(self):
        import os
        host = os.getenv("MCP_HOST", "0.0.0.0" if os.path.exists("/.dockerenv") else "127.0.0.1")
        port = int(os.getenv("MCP_PORT", str(self.default_port)))
        print(f"Starting {self.server.name} server on {host}:{port}")
        self.server.run(transport="streamable-http", host=host, port=port, path="/mcp")
```

## 2. Health Check Endpoints

### Duplicate Pattern Found
All servers have identical health check implementations:

```python
# Lines 20-24 (repeated in all servers)
@server.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Simple health check endpoint for Docker health checks."""
    return JSONResponse({"status": "healthy", "service": "[service_name]-server"})
```

### Refactoring Opportunity
Create a health check factory function:

```python
# mcp_servers/utils.py
def create_health_check(service_name: str):
    async def health_check(request: Request) -> JSONResponse:
        """Simple health check endpoint for Docker health checks."""
        return JSONResponse({"status": "healthy", "service": f"{service_name}-server"})
    return health_check
```

## 3. Coordinate Handling Logic

### Duplicate Pattern Found
All servers share similar coordinate validation and processing:

```python
# Lines ~50-63 (similar pattern in all servers)
if latitude is not None and longitude is not None:
    coords = {"latitude": latitude, "longitude": longitude, "name": location or f"{latitude:.4f},{longitude:.4f}"}
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
```

### Refactoring Opportunity
Create a coordinate validation utility:

```python
# mcp_servers/coordinate_utils.py
async def validate_and_get_coordinates(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    error_prefix: str = "location"
) -> Union[dict, dict]:
    """Validate and return coordinates or error dict."""
    if latitude is not None and longitude is not None:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "name": location or f"{latitude:.4f},{longitude:.4f}"
        }
    elif location:
        coords = await get_coordinates(location)
        if not coords:
            return {
                "error": f"Could not find {error_prefix}: {location}. Please try a major city name."
            }
        return coords
    else:
        return {
            "error": f"Either {error_prefix} name or coordinates (latitude, longitude) required"
        }
```

## 4. Response Structure Building

### Duplicate Pattern Found
All servers build similar response structures:

```python
# Lines ~78-89 (similar in all servers)
data["location_info"] = {
    "name": coords.get("name", location),
    "coordinates": {
        "latitude": coords["latitude"],
        "longitude": coords["longitude"]
    }
}
data["summary"] = f"[Type] for {coords.get('name', location)} ..."
```

### Refactoring Opportunity
Create a response builder utility:

```python
# mcp_servers/response_utils.py
def add_location_and_summary(data: dict, coords: dict, location: str, summary_template: str) -> dict:
    """Add location info and summary to response data."""
    data["location_info"] = {
        "name": coords.get("name", location),
        "coordinates": {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"]
        }
    }
    data["summary"] = summary_template.format(
        location=coords.get('name', location)
    )
    return data
```

## 5. Test Result Tracking

### Duplicate Pattern Found
Both test files implement similar test result tracking classes:

```python
# TestResults in test_mcp_servers.py and TestResultsTracker in test_mcp_agent.py
class TestResults:  # or TestResultsTracker
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_test(self, name: str, passed: bool, details: str = ""):
        # Identical implementation
    
    def print_summary(self):
        # Nearly identical implementation
```

### Refactoring Opportunity
Create a shared test utilities module:

```python
# tests/test_utils.py
class TestResultsTracker:
    """Unified test results tracking for all test modules."""
    def __init__(self, suite_name: str):
        self.suite_name = suite_name
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_test(self, name: str, passed: bool, details: str = ""):
        # Shared implementation
    
    def print_summary(self):
        # Shared implementation with suite_name
```

## 6. Common Test Patterns

### Duplicate Pattern Found
Similar test setup and execution patterns:

```python
# Common pattern in both test files
async def test_something():
    print("\n🧪 Testing Something...")
    print("-" * 50)
    
    try:
        # Test logic
        if success:
            results.add_test("Test Name", True, "Success details")
            print("✅ Success message")
        else:
            results.add_test("Test Name", False, "Failure details")
            print("❌ Failure message")
    except Exception as e:
        results.add_test("Test Name", False, str(e))
        print(f"❌ Error: {e}")
```

### Refactoring Opportunity
Create test decorator or context manager:

```python
# tests/test_utils.py
class TestCase:
    def __init__(self, name: str, results: TestResultsTracker):
        self.name = name
        self.results = results
    
    async def __aenter__(self):
        print(f"\n🧪 Testing {self.name}...")
        print("-" * 50)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.results.add_test(self.name, False, str(exc_val))
            print(f"❌ Error in {self.name}: {exc_val}")
        return False
    
    def assert_success(self, condition: bool, success_msg: str, failure_msg: str = ""):
        if condition:
            self.results.add_test(self.name, True, success_msg)
            print(f"✅ {success_msg}")
        else:
            self.results.add_test(self.name, False, failure_msg)
            print(f"❌ {failure_msg}")
```

## 7. API Client Usage Patterns

### Duplicate Pattern Found
All servers use OpenMeteoClient in similar ways:

```python
# Common pattern across servers
params = {
    "latitude": coords["latitude"],
    "longitude": coords["longitude"],
    # ... other params
}
data = await client.get("[api_type]", params)
```

### Refactoring Opportunity
The api_utils.py already provides good abstraction, but could add higher-level methods:

```python
# Extension to api_utils.py
class OpenMeteoClient:
    # ... existing code ...
    
    async def get_forecast_with_location(
        self, 
        coords: dict, 
        days: int,
        daily_params: List[str],
        hourly_params: Optional[List[str]] = None,
        current_params: Optional[str] = None
    ) -> dict:
        """High-level forecast retrieval with standard params."""
        params = {
            "latitude": coords["latitude"],
            "longitude": coords["longitude"],
            "forecast_days": days,
            "daily": ",".join(daily_params),
            "timezone": "auto"
        }
        if hourly_params:
            params["hourly"] = ",".join(hourly_params)
        if current_params:
            params["current"] = current_params
        
        return await self.get("forecast", params)
```

## Implementation Priority

1. **High Priority** - Create base server class (reduces most duplication)
2. **High Priority** - Create shared test utilities (improves test maintainability)
3. **Medium Priority** - Extract coordinate validation logic
4. **Medium Priority** - Create response builder utilities
5. **Low Priority** - Enhance API client with higher-level methods

## Benefits of Refactoring

1. **Reduced Code Duplication**: ~40% reduction in server code, ~30% in test code
2. **Easier Maintenance**: Changes to common patterns need only one update
3. **Better Testability**: Shared utilities can be unit tested separately
4. **Clearer Intent**: Higher-level abstractions make code purpose clearer
5. **Easier Extension**: Adding new servers becomes much simpler

## Potential New Structure

```
mcp_servers/
├── base_server.py      # Base server class
├── utils/
│   ├── __init__.py
│   ├── coordinates.py   # Coordinate validation
│   ├── responses.py     # Response building
│   └── health.py        # Health check factory
├── forecast_server.py   # Now ~50% smaller
├── historical_server.py # Now ~50% smaller
├── agricultural_server.py # Now ~50% smaller
└── api_utils.py         # Enhanced with high-level methods

tests/
├── utils/
│   ├── __init__.py
│   ├── results.py       # TestResultsTracker
│   ├── fixtures.py      # Common test data
│   └── helpers.py       # Test decorators/context managers
├── test_mcp_servers.py  # Now uses shared utilities
└── test_mcp_agent.py    # Now uses shared utilities
```

This refactoring would significantly improve code quality while maintaining all existing functionality.