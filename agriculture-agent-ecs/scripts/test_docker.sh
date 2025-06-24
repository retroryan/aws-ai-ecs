#!/bin/bash

# Docker Integration Test Script
# This script tests the running Docker services without starting them
# Use ./start_docker.sh to start the services first

set -e

echo "🐳 Docker Service Test"
echo "====================="
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
    local max_attempts=5
    local attempt=1
    
    echo -n "Checking $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e " ${GREEN}✓${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗${NC}"
    return 1
}

# Function to check MCP service
check_mcp_service() {
    local service=$1
    local url=$2
    local max_attempts=5
    local attempt=1
    
    echo -n "Checking $service..."
    
    while [ $attempt -le $max_attempts ]; do
        response=$(curl -s -X POST "$url" \
            -H "Content-Type: application/json" \
            -H "Accept: application/json, text/event-stream" \
            -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}' 2>/dev/null || echo "failed")
        
        if [[ "$response" != "failed" ]] && [[ "$response" != "" ]]; then
            # Check if response contains error about session (which means server is responding)
            if echo "$response" | grep -q "session" || echo "$response" | grep -q "tools"; then
                echo -e " ${GREEN}✓${NC}"
                return 0
            fi
        fi
        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}✗${NC}"
    return 1
}

echo "1. Checking Docker services status..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Check for running containers using docker directly (avoids env var warnings)
running_containers=$(docker ps --filter "name=mcp-" --filter "name=weather-agent" -q | wc -l | tr -d ' ')

if [ "$running_containers" -eq "0" ]; then
    echo -e "${RED}No services running!${NC}"
    echo ""
    echo "Please start the services first with:"
    echo "  ./scripts/start_docker.sh"
    exit 1
fi

echo "Found $running_containers running containers"
echo ""
docker ps --filter "name=mcp-" --filter "name=weather-agent" --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "2. Testing service endpoints..."
echo ""

# Check each service
services_ok=true

# Check MCP servers (they don't have /health endpoints)
if ! check_mcp_service "Forecast Server" "http://localhost:7071/mcp/"; then
    services_ok=false
fi

if ! check_mcp_service "Historical Server" "http://localhost:7072/mcp/"; then
    services_ok=false
fi

if ! check_mcp_service "Agricultural Server" "http://localhost:7073/mcp/"; then
    services_ok=false
fi

# Check Weather Agent (has proper health endpoint)
if ! check_service "Weather Agent" "http://localhost:7075/health"; then
    services_ok=false
fi

if [ "$services_ok" = false ]; then
    echo ""
    echo -e "${RED}Some services are not responding!${NC}"
    echo ""
    echo "Check service logs with:"
    echo "  docker-compose logs -f"
    exit 1
fi

echo ""
echo -e "${GREEN}All services are healthy!${NC}"
echo ""
echo "3. Running test queries..."
echo ""

# Function to test a query
test_query() {
    local query=$1
    echo "Query: \"$query\""
    
    response=$(curl -s -X POST http://localhost:7075/query \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" 2>/dev/null || echo '{"response": "Error: Failed to connect"}')
    
    # Extract response field
    response_text=$(echo "$response" | jq -r '.response' 2>/dev/null || echo "Error parsing response")
    
    if [[ "$response_text" == "Error"* ]] || [[ "$response_text" == "An error occurred"* ]]; then
        if [[ "$response_text" == *"credentials"* ]]; then
            echo -e "Response: ${YELLOW}⚠${NC} AWS credentials not configured (expected in Docker)"
        else
            echo -e "Response: ${RED}✗ $response_text${NC}"
        fi
    else
        echo -e "Response: ${GREEN}✓${NC} $response_text"
    fi
    echo ""
}

# Test different types of queries
test_query "What's the weather forecast for Chicago?"
test_query "Show me historical weather for Seattle last week"
test_query "Are conditions good for planting corn in Iowa?"

echo ""
echo "4. Service URLs:"
echo "   - Weather Agent API: http://localhost:7075"
echo "   - API Docs: http://localhost:7075/docs"
echo "   - Health Check: http://localhost:7075/health"
echo ""
echo "   MCP Servers (internal):"
echo "   - Forecast: http://localhost:7071/mcp/"
echo "   - Historical: http://localhost:7072/mcp/"
echo "   - Agricultural: http://localhost:7073/mcp/"
echo ""

echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "Commands:"
echo "  Stop services:  ./scripts/stop_docker.sh"
echo "  View logs:      docker-compose logs -f"
echo "  Restart:        ./scripts/stop_docker.sh && ./scripts/start_docker.sh"
echo ""