#!/bin/bash

# Comprehensive test script for local development
# Tests health checks and all endpoints

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CLIENT_URL="http://localhost:8080"
SERVER_URL="http://localhost:8081"

echo "========================================"
echo "Local Development Testing"
echo "========================================"
echo ""

# Function to check endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_code=$3
    
    echo -n "Checking $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$response" = "$expected_code" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $response)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $response, expected $expected_code)"
        return 1
    fi
}

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

# 1. Basic Health Checks
echo "1. Health Checks"
echo "================"
echo ""

check_endpoint "Server" "$SERVER_URL/health" "200"
check_endpoint "Client" "$CLIENT_URL/health" "200"
echo ""

# 2. API Endpoints
echo "2. API Endpoints"
echo "================"
echo ""

# Test getting all employees
test_endpoint "GET" "$CLIENT_URL/employees" "" "Get all knowledge specialists"

# Test asking a specialist
test_endpoint "POST" "$CLIENT_URL/ask/1" \
    '{"question": "What are the main components of modern aircraft navigation systems?"}' \
    "Ask Dr. Sarah Chen about aircraft systems"

# Test error handling
test_endpoint "POST" "$CLIENT_URL/ask/999" \
    '{"question": "Test question"}' \
    "Ask non-existent employee (error test)"

# 3. Quick Functionality Test
echo ""
echo "3. Quick Functionality Test"
echo "=========================="
echo ""

echo "Getting employee list..."
response=$(curl -s http://localhost:8080/employees)
if command -v jq &> /dev/null; then
    count=$(echo "$response" | jq -r '.employees | length // 0')
    echo -e "${GREEN}✓${NC} Found $count knowledge specialists"
else
    echo "$response"
fi

echo ""
echo "========================================"
echo "Testing Complete!"
echo "========================================"
echo ""
echo "Note: If you see 'Unable to locate credentials' errors,"
echo "this is expected without AWS credentials configured."
echo "Run './scripts/setup.sh' to configure AWS Bedrock access."