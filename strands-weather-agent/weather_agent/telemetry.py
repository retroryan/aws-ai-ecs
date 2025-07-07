"""Simple telemetry setup for AWS Strands Weather Agent Demo

This module demonstrates the correct way to integrate Strands with Langfuse:
- OTEL environment variables MUST be set before importing Strands
- Uses signal-specific endpoint (/api/public/otel/v1/traces)
- Explicit telemetry initialization with StrandsTelemetry
- Clean, educational demo pattern
"""
import os
import base64
import logging
from strands.telemetry import StrandsTelemetry

logger = logging.getLogger(__name__)


def setup_telemetry(service_name: str = "weather-agent", 
                   environment: str = "demo",
                   version: str = "2.0.0") -> bool:
    """Setup OTEL for Langfuse if credentials exist
    
    Args:
        service_name: Name for service identification in traces
        environment: Deployment environment (e.g., 'demo', 'production')
        version: Service version
        
    Returns:
        bool: True if telemetry was enabled, False otherwise
    """
    pk = os.getenv("LANGFUSE_PUBLIC_KEY")
    sk = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
    
    if pk and sk:
        # Create auth token
        auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
        
        # Configure service metadata for better trace identification
        os.environ["OTEL_SERVICE_NAME"] = service_name
        os.environ["OTEL_RESOURCE_ATTRIBUTES"] = f"service.version={version},deployment.environment={environment}"
        
        # CRITICAL: Use signal-specific endpoint for traces
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = f"{host}/api/public/otel/v1/traces"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"
        
        # Initialize telemetry
        telemetry = StrandsTelemetry()
        telemetry.setup_otlp_exporter()
        logger.info(f"Langfuse telemetry enabled for {service_name} v{version} ({environment})")
        return True
    
    logger.info("Langfuse telemetry not configured (credentials not found)")
    return False