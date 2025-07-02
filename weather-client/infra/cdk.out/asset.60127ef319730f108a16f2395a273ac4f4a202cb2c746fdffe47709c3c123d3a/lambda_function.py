import json
import os
from datetime import datetime
from typing import Dict, Any

# AWS Lambda Powertools for structured logging, metrics, and tracing
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize Powertools
logger = Logger()
tracer = Tracer()
metrics = Metrics()

@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    AWS Lambda function handler for Hello World with Function URL
    
    Args:
        event: Lambda event object containing request details
        context: Lambda context object containing runtime information
        
    Returns:
        Dict containing HTTP response with status code, headers, and body
    """
    try:
        # Add metrics for successful invocations
        metrics.add_metric(name="Invocations", unit=MetricUnit.Count, value=1)
        
        # Extract HTTP method and path
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        path = event.get('requestContext', {}).get('http', {}).get('path', '/')
        
        # Log request details (structured logging)
        logger.info("Processing request", extra={
            "http_method": http_method,
            "path": path,
            "user_agent": event.get('headers', {}).get('user-agent', 'unknown')
        })
        
        # Handle different routes
        if path == '/health':
            metrics.add_metric(name="HealthChecks", unit=MetricUnit.Count, value=1)
            return create_response(200, {'status': 'healthy', 'message': 'Lambda function is running'})
        elif path == '/' or path == '/hello':
            metrics.add_metric(name="HelloRequests", unit=MetricUnit.Count, value=1)
            return handle_hello_world(event, http_method)
        else:
            metrics.add_metric(name="NotFoundRequests", unit=MetricUnit.Count, value=1)
            logger.warning("Path not found", extra={"requested_path": path})
            return create_response(404, {'error': 'Not Found', 'message': f'Path {path} not found'})
            
    except Exception as e:
        metrics.add_metric(name="Errors", unit=MetricUnit.Count, value=1)
        logger.error("Error processing request", extra={
            "error": str(e),
            "path": event.get('requestContext', {}).get('http', {}).get('path', '/'),
            "method": event.get('requestContext', {}).get('http', {}).get('method', 'UNKNOWN')
        })
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })

@tracer.capture_method
def handle_hello_world(event: Dict[str, Any], method: str) -> Dict[str, Any]:
    """Handle the hello world endpoint"""
    
    if method == 'GET':
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        name = query_params.get('name', 'World')
        
        response_body = {
            'message': f'Hello, {name}!',
            'timestamp': context_timestamp(),
            'method': method,
            'function_name': os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'local-test'),
            'version': os.getenv('AWS_LAMBDA_FUNCTION_VERSION', '$LATEST')
        }
        
        return create_response(200, response_body)
    
    elif method == 'POST':
        # Handle POST request with JSON body
        try:
            body = json.loads(event.get('body', '{}'))
            name = body.get('name', 'World')
            
            response_body = {
                'message': f'Hello, {name}! (via POST)',
                'received_data': body,
                'timestamp': context_timestamp()
            }
            
            return create_response(200, response_body)
            
        except json.JSONDecodeError:
            return create_response(400, {
                'error': 'Bad Request',
                'message': 'Invalid JSON in request body'
            })
    
    else:
        return create_response(405, {
            'error': 'Method Not Allowed',
            'message': f'Method {method} not supported'
        })

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a properly formatted HTTP response for Lambda Function URL
    
    Args:
        status_code: HTTP status code
        body: Response body as dictionary
        
    Returns:
        Formatted response dictionary
    """
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Configure appropriately for production
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps(body, indent=2)
    }

def context_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.utcnow().isoformat() + 'Z'
