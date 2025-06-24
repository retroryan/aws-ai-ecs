# Strands Weather Agent - Code Cleanup Proposal

## Executive Summary

After a comprehensive analysis of the strands-weather-agent codebase, I've identified significant opportunities for cleanup and refactoring that could reduce the codebase size by approximately 40% while improving maintainability and clarity. This proposal outlines specific files to remove, code patterns to refactor, and structural improvements to implement.

**Key Change**: All Python code for the weather agent will be consolidated into the `weather_agent` directory, making it a self-contained Python application that users can run with `cd weather_agent && python main.py`.

## 1. Files to Remove (Immediate Impact)

### 1.1 Consolidate Entry Points
- **Move**: `api.py` → `weather_agent/main.py` (rename and move)
- **Remove**: `weather_agent/chatbot.py` (281 lines)
- **Remove**: Current `weather_agent/main.py` (22 lines)
- **Rationale**: Create a single, clear entry point in the weather_agent directory that provides the FastAPI interface.

### 1.2 Unused Model Files
- **Remove**: `weather_agent/models/queries.py`
- **Remove**: `weather_agent/models/metadata.py`
- **Rationale**: No imports found anywhere in the codebase

### 1.3 Legacy Test Files
- **Remove**: `tests/test_mcp_agent.py` (LangGraph version)
- **Remove**: `tests/test_coordinate_handling.py`
- **Remove**: `tests/test_coordinate_usage.py`
- **Remove**: `tests/test_simple_coordinate.py`
- **Remove**: `tests/test_diverse_cities.py`
- **Remove**: `test_context_retention.py` (root level)
- **Keep**: Consolidate coordinate testing into `tests/test_structured_output.py`
- **Rationale**: All coordinate tests duplicate the same functionality. The LangGraph test file references non-existent imports.

### 1.4 Unused Utilities
- **Remove**: `mcp_servers/utils/display.py`
- **Rationale**: Imported but never used

### 1.5 Configuration Consolidation
- **Move**: Root `requirements.txt` → `weather_agent/requirements.txt`
- **Move**: Root `.env.example` → `weather_agent/.env.example`
- **Add**: `weather_agent/.python-version` with content `3.12.10`
- **Rationale**: Make weather_agent directory self-contained for Python development

### 1.6 Historical/Temporary Files
- **Remove**: `.history/` directory with old .env versions
- **Remove**: `/infra/logs/` directory with June 2025 deployment logs
- **Remove**: Empty `/test_results/` directory
- **Rationale**: Historical files that provide no current value

## 2. Code Refactoring Priorities

### 2.1 Create Base Classes for Common Patterns

#### A. MCP Server Base Class
```python
# mcp_servers/base_server.py
class BaseMCPServer:
    def __init__(self, name: str, port: int):
        self.server = Server(name)
        self.api = APIClient()
        self.setup_health_check()
        self.setup_error_handling()
    
    def setup_health_check(self):
        @self.server.custom_route("/health", methods=["GET"])
        async def health_check(request: Request):
            return JSONResponse({"status": "healthy", "service": self.name})
    
    def validate_coordinates(self, lat: float, lon: float):
        # Common coordinate validation
        pass
    
    def build_response(self, location_info: dict, data: dict):
        # Common response structure
        pass
```

**Impact**: Reduce ~120 lines of duplicate code across 3 servers

#### B. Test Base Class
```python
# tests/base_test.py
class BaseWeatherTest:
    def setup_test_results(self):
        # Common test result tracking
        pass
    
    def validate_structured_response(self, response):
        # Common validation logic
        pass
    
    def report_results(self):
        # Common reporting
        pass
```

**Impact**: Reduce ~150 lines of duplicate test code

### 2.2 Consolidate Model Definitions

#### Current State:
- `ExtractedLocation` in `structured_responses.py`
- `LocationInfo` in `weather.py`
- `Coordinates` in `weather.py`

#### Proposed:
```python
# weather_agent/models/location.py
class Location(BaseModel):
    """Unified location model"""
    name: str
    latitude: float
    longitude: float
    country: Optional[str] = None
    country_code: Optional[str] = None
    timezone: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        # Common display logic
        pass
```

**Impact**: Reduce 3 models to 1, improving consistency

### 2.3 Extract Common Utilities

#### A. Environment Configuration
```python
# utils/config.py
class Config:
    """Centralized configuration management"""
    def __init__(self):
        load_dotenv()
        self.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID")
        self.bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
        # ... other config
```

#### B. Logging Setup
```python
# utils/logging.py
def setup_logger(name: str) -> logging.Logger:
    """Standardized logger setup"""
    logger = logging.getLogger(name)
    # Common configuration
    return logger
```

#### C. Session Management
```python
# weather_agent/session_manager.py
class SessionManager:
    """Handle all session operations"""
    def get_messages(self, session_id: str): pass
    def save_messages(self, session_id: str, messages: list): pass
    def clear_session(self, session_id: str): pass
```

### 2.4 Clean Up Unused Code

#### In `weather_agent/mcp_agent.py`:
- Remove unused imports:
  - Line 17: `from contextlib import ExitStack`
  - Line 18: `from concurrent.futures import ThreadPoolExecutor` (and self.executor)
  - Line 23: `from pydantic import ValidationError`
- Remove commented import on line 31
- Remove duplicate `Path` import on line 44

## 3. Structural Improvements

### 3.1 Proposed Directory Structure
```
strands-weather-agent/
├── weather_agent/              # Self-contained Python application
│   ├── main.py                # Single entry point (moved from api.py)
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Environment template
│   ├── .python-version       # pyenv version (3.12.10)
│   ├── agent/                # Agent implementation
│   │   ├── __init__.py
│   │   ├── weather_agent.py  # Main agent (renamed from mcp_agent.py)
│   │   └── session_manager.py # Extracted session handling
│   ├── models/               # Consolidated models
│   │   ├── __init__.py
│   │   ├── location.py      # Unified location model
│   │   ├── weather.py       # Weather-specific models
│   │   └── responses.py     # Response models
│   ├── servers/             # MCP servers
│   │   ├── __init__.py
│   │   ├── base.py         # Base server class
│   │   ├── forecast.py
│   │   ├── historical.py
│   │   └── agricultural.py
│   ├── utils/              # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── date_utils.py
│   └── tests/              # Agent-specific tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_agent.py
│       └── test_integration.py
├── mcp_servers/            # Keep separate (they're independent services)
├── docker/                 # Docker files (updated paths)
├── infra/                  # Infrastructure (unchanged)
├── scripts/                # Scripts (updated to reference weather_agent/)
└── README.md              # Project documentation
```

### 3.2 Usage Pattern

Users will interact with the weather agent as follows:

```bash
# Navigate to the weather agent directory
cd weather_agent

# Set Python version (pyenv will read .python-version)
pyenv local 3.12.10

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env to set BEDROCK_MODEL_ID and other configs

# Run the application
python main.py

# Or with uvicorn for development
uvicorn main:app --reload --port 8090
```

### 3.3 Import Path Updates

With the new structure, imports within the weather_agent directory will be relative:
```python
# In weather_agent/main.py
from agent.weather_agent import MCPWeatherAgent
from models.responses import WeatherQueryResponse
from utils.config import Config
from utils.logging import setup_logger

# In weather_agent/agent/weather_agent.py
from ..models.location import Location
from ..utils.config import Config
from .session_manager import SessionManager
```

### 3.4 MCP Servers Integration

The MCP servers remain in their separate directory but the weather agent will reference them via environment variables:
```bash
# In weather_agent/.env
MCP_FORECAST_URL=http://localhost:8081/mcp
MCP_HISTORICAL_URL=http://localhost:8082/mcp
MCP_AGRICULTURAL_URL=http://localhost:8083/mcp
```

## 4. Implementation Plan

### Phase 1: Consolidate to weather_agent Directory (2-3 hours)
1. Move `api.py` to `weather_agent/main.py`
2. Move root `requirements.txt` to `weather_agent/requirements.txt`
3. Move `.env.example` to `weather_agent/.env.example`
4. Create `weather_agent/.python-version` with `3.12.10`
5. Update all import paths in moved files
6. Delete redundant files (chatbot.py, old main.py)
7. Update scripts to reference new paths

### Phase 2: Create Base Classes (2-3 hours)
1. Implement BaseMCPServer
2. Refactor the 3 MCP servers to use base class
3. Implement BaseWeatherTest
4. Refactor test files to use base class

### Phase 3: Consolidate Models (1-2 hours)
1. Create unified Location model
2. Update all references throughout codebase
3. Remove redundant model files

### Phase 4: Extract Utilities (2-3 hours)
1. Create config.py for centralized configuration
2. Create logging.py for standardized logging
3. Extract SessionManager from mcp_agent.py
4. Clean up unused imports and code

### Phase 5: Update Docker and Scripts (2-3 hours)
1. Update Dockerfile paths to reference weather_agent/
2. Update docker-compose.yml to use new structure
3. Update shell scripts in scripts/ directory
4. Update GitHub Actions or CI/CD pipelines
5. Comprehensive testing of all components

## 5. Expected Benefits

### Quantitative:
- **Code Reduction**: ~40% fewer lines of code
- **File Count**: Reduce from 71 to ~45 Python files
- **Test Files**: Reduce from 11 to 4 test files
- **Duplicate Code**: Eliminate ~500 lines of duplicate code

### Qualitative:
- **Maintainability**: Single source of truth for common patterns
- **Clarity**: Clear separation of concerns with self-contained weather_agent
- **Extensibility**: Easy to add new MCP servers or features
- **Testing**: More focused, less redundant tests
- **Onboarding**: Simpler codebase - just `cd weather_agent && python main.py`
- **Development**: Standard Python project structure with pyenv support

## 6. Risk Mitigation

1. **Create a branch** for all cleanup work
2. **Run full test suite** after each phase
3. **Test Docker builds** after structural changes
4. **Update documentation** as files are moved/renamed
5. **Keep backups** of removed files initially (in a `deprecated/` folder)

## 7. Metrics for Success

- All existing tests pass
- Docker builds succeed
- API functionality unchanged
- Performance metrics remain stable
- Code coverage maintained or improved

## 8. Example: New Developer Experience

After cleanup, a new developer's experience would be:

```bash
# Clone the repository
git clone <repo-url>
cd strands-weather-agent/weather_agent

# Python version is automatically set via .python-version
pyenv install  # Installs 3.12.10 if not already installed
python --version  # Should show Python 3.12.10

# Set up the environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env to add BEDROCK_MODEL_ID

# Run the agent
python main.py

# That's it! The API is now available at http://localhost:8090
```

## Conclusion

This cleanup will transform the strands-weather-agent from a prototype with organic growth patterns into a production-ready codebase. The key improvement is consolidating all weather agent Python code into a self-contained directory that follows Python best practices.

The proposed changes maintain all functionality while significantly improving code quality and developer experience. The phased approach allows for incremental improvements with validation at each step, minimizing risk while maximizing benefit. I recommend starting with Phase 1 immediately, as it provides the foundation for all other improvements.