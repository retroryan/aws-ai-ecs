#!/bin/bash

# Comprehensive endpoint testing script
# Tests all client and server endpoints with various scenarios

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CLIENT_URL="http://localhost:8080"
SERVER_URL="http://localhost:8081"

echo "========================================"
echo "Comprehensive Endpoint Testing"
echo "========================================"
echo ""

# Function to test endpoint
test_endpoint() {
    local method=$1
    local url=$2
    local data=$3
    local description=$4
    
    echo "Testing: $description"
    echo "Method: $method"
    echo "URL: $url"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$url")
    else
        response=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | grep "HTTP_CODE:" | cut -d':' -f2)
    body=$(echo "$response" | sed '/HTTP_CODE:/d')
    
    if [ "$http_code" = "200" ]; then
        echo -e "Status: ${GREEN}✓ $http_code${NC}"
    else
        echo -e "Status: ${RED}✗ $http_code${NC}"
    fi
    
    echo "Response:"
    echo "$body" | jq . 2>/dev/null || echo "$body"
    echo "----------------------------------------"
    echo ""
}

echo "1. Testing Server Endpoints"
echo "=========================="
echo ""

# Test server home
test_endpoint "GET" "$SERVER_URL/" "" "Server home endpoint"

# Test server health
test_endpoint "GET" "$SERVER_URL/health" "" "Server health check"

# Test server employees list
test_endpoint "GET" "$SERVER_URL/api/employees" "" "Server employees list"

# Test asking a valid employee
test_endpoint "POST" "$SERVER_URL/api/employee/1/ask" \
    '{"question": "What causes turbulence in commercial flights?"}' \
    "Ask Dr. Sarah Chen (valid employee)"

# Test asking invalid employee
test_endpoint "POST" "$SERVER_URL/api/employee/999/ask" \
    '{"question": "Test question"}' \
    "Ask non-existent employee"

# Test missing question
test_endpoint "POST" "$SERVER_URL/api/employee/1/ask" \
    '{}' \
    "Ask without question"

echo ""
echo "2. Testing Client Endpoints"
echo "=========================="
echo ""

# Test client home
test_endpoint "GET" "$CLIENT_URL/" "" "Client home endpoint"

# Test client health
test_endpoint "GET" "$CLIENT_URL/health" "" "Client health check"

# Test client employees list
test_endpoint "GET" "$CLIENT_URL/employees" "" "Client employees list"

# Test asking through client
test_endpoint "POST" "$CLIENT_URL/ask/1" \
    '{"question": "What are the main components of modern aircraft navigation systems?"}' \
    "Ask Dr. Sarah Chen through client"

# Test different specialists
echo ""
echo "3. Testing Different Specialists"
echo "================================"
echo ""

# Test planetary science
test_endpoint "POST" "$CLIENT_URL/ask/2" \
    '{"question": "What is the largest planet in our solar system?"}' \
    "Ask Prof. Marcus Rodriguez about planets"

# Test forest ecology
test_endpoint "POST" "$CLIENT_URL/ask/3" \
    '{"question": "How do trees communicate with each other?"}' \
    "Ask Dr. Emily Thompson about forests"

# Test marine biology
test_endpoint "POST" "$CLIENT_URL/ask/5" \
    '{"question": "What is the deepest part of the ocean?"}' \
    "Ask Dr. Maria Garcia about oceans"

echo ""
echo "========================================"
echo "Testing Complete!"
echo "========================================"
echo ""
echo "Note: If you see 'Unable to locate credentials' errors,"
echo "this is expected in local development without AWS credentials."
echo "Run './aws-setup.sh' to configure AWS Bedrock access."