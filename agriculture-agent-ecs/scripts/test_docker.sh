#!/bin/bash

# Docker Integration Test Script
set -e

echo "🐳 Docker Integration Test"
echo "========================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if a service is healthy
check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "Checking $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗${NC}"
    return 1
}

# Check if .env file exists
if [ ! -f ../.env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Copying from .env.docker${NC}"
    cp ../.env.docker ../.env
    echo "Please edit .env file with your AWS Bedrock configuration"
    exit 1
fi

# Check if BEDROCK_MODEL_ID is set
if ! grep -q "^BEDROCK_MODEL_ID=" ../.env || [ -z "$(grep "^BEDROCK_MODEL_ID=" ../.env | cut -d'=' -f2)" ]; then
    echo -e "${RED}Error: BEDROCK_MODEL_ID not set in .env file${NC}"
    echo "Please set BEDROCK_MODEL_ID to a valid AWS Bedrock model ID"
    exit 1
fi

echo "1. Building Docker images..."
cd .. && docker-compose build

echo ""
echo "2. Starting services..."
cd .. && docker-compose up -d

echo ""
echo "3. Waiting for services to be healthy..."
echo ""

# Check each service
services_ok=true

if ! check_service "Forecast Server" "http://localhost:7071/health"; then
    services_ok=false
fi

if ! check_service "Historical Server" "http://localhost:7072/health"; then
    services_ok=false
fi

if ! check_service "Agricultural Server" "http://localhost:7073/health"; then
    services_ok=false
fi

if ! check_service "Weather Agent" "http://localhost:8000/health"; then
    services_ok=false
fi

if [ "$services_ok" = false ]; then
    echo ""
    echo -e "${RED}Some services failed to start. Checking logs...${NC}"
    echo ""
    cd .. && docker-compose logs --tail=20
    echo ""
    echo "Stopping services..."
    cd .. && docker-compose down
    exit 1
fi

echo ""
echo -e "${GREEN}All services are healthy!${NC}"
echo ""
echo "4. Running test queries..."
echo ""

# Function to test a query
test_query() {
    local query=$1
    echo "Query: \"$query\""
    
    response=$(curl -s -X POST http://localhost:8000/query \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" | jq -r '.response' 2>/dev/null || echo "Error")
    
    if [ "$response" != "Error" ] && [ -n "$response" ]; then
        echo -e "Response: ${GREEN}✓${NC} $(echo "$response" | head -n 2)..."
    else
        echo -e "Response: ${RED}✗ Failed${NC}"
    fi
    echo ""
}

# Test different types of queries
test_query "What's the weather forecast for Chicago?"
test_query "Show me historical weather for Seattle last week"
test_query "Are conditions good for planting corn in Iowa?"

echo "5. Checking container logs for errors..."
if cd .. && docker-compose logs | grep -i "error" | grep -v "Error handling" > /dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Found errors in logs${NC}"
else
    echo -e "${GREEN}No errors found in logs${NC}"
fi

echo ""
echo "6. Service URLs:"
echo "   - Weather Agent API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Health Check: http://localhost:8000/health"
echo ""
echo "   MCP Servers (internal):"
echo "   - Forecast: http://localhost:7071"
echo "   - Historical: http://localhost:7072"
echo "   - Agricultural: http://localhost:7073"
echo ""

echo -e "${GREEN}✅ Docker integration test completed successfully!${NC}"
echo ""
echo "To stop all services, run: cd .. && docker-compose down"
echo "To view logs, run: cd .. && docker-compose logs -f"
echo ""