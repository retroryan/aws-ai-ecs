"""
Test configuration management for Strands Weather Agent tests.
Uses the same .env file as the main infrastructure scripts.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from cloud.env file in parent directory
# This assumes scripts are run from the main strands-weather-agent directory
cloud_env_file = Path(__file__).parent.parent.parent / 'cloud.env'
if cloud_env_file.exists():
    load_dotenv(cloud_env_file)
else:
    # Fallback to check if we're running from infra directory
    cloud_env_file_alt = Path(__file__).parent.parent / 'cloud.env'
    if cloud_env_file_alt.exists():
        load_dotenv(cloud_env_file_alt)


class TestAWSConfig(BaseModel):
    """AWS configuration for tests."""
    region: str = Field(default_factory=lambda: os.environ.get('AWS_REGION', 'us-east-1'))
    profile: Optional[str] = Field(default_factory=lambda: os.environ.get('AWS_PROFILE'))
    
    # Stack names - reuse from main config
    base_stack_name: str = Field(
        default_factory=lambda: os.environ.get('BASE_STACK_NAME', 'strands-weather-agent-base')
    )
    services_stack_name: str = Field(
        default_factory=lambda: os.environ.get('SERVICES_STACK_NAME', 'strands-weather-agent-services')
    )
    cluster_name: str = Field(
        default_factory=lambda: os.environ.get('CLUSTER_NAME', 'strands-weather-agent')
    )
    
    class Config:
        validate_assignment = True


class TestServiceConfig(BaseModel):
    """Service configuration for tests."""
    # Service names
    main_service: str = "strands-weather-agent-main"
    forecast_service: str = "strands-weather-agent-forecast"
    historical_service: str = "strands-weather-agent-historical"
    agricultural_service: str = "strands-weather-agent-agricultural"
    
    # Log groups
    log_group_prefix: str = "/ecs/strands-weather-agent"
    
    @property
    def all_services(self) -> List[str]:
        return [
            self.main_service,
            self.forecast_service,
            self.historical_service,
            self.agricultural_service
        ]
    
    def get_log_group(self, service: str) -> str:
        """Get log group name for a service."""
        service_suffix = service.split('-')[-1]
        return f"{self.log_group_prefix}-{service_suffix}"


class TestTimeoutConfig(BaseModel):
    """Timeout configuration for tests."""
    health_check_timeout: int = Field(
        default_factory=lambda: int(os.environ.get('TEST_HEALTH_TIMEOUT', '10'))
    )
    query_timeout: int = Field(
        default_factory=lambda: int(os.environ.get('TEST_QUERY_TIMEOUT', '30'))
    )
    service_startup_wait: int = Field(
        default_factory=lambda: int(os.environ.get('TEST_STARTUP_WAIT', '60'))
    )


class TestLangfuseConfig(BaseModel):
    """Langfuse configuration for tests."""
    host: Optional[str] = Field(default_factory=lambda: os.environ.get('LANGFUSE_HOST'))
    public_key: Optional[str] = Field(default_factory=lambda: os.environ.get('LANGFUSE_PUBLIC_KEY'))
    secret_key: Optional[str] = Field(default_factory=lambda: os.environ.get('LANGFUSE_SECRET_KEY'))
    
    @property
    def is_configured(self) -> bool:
        """Check if Langfuse is properly configured."""
        return bool(self.host and self.public_key)


class TestQueries(BaseModel):
    """Default test queries."""
    basic_queries: List[Dict[str, str]] = Field(default_factory=lambda: [
        {
            "query": "What's the weather in Seattle?",
            "description": "Basic weather query"
        },
        {
            "query": "Give me a 5-day forecast for Chicago",
            "description": "Forecast query"
        },
        {
            "query": "Are conditions good for planting corn in Iowa?",
            "description": "Agricultural query"
        }
    ])
    
    stress_queries: List[Dict[str, str]] = Field(default_factory=lambda: [
        {
            "query": "Compare weather in New York, Los Angeles, Chicago, Houston, and Phoenix",
            "description": "Multi-location query"
        },
        {
            "query": "What were the temperatures in Seattle for the past 30 days?",
            "description": "Historical data query"
        }
    ])


@dataclass
class TestConfig:
    """Main test configuration container."""
    aws: TestAWSConfig = field(default_factory=TestAWSConfig)
    services: TestServiceConfig = field(default_factory=TestServiceConfig)
    timeouts: TestTimeoutConfig = field(default_factory=TestTimeoutConfig)
    langfuse: TestLangfuseConfig = field(default_factory=TestLangfuseConfig)
    queries: TestQueries = field(default_factory=TestQueries)
    
    # Test behavior flags
    verbose: bool = os.environ.get('TEST_VERBOSE', '').lower() in ('true', '1', 'yes')
    fail_fast: bool = os.environ.get('TEST_FAIL_FAST', '').lower() in ('true', '1', 'yes')
    skip_langfuse: bool = os.environ.get('TEST_SKIP_LANGFUSE', '').lower() in ('true', '1', 'yes')
    
    # API URL override (for local testing)
    api_url_override: Optional[str] = os.environ.get('API_URL')


# Global config instance
config = TestConfig()