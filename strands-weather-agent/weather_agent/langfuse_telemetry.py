"""
Langfuse Telemetry Integration for AWS Strands Weather Agent

This module provides Langfuse v3 observability integration for the weather agent,
following AWS Strands best practices for OpenTelemetry integration.

Key Features:
- Automatic OTEL configuration for Langfuse v3
- Session and user tracking with v3 patterns
- Tagging and metadata support
- Proper telemetry initialization with v3 tracing_enabled parameter
- Support for evaluation and scoring with v3 API
- Deterministic trace ID generation for reliable scoring
"""

import os
import base64
import logging
import requests
from typing import Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

if TYPE_CHECKING:
    from langfuse import Langfuse

# Load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
except ImportError:
    pass

from strands.telemetry import StrandsTelemetry

# Import Langfuse v3 for direct client operations
try:
    from langfuse import Langfuse
    LANGFUSE_V3_AVAILABLE = True
except ImportError:
    LANGFUSE_V3_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Langfuse v3 not available. Some features will be disabled.")

# Configure logging
logger = logging.getLogger(__name__)

# Global flag to track if telemetry has been initialized
_TELEMETRY_INITIALIZED = False

# Global cache for availability check
_LANGFUSE_AVAILABLE_CACHE = None
_LAST_AVAILABILITY_CHECK = None


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
                 environment: str = "production",
                 auto_initialize: bool = True):
        """
        Initialize Langfuse telemetry configuration.
        
        Args:
            public_key: Langfuse public key (or from env)
            secret_key: Langfuse secret key (or from env)
            host: Langfuse host URL (or from env)
            service_name: Service name for OTEL
            environment: Deployment environment
            auto_initialize: Whether to auto-initialize if Langfuse is available
        """
        # Get credentials from environment if not provided
        self.public_key = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        self.host = host or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        self.service_name = service_name
        self.environment = environment
        self.telemetry_initialized = False
        
        logger.info(f"🔍 Langfuse Telemetry Init - Host: {self.host}, Service: {self.service_name}")
        
        # Check if we should auto-initialize
        if auto_initialize:
            if not self.public_key or not self.secret_key:
                logger.info("📋 Langfuse credentials not found - telemetry disabled")
            else:
                logger.info(f"🌐 Checking Langfuse connectivity at {self.host}...")
                if self.check_langfuse_available():
                    self._setup_langfuse_telemetry()
                else:
                    logger.warning(f"⚠️ Langfuse not reachable at {self.host} - continuing without telemetry")
    
    def check_langfuse_available(self) -> bool:
        """
        Check if Langfuse is available and reachable.
        
        This method performs a quick health check to determine if Langfuse
        should be used. Results are cached for 60 seconds to avoid repeated checks.
        
        Returns:
            True if Langfuse is available, False otherwise
        """
        global _LANGFUSE_AVAILABLE_CACHE, _LAST_AVAILABILITY_CHECK
        
        # Check cache first (60 second TTL)
        if _LAST_AVAILABILITY_CHECK and _LANGFUSE_AVAILABLE_CACHE is not None:
            cache_age = (datetime.now() - _LAST_AVAILABILITY_CHECK).total_seconds()
            if cache_age < 60:
                return _LANGFUSE_AVAILABLE_CACHE
        
        # Validate credentials exist
        if not self.public_key or not self.secret_key:
            _LANGFUSE_AVAILABLE_CACHE = False
            _LAST_AVAILABILITY_CHECK = datetime.now()
            return False
        
        try:
            # Create auth header
            auth_token = base64.b64encode(
                f"{self.public_key}:{self.secret_key}".encode()
            ).decode()
            
            health_url = f"{self.host}/api/public/health"
            logger.debug(f"🔗 Attempting Langfuse health check at: {health_url}")
            
            # Quick health check with 1 second timeout
            response = requests.get(
                health_url,
                headers={"Authorization": f"Basic {auth_token}"},
                timeout=1.0
            )
            
            # Cache and return result
            available = response.status_code in [200, 204]
            _LANGFUSE_AVAILABLE_CACHE = available
            _LAST_AVAILABILITY_CHECK = datetime.now()
            
            if available:
                logger.info(f"✅ Langfuse health check successful at {self.host} (status: {response.status_code})")
            else:
                logger.warning(f"❌ Langfuse health check failed at {self.host} with status {response.status_code}")
                logger.debug(f"Response: {response.text[:200]}")
                
            return available
            
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Langfuse health check timed out after 1 second at {self.host}")
            _LANGFUSE_AVAILABLE_CACHE = False
            _LAST_AVAILABILITY_CHECK = datetime.now()
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 Cannot connect to Langfuse at {self.host}: {e}")
            _LANGFUSE_AVAILABLE_CACHE = False
            _LAST_AVAILABILITY_CHECK = datetime.now()
            return False
        except Exception as e:
            logger.warning(f"❌ Langfuse health check failed: {type(e).__name__}: {e}")
            _LANGFUSE_AVAILABLE_CACHE = False
            _LAST_AVAILABILITY_CHECK = datetime.now()
            return False
    
    def _setup_langfuse_telemetry(self):
        """
        Set up Langfuse telemetry with proper OTEL configuration.
        
        Critical configuration points:
        1. Use signal-specific endpoint (/api/public/otel/v1/traces)
        2. Set environment variables BEFORE importing Strands
        3. Explicitly initialize StrandsTelemetry
        4. Use proper authentication headers
        """
        global _TELEMETRY_INITIALIZED
        
        # Skip if already initialized globally
        if _TELEMETRY_INITIALIZED:
            logger.info("Langfuse telemetry already initialized, skipping")
            self.telemetry_initialized = True
            return
            
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
            _TELEMETRY_INITIALIZED = True  # Set global flag
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
                               environment: Optional[str] = None) -> Optional[LangfuseTelemetry]:
    """
    Configure Langfuse telemetry from environment variables with auto-detection.
    
    This function will automatically detect if Langfuse is available and configure
    telemetry accordingly. No explicit enable flag is needed.
    
    Environment variables checked:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_HOST (optional, defaults to cloud.langfuse.com)
    
    Args:
        service_name: Name of the service for tracking
        environment: Environment name (defaults to ENVIRONMENT env var or 'production')
        
    Returns:
        Configured LangfuseTelemetry instance if available, None otherwise
    """
    env = environment or os.getenv("ENVIRONMENT", "production")
    
    # Check if basic credentials exist
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        logger.info("Langfuse credentials not found - telemetry disabled")
        return None
    
    logger.info("Checking Langfuse availability...")
    
    telemetry = LangfuseTelemetry(
        service_name=service_name,
        environment=env,
        auto_initialize=True  # Will check availability and initialize if reachable
    )
    
    if telemetry.is_enabled():
        logger.info(f"✅ Langfuse telemetry active at {telemetry.host}")
        return telemetry
    else:
        logger.info("ℹ️  Langfuse not available - continuing without telemetry")
        return None


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


def get_langfuse_client() -> Optional['Langfuse']:
    """
    Get a Langfuse v3 client for direct operations like scoring.
    
    This client is separate from the OTEL telemetry and is used for
    operations that require the Langfuse API directly.
    
    Returns:
        Langfuse client or None if not available/configured
    """
    if not LANGFUSE_V3_AVAILABLE:
        logger.warning("Langfuse v3 not available")
        return None
    
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    
    if not public_key or not secret_key:
        logger.warning("Langfuse credentials not configured")
        return None
    
    try:
        # Create Langfuse v3 client with tracing_enabled parameter
        client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
            tracing_enabled=True  # v3 parameter
        )
        return client
    except Exception as e:
        logger.error(f"Failed to create Langfuse client: {e}")
        return None


def create_deterministic_trace_id(seed: str) -> Optional[str]:
    """
    Create a deterministic trace ID using Langfuse v3.
    
    This is useful for:
    - Correlating traces with external systems
    - Reliable scoring in test scenarios
    - Maintaining trace consistency across retries
    
    Args:
        seed: Unique seed string for generating the trace ID
        
    Returns:
        W3C-compliant trace ID or None if v3 not available
    """
    if not LANGFUSE_V3_AVAILABLE:
        return None
    
    try:
        # Use Langfuse v3's deterministic trace ID generation
        trace_id = Langfuse.create_trace_id(seed=seed)
        return trace_id
    except Exception as e:
        logger.error(f"Failed to create deterministic trace ID: {e}")
        return None


def get_current_trace_id() -> Optional[str]:
    """Get the current trace ID from the active span context."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            if span_context and span_context.is_valid:
                # Convert trace ID to hex string format
                return format(span_context.trace_id, '032x')
    except Exception as e:
        logger.debug(f"Could not get current trace ID: {e}")
    return None


def get_langfuse_host() -> str:
    """Get the configured Langfuse host URL."""
    return os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")