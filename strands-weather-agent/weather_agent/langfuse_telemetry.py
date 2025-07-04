"""
Langfuse Telemetry Integration for AWS Strands Weather Agent

This module provides Langfuse observability integration for the weather agent,
following AWS Strands best practices for OpenTelemetry integration.

Key Features:
- Automatic OTEL configuration for Langfuse
- Session and user tracking
- Tagging and metadata support
- Proper telemetry initialization
- Support for evaluation and scoring
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path

# Load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

from strands.telemetry import StrandsTelemetry

# Configure logging
logger = logging.getLogger(__name__)


class LangfuseTelemetry:
    """
    Manages Langfuse telemetry configuration for AWS Strands agents.
    
    This class handles the proper setup of OpenTelemetry exports to Langfuse,
    following the critical configuration points identified in the integration guide.
    """
    
    def __init__(self, 
                 public_key: Optional[str] = None,
                 secret_key: Optional[str] = None,
                 host: Optional[str] = None,
                 service_name: str = "weather-agent",
                 environment: str = "production"):
        """
        Initialize Langfuse telemetry configuration.
        
        Args:
            public_key: Langfuse public key (or from env)
            secret_key: Langfuse secret key (or from env)
            host: Langfuse host URL (or from env)
            service_name: Service name for OTEL
            environment: Deployment environment
        """
        # Get credentials from environment if not provided
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        self.service_name = service_name
        self.environment = environment
        self.telemetry_initialized = False
        
        # Validate configuration
        if not self.public_key or not self.secret_key:
            logger.warning("Langfuse credentials not configured. Telemetry will be disabled.")
            return
        
        # Initialize telemetry
        self._setup_langfuse_telemetry()
    
    def _setup_langfuse_telemetry(self):
        """
        Set up Langfuse telemetry with proper OTEL configuration.
        
        Critical configuration points:
        1. Use signal-specific endpoint (/api/public/otel/v1/traces)
        2. Set environment variables BEFORE importing Strands
        3. Explicitly initialize StrandsTelemetry
        4. Use proper authentication headers
        """
        try:
            # Create auth token for OTEL authentication
            auth_token = base64.b64encode(
                f"{self.public_key}:{self.secret_key}".encode()
            ).decode()
            
            # CRITICAL: Set OTEL environment variables
            # Use signal-specific endpoint (not generic /api/public/otel)
            os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{self.host}/api/public/otel/v1/traces"
            os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth_token}"
            os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"
            os.environ["OTEL_SERVICE_NAME"] = self.service_name
            
            # Add resource attributes
            resource_attrs = f"service.version=1.0.0,deployment.environment={self.environment}"
            if hasattr(os, 'uname'):
                resource_attrs += f",host.name={os.uname().nodename}"
            os.environ["OTEL_RESOURCE_ATTRIBUTES"] = resource_attrs
            
            # CRITICAL: Explicitly initialize StrandsTelemetry
            # This is required - telemetry is NOT automatic!
            telemetry = StrandsTelemetry()
            telemetry.setup_otlp_exporter()
            
            self.telemetry_initialized = True
            logger.info(f"Langfuse telemetry initialized successfully")
            logger.info(f"  Host: {self.host}")
            logger.info(f"  Service: {self.service_name}")
            logger.info(f"  Environment: {self.environment}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse telemetry: {e}")
            self.telemetry_initialized = False
    
    def create_trace_attributes(self,
                               session_id: Optional[str] = None,
                               user_id: Optional[str] = None,
                               tags: Optional[list] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create trace attributes for Langfuse tracking.
        
        Args:
            session_id: Session identifier for grouping traces
            user_id: User identifier
            tags: List of tags for filtering
            metadata: Additional metadata to include
            
        Returns:
            Dictionary of trace attributes
        """
        attributes = {}
        
        # Core Langfuse attributes
        if session_id:
            attributes["session.id"] = session_id
        if user_id:
            attributes["user.id"] = user_id
        if tags:
            attributes["langfuse.tags"] = tags
        
        # Add service context
        attributes["service.name"] = self.service_name
        attributes["environment"] = self.environment
        
        # Add metadata
        if metadata:
            for key, value in metadata.items():
                # Prefix custom attributes to avoid conflicts
                attributes[f"custom.{key}"] = value
        
        return attributes
    
    def is_enabled(self) -> bool:
        """Check if telemetry is enabled and initialized."""
        return self.telemetry_initialized


def configure_langfuse_from_env(service_name: str = "weather-agent",
                               environment: Optional[str] = None) -> LangfuseTelemetry:
    """
    Configure Langfuse telemetry from environment variables.
    
    This is the recommended way to initialize Langfuse in production.
    
    Required environment variables:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_HOST (optional, defaults to cloud.langfuse.com)
    
    Args:
        service_name: Name of the service for tracking
        environment: Environment name (defaults to ENVIRONMENT env var or 'production')
        
    Returns:
        Configured LangfuseTelemetry instance
    """
    env = environment or os.getenv("ENVIRONMENT", "production")
    
    telemetry = LangfuseTelemetry(
        service_name=service_name,
        environment=env
    )
    
    if not telemetry.is_enabled():
        logger.warning(
            "Langfuse telemetry not enabled. Set LANGFUSE_PUBLIC_KEY and "
            "LANGFUSE_SECRET_KEY environment variables to enable."
        )
    
    return telemetry


def force_flush_telemetry():
    """
    Force flush telemetry to ensure traces are sent.
    
    This is important for short-lived scripts or when you need
    to ensure traces are sent immediately.
    """
    try:
        from strands.telemetry import StrandsTelemetry
        telemetry = StrandsTelemetry()
        if hasattr(telemetry, 'tracer_provider') and hasattr(telemetry.tracer_provider, 'force_flush'):
            telemetry.tracer_provider.force_flush()
            logger.debug("Telemetry flushed successfully")
    except Exception as e:
        logger.warning(f"Failed to flush telemetry: {e}")