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
        endpoint = f"{host}/api/public/otel/v1/traces"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"] = endpoint
        os.environ["OTEL_EXPORTER_OTLP_TRACES_HEADERS"] = f"Authorization=Basic {auth}"
        os.environ["OTEL_EXPORTER_OTLP_TRACES_PROTOCOL"] = "http/protobuf"
        
        # Initialize telemetry
        telemetry = StrandsTelemetry()
        telemetry.setup_otlp_exporter()
        
        # Log detailed connection information with enhanced debugging
        logger.info("="*60)
        logger.info("📊 LANGFUSE TELEMETRY CONFIGURATION")
        logger.info("="*60)
        logger.info(f"Service Name: {service_name}")
        logger.info(f"Version: {version}")
        logger.info(f"Environment: {environment}")
        logger.info(f"Langfuse Host: {host}")
        logger.info(f"OTEL Endpoint: {endpoint}")
        logger.info(f"Public Key: {pk[:8]}...{pk[-8:]}" if len(pk) > 20 else f"Public Key: {pk}")
        logger.info(f"Secret Key: {sk[:8]}...{sk[-8:]}" if len(sk) > 20 else f"Secret Key: {sk}")
        logger.info(f"Auth Header (first 20 chars): {auth[:20]}...")
        logger.info(f"Protocol: http/protobuf")
        logger.info("Status: ✅ ENABLED")
        logger.info("="*60)
        
        # Additional debug logging for troubleshooting
        logger.debug(f"Full OTEL_EXPORTER_OTLP_TRACES_ENDPOINT: {os.environ.get('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT')}")
        logger.debug(f"Full OTEL_EXPORTER_OTLP_TRACES_HEADERS: {os.environ.get('OTEL_EXPORTER_OTLP_TRACES_HEADERS')[:50]}...")
        logger.debug(f"Full OTEL_SERVICE_NAME: {os.environ.get('OTEL_SERVICE_NAME')}")
        logger.debug(f"Full OTEL_RESOURCE_ATTRIBUTES: {os.environ.get('OTEL_RESOURCE_ATTRIBUTES')}")
        
        return True
    
    # Log detailed information about missing configuration
    logger.info("="*60)
    logger.info("📊 LANGFUSE TELEMETRY CONFIGURATION")
    logger.info("="*60)
    logger.info(f"Service Name: {service_name}")
    logger.info(f"Version: {version}")
    logger.info(f"Environment: {environment}")
    logger.info(f"Langfuse Host: {host}")
    logger.info(f"Public Key: {pk[:8]}...{pk[-8:]}" if pk else "NOT SET")
    logger.info(f"Secret Key: {sk[:8]}...{sk[-8:]}" if sk else "NOT SET")
    logger.info(f"Status: ❌ DISABLED ({'missing credentials' if not pk or not sk else 'configuration error'})")
    logger.info("="*60)
    
    return False