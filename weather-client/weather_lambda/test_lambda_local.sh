#!/bin/bash

# Script to build, run, and test the Lambda function locally
# This script uses the AWS Lambda Runtime Interface Emulator

set -e  # Exit on any error

# Configuration
IMAGE_NAME="hello-world-lambda"
CONTAINER_NAME="hello-world-lambda-test"
PORT=9000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting Lambda local testing...${NC}"

# Function to cleanup
cleanup() {
    echo -e "${YELLOW}🧹 Cleaning up...${NC}"
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
}

# Trap to ensure cleanup on script exit
trap cleanup EXIT

# Build the Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker build -t $IMAGE_NAME .

# Stop and remove any existing container
cleanup

# Run the container
echo -e "${YELLOW}🐳 Starting Lambda container on port $PORT...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:8080 \
    $IMAGE_NAME

# Wait for container to be ready
echo -e "${YELLOW}⏳ Waiting for Lambda to be ready...${NC}"
sleep 3

# Function to test endpoint
test_endpoint() {
    local method=$1
    local path=$2
    local data=$3
    local description=$4
    
    echo -e "${YELLOW}🧪 Testing: $description${NC}"
    
    local curl_cmd="curl -s -w '\nHTTP Status: %{http_code}\n' -X $method"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi
    
    # Construct the Lambda invocation payload
    local lambda_payload="{
        \"requestContext\": {
            \"http\": {
                \"method\": \"$method\",
                \"path\": \"$path\"
            }
        }"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        lambda_payload="$lambda_payload,
        \"body\": \"$data\""
    fi
    
    if [ "$path" = "/hello" ] && [ "$method" = "GET" ]; then
        lambda_payload="$lambda_payload,
        \"queryStringParameters\": {
            \"name\": \"AWS Developer\"
        }"
    fi
    
    lambda_payload="$lambda_payload}"
    
    local response=$(curl -s -w '\nHTTP_STATUS:%{http_code}' \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$lambda_payload" \
        http://localhost:$PORT/2015-03-31/functions/function/invocations)
    
    local http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    local body=$(echo "$response" | sed '/HTTP_STATUS:/d')
    
    if [ "$http_status" = "200" ]; then
        echo -e "${GREEN}✅ Success!${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Failed with HTTP status: $http_status${NC}"
        echo "$body"
    fi
    echo ""
}

# Test health endpoint
test_endpoint "GET" "/health" "" "Health check"

# Test hello world endpoint
test_endpoint "GET" "/hello" "" "Hello World with query parameter"

# Test root endpoint
test_endpoint "GET" "/" "" "Root endpoint"

# Test POST endpoint
test_endpoint "POST" "/hello" '{"name": "Lambda Developer"}' "POST request with JSON body"

# Test 404 endpoint
test_endpoint "GET" "/nonexistent" "" "404 Not Found test"

# Show container logs
echo -e "${YELLOW}📋 Container logs:${NC}"
docker logs $CONTAINER_NAME

echo -e "${GREEN}🎉 Testing completed!${NC}"
echo -e "${YELLOW}💡 To manually test, you can use:${NC}"
echo "curl -X POST http://localhost:$PORT/2015-03-31/functions/function/invocations \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"requestContext\":{\"http\":{\"method\":\"GET\",\"path\":\"/hello\"}}}'"
echo ""
echo -e "${YELLOW}🛑 Container will be stopped and removed when script exits${NC}"

# Keep the script running so user can do manual testing
read -p "Press Enter to stop the container and exit..."
