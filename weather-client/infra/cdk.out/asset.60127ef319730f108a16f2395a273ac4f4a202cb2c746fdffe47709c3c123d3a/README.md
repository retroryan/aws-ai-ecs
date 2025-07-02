# Hello World AWS Lambda Function with Function URL

This is a simple Hello World AWS Lambda function designed to work with Lambda Function URLs, following AWS best practices.

## Features

- **Multiple endpoints**: `/`, `/hello`, and `/health`
- **HTTP methods**: Supports both GET and POST requests
- **Query parameters**: GET requests can include a `name` parameter
- **JSON POST body**: POST requests can send JSON data
- **Health check endpoint**: `/health` for monitoring
- **Error handling**: Proper error responses and logging
- **CORS headers**: Configured for web browser compatibility
- **Type hints**: Full Python type annotations
- **Structured logging**: Uses AWS Lambda's built-in logging

## Project Structure

```
weather_lambda/
├── lambda_function.py      # Main Lambda function code
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container for local testing
├── test_lambda_local.sh   # Script to test locally
└── README.md             # This file
```

## AWS Best Practices Implemented

1. **Error Handling**: Comprehensive try-catch blocks with proper HTTP status codes
2. **Logging**: Structured logging with configurable log levels
3. **Type Hints**: Full type annotations for better code maintainability
4. **Environment Variables**: Uses AWS Lambda environment variables
5. **Security**: CORS headers configured (customize for production)
6. **Performance**: Minimal dependencies and efficient code structure
7. **Monitoring**: Health check endpoint for monitoring systems

## Local Testing

### Prerequisites
- Docker installed on your system
- Python 3.11+ (for development)

### Run Local Tests

```bash
# Navigate to the weather_lambda directory
cd weather_lambda

# Run the test script (builds Docker image and runs tests)
./test_lambda_local.sh
```

The test script will:
1. Build the Docker image
2. Start the Lambda container
3. Run automated tests on all endpoints
4. Display results and container logs
5. Keep the container running for manual testing

### Manual Testing

While the container is running, you can test manually:

```bash
# Health check
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"requestContext":{"http":{"method":"GET","path":"/health"}}}'

# Hello World with query parameter
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"requestContext":{"http":{"method":"GET","path":"/hello"}},"queryStringParameters":{"name":"Developer"}}'

# POST request with JSON body
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"requestContext":{"http":{"method":"POST","path":"/hello"}},"body":"{\"name\":\"Lambda User\"}"}'
```

## Deployment to AWS

### Using AWS CLI

1. **Create deployment package**:
```bash
zip -r lambda-function.zip lambda_function.py
```

2. **Create Lambda function**:
```bash
aws lambda create-function \
  --function-name hello-world-lambda \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR-ACCOUNT:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda-function.zip
```

3. **Create Function URL**:
```bash
aws lambda create-function-url-config \
  --function-name hello-world-lambda \
  --auth-type NONE \
  --cors '{
    "AllowCredentials": false,
    "AllowHeaders": ["Content-Type"],
    "AllowMethods": ["GET", "POST", "OPTIONS"],
    "AllowOrigins": ["*"],
    "MaxAge": 300
  }'
```

### Using AWS SAM or CDK

For production deployments, consider using AWS SAM or AWS CDK for infrastructure as code.

## API Endpoints

### GET /health
Returns health status of the Lambda function.

**Response**:
```json
{
  "status": "healthy",
  "message": "Lambda function is running"
}
```

### GET / or GET /hello
Returns a hello world message.

**Query Parameters**:
- `name` (optional): Name to greet (defaults to "World")

**Response**:
```json
{
  "message": "Hello, World!",
  "timestamp": "2024-01-01T12:00:00Z",
  "method": "GET",
  "function_name": "hello-world-lambda",
  "version": "$LATEST"
}
```

### POST /hello
Accepts JSON body and returns personalized greeting.

**Request Body**:
```json
{
  "name": "Developer"
}
```

**Response**:
```json
{
  "message": "Hello, Developer! (via POST)",
  "received_data": {
    "name": "Developer"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Environment Variables

- `LOG_LEVEL`: Set logging level (DEBUG, INFO, WARNING, ERROR)
- `AWS_LAMBDA_FUNCTION_NAME`: Automatically set by AWS Lambda
- `AWS_LAMBDA_FUNCTION_VERSION`: Automatically set by AWS Lambda

## Security Considerations

- CORS is configured to allow all origins (`*`) for development
- For production, configure CORS to allow only specific domains
- Consider adding authentication/authorization for sensitive endpoints
- Review and configure appropriate IAM roles and policies

## Monitoring and Observability

- All requests are logged with structured logging
- Health check endpoint for load balancer/monitoring systems
- Error responses include correlation information
- CloudWatch integration automatic with AWS Lambda
