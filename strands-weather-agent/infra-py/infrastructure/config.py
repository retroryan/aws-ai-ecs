"""
Centralized configuration management for infrastructure scripts.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables from cloud.env file in parent directory
# This assumes scripts are run from the main strands-weather-agent directory
cloud_env_file = Path(__file__).parent.parent.parent / 'cloud.env'
if cloud_env_file.exists():
    load_dotenv(cloud_env_file)
else:
    # Fallback to check if we're running from infra-py directory
    cloud_env_file_alt = Path(__file__).parent.parent / 'cloud.env'
    if cloud_env_file_alt.exists():
        load_dotenv(cloud_env_file_alt)


class AWSConfig(BaseModel):
    """AWS-specific configuration."""
    region: str = Field(default_factory=lambda: os.environ.get('AWS_REGION', 'us-east-1'))
    profile: Optional[str] = Field(default_factory=lambda: os.environ.get('AWS_PROFILE'))
    account_id: Optional[str] = None
    
    class Config:
        validate_assignment = True


class StackConfig(BaseModel):
    """CloudFormation stack configuration."""
    base_stack_name: str = Field(
        default_factory=lambda: os.environ.get('BASE_STACK_NAME', 'strands-weather-agent-base')
    )
    services_stack_name: str = Field(
        default_factory=lambda: os.environ.get('SERVICES_STACK_NAME', 'strands-weather-agent-services')
    )
    cluster_name: str = Field(
        default_factory=lambda: os.environ.get('CLUSTER_NAME', 'strands-weather-agent')
    )


class ECRConfig(BaseModel):
    """ECR repository configuration."""
    repo_prefix: str = 'strands-weather-agent'
    
    @property
    def main_repo(self) -> str:
        return f"{self.repo_prefix}-main"
    
    @property
    def forecast_repo(self) -> str:
        return f"{self.repo_prefix}-forecast"
    
    @property
    def historical_repo(self) -> str:
        return f"{self.repo_prefix}-historical"
    
    @property
    def agricultural_repo(self) -> str:
        return f"{self.repo_prefix}-agricultural"
    
    @property
    def all_repos(self) -> list[str]:
        return [self.main_repo, self.forecast_repo, self.historical_repo, self.agricultural_repo]


class ServiceConfig(BaseModel):
    """ECS service configuration."""
    main_service_name: str = 'strands-weather-agent-main'
    forecast_service_name: str = 'strands-weather-agent-forecast'
    historical_service_name: str = 'strands-weather-agent-historical'
    agricultural_service_name: str = 'strands-weather-agent-agricultural'
    
    # Service ports
    main_port: int = 7777
    forecast_port: int = 7778
    historical_port: int = 7779
    agricultural_port: int = 7780
    
    # Health check paths
    health_check_path: str = '/health'
    
    @property
    def all_services(self) -> list[str]:
        return [
            self.main_service_name,
            self.forecast_service_name,
            self.historical_service_name,
            self.agricultural_service_name
        ]


class BedrockConfig(BaseModel):
    """AWS Bedrock configuration."""
    model_id: str = Field(
        default_factory=lambda: os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')
    )
    region: str = Field(
        default_factory=lambda: os.environ.get('BEDROCK_REGION', 'us-east-1')
    )
    temperature: float = Field(
        default_factory=lambda: float(os.environ.get('BEDROCK_TEMPERATURE', '0'))
    )


class DockerConfig(BaseModel):
    """Docker build configuration."""
    platform: str = 'linux/amd64'  # For Fargate compatibility
    build_args: Dict[str, str] = field(default_factory=dict)
    
    @property
    def version_tag(self) -> str:
        """Generate version tag based on git commit and timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"v{timestamp}"


class DeploymentConfig(BaseModel):
    """Deployment configuration."""
    environment: str = Field(
        default_factory=lambda: os.environ.get('DEPLOYMENT_ENV', 'dev')
    )
    enable_telemetry: bool = Field(
        default_factory=lambda: os.environ.get('ENABLE_TELEMETRY', 'false').lower() == 'true'
    )
    log_level: str = Field(
        default_factory=lambda: os.environ.get('LOG_LEVEL', 'INFO')
    )
    
    # Timeouts
    stack_creation_timeout: int = 600  # 10 minutes
    service_stabilization_timeout: int = 300  # 5 minutes
    health_check_timeout: int = 30
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


class AppConfig(BaseModel):
    """Main application configuration."""
    aws: AWSConfig = Field(default_factory=AWSConfig)
    stacks: StackConfig = Field(default_factory=StackConfig)
    ecr: ECRConfig = Field(default_factory=ECRConfig)
    services: ServiceConfig = Field(default_factory=ServiceConfig)
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)
    
    def to_env_dict(self) -> Dict[str, str]:
        """Convert configuration to environment variable dictionary."""
        return {
            # AWS
            'AWS_REGION': self.aws.region,
            'AWS_PROFILE': self.aws.profile or '',
            
            # Stacks
            'BASE_STACK_NAME': self.stacks.base_stack_name,
            'SERVICES_STACK_NAME': self.stacks.services_stack_name,
            'CLUSTER_NAME': self.stacks.cluster_name,
            
            # Bedrock
            'BEDROCK_MODEL_ID': self.bedrock.model_id,
            'BEDROCK_REGION': self.bedrock.region,
            'BEDROCK_TEMPERATURE': str(self.bedrock.temperature),
            
            # Deployment
            'DEPLOYMENT_ENV': self.deployment.environment,
            'ENABLE_TELEMETRY': str(self.deployment.enable_telemetry).lower(),
            'LOG_LEVEL': self.deployment.log_level,
        }
    
    def update_from_env(self) -> None:
        """Update configuration from environment variables."""
        # AWS
        if aws_region := os.environ.get('AWS_REGION'):
            self.aws.region = aws_region
        if aws_profile := os.environ.get('AWS_PROFILE'):
            self.aws.profile = aws_profile
            
        # Stacks
        if base_stack := os.environ.get('BASE_STACK_NAME'):
            self.stacks.base_stack_name = base_stack
        if services_stack := os.environ.get('SERVICES_STACK_NAME'):
            self.stacks.services_stack_name = services_stack
        if cluster_name := os.environ.get('CLUSTER_NAME'):
            self.stacks.cluster_name = cluster_name
            
        # Bedrock
        if model_id := os.environ.get('BEDROCK_MODEL_ID'):
            self.bedrock.model_id = model_id
        if bedrock_region := os.environ.get('BEDROCK_REGION'):
            self.bedrock.region = bedrock_region
        if temperature := os.environ.get('BEDROCK_TEMPERATURE'):
            self.bedrock.temperature = float(temperature)
            
        # Deployment
        if env := os.environ.get('DEPLOYMENT_ENV'):
            self.deployment.environment = env
        if telemetry := os.environ.get('ENABLE_TELEMETRY'):
            self.deployment.enable_telemetry = telemetry.lower() == 'true'
        if log_level := os.environ.get('LOG_LEVEL'):
            self.deployment.log_level = log_level


# Global configuration instance
config = AppConfig()
config.update_from_env()


def get_config() -> AppConfig:
    """Get the global configuration instance."""
    return config


def reload_config() -> AppConfig:
    """Reload configuration from environment."""
    global config
    config = AppConfig()
    config.update_from_env()
    return config