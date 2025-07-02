import json
import logging
import os
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.getenv('LOG_LEVEL', 'INFO'))

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function handler for Hello World with Function URL
    
    Args:
        event: Lambda event object containing request details
        context: Lambda context object containing runtime information
        
    Returns:
        Dict containing HTTP response with status code, headers, and body
    """
    try:
        # Log the incoming event for debugging (be careful with sensitive data in production)
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract HTTP method and path
        http_method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
        path = event.get('requestContext', {}).get('http', {}).get('path', '/')
        
        # Handle different routes
        if path == '/health':
            return create_response(200, {'status': 'healthy', 'message': 'Lambda function is running'})
        elif path == '/' or path == '/hello':
            return handle_hello_world(event, http_method)
        else:
            return create_response(404, {'error': 'Not Found', 'message': f'Path {path} not found'})
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return create_response(500, {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        })

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
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'
