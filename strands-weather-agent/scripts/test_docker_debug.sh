#!/bin/bash

# Test script for Docker Compose with debug mode
set -e

echo "Testing Docker Compose services with DEBUG mode..."
echo ""

# Navigate to project root
cd "$(dirname "$0")/.."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name... "
    
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    
    if [ "$response_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} (Status: $response_code)"
        return 0
    else
        echo -e "${RED}✗${NC} (Status: $response_code, Expected: $expected_status)"
        return 1
    fi
}

# Function to test query endpoint
test_query() {
    local query=$1
    echo ""
    echo -e "${YELLOW}Testing query:${NC} '$query'"
    
    response=$(curl -s -X POST http://localhost:7777/query \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Query successful${NC}"
        # Extract response text (assuming JSON with 'response' field)
        echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"Response: {data.get('response', 'No response field')[:200]}...\")" 2>/dev/null || echo "$response"
    else
        echo -e "${RED}✗ Query failed${NC}"
    fi
}

# Main testing
echo "=== Docker Compose Services Health Check ==="
echo ""

# Test MCP servers
test_endpoint "http://localhost:7778/health" "Forecast MCP Server"
test_endpoint "http://localhost:7779/health" "Historical MCP Server"
test_endpoint "http://localhost:7780/health" "Agricultural MCP Server"

# Test Weather Agent API
test_endpoint "http://localhost:7777/health" "Weather Agent API"
test_endpoint "http://localhost:7777/info" "Weather Agent Info"

# Test MCP connectivity
echo ""
echo "=== MCP Server Connectivity ==="
mcp_status=$(curl -s http://localhost:7777/mcp/status)
echo "$mcp_status" | python3 -m json.tool 2>/dev/null || echo "$mcp_status"

# Check debug logging status
echo ""
echo "=== Debug Logging Status ==="
agent_info=$(curl -s http://localhost:7777/info)
debug_enabled=$(echo "$agent_info" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('debug_logging', False))" 2>/dev/null || echo "unknown")
if [ "$debug_enabled" = "True" ]; then
    echo -e "${GREEN}✓ Debug logging is ENABLED${NC}"
else
    echo -e "${RED}✗ Debug logging is DISABLED${NC}"
fi

# Test actual queries
echo ""
echo "=== Testing Sample Queries ==="
test_query "What's the weather in Seattle?"

# Check for debug logs
echo ""
echo "=== Checking Debug Logs ==="
echo "Looking for log files in the weather-agent container..."

# Check if container has log files
docker exec weather-agent-app find logs -name "weather_api_debug_*.log" -type f 2>/dev/null | head -5 || echo "No debug log files found"

# Show last few lines of the most recent debug log if it exists
latest_log=$(docker exec weather-agent-app find logs -name "weather_api_debug_*.log" -type f 2>/dev/null | sort -r | head -1)
if [ -n "$latest_log" ]; then
    echo ""
    echo "Latest debug log file: $latest_log"
    echo "Last 10 lines:"
    docker exec weather-agent-app tail -10 "$latest_log" 2>/dev/null || echo "Could not read log file"
fi

echo ""
echo "=== Test Complete ==="