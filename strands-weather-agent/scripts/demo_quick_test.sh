#!/bin/bash

# Quick Demo Test Script for Strands Weather Agent
# This script demonstrates the key features of the setup

set -e

echo "🌤️  Strands Weather Agent - Quick Demo Test"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test endpoints
test_endpoint() {
    local name=$1
    local url=$2
    echo -n "Testing $name... "
    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "❌"
        return 1
    fi
}

# Function to run a query
run_query() {
    local query=$1
    echo -e "\n${BLUE}Query:${NC} \"$query\""
    
    response=$(curl -s -X POST http://localhost:7777/query \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" 2>/dev/null | jq -r '.response' 2>/dev/null || echo "Error")
    
    # Truncate response for display
    if [ "${#response}" -gt 200 ]; then
        echo -e "${GREEN}Response:${NC} ${response:0:200}..."
    else
        echo -e "${GREEN}Response:${NC} $response"
    fi
}

# 1. Check Services
echo -e "${YELLOW}1. Service Health Checks${NC}"
echo "------------------------"
test_endpoint "Weather Agent API" "http://localhost:7777/health"
test_endpoint "Forecast Server" "http://localhost:7778/health"
test_endpoint "Historical Server" "http://localhost:7779/health"
test_endpoint "Agricultural Server" "http://localhost:7780/health"

# 2. Check Telemetry
echo -e "\n${YELLOW}2. Telemetry Status${NC}"
echo "-------------------"
TELEMETRY_ENABLED=$(docker exec weather-agent-app env | grep ENABLE_TELEMETRY | cut -d= -f2)
if [ "$TELEMETRY_ENABLED" = "true" ]; then
    echo -e "Langfuse Telemetry: ${GREEN}Enabled${NC}"
    echo "Dashboard: http://localhost:3000"
else
    echo -e "Langfuse Telemetry: Disabled"
fi

# 3. Run Demo Queries
echo -e "\n${YELLOW}3. Demo Queries${NC}"
echo "---------------"

# Basic weather query
run_query "What's the weather in Seattle?"

# Multi-location comparison
run_query "Compare the weather between Miami and Boston"

# Agricultural query
run_query "Is it good weather for planting corn in Iowa?"

# 4. Session Management
echo -e "\n${YELLOW}4. Session Management${NC}"
echo "--------------------"
SESSION_COUNT=$(curl -s http://localhost:7777/sessions | jq '.sessions | length' 2>/dev/null || echo "0")
echo -e "Active Sessions: ${GREEN}$SESSION_COUNT${NC}"

# 5. Performance Check
echo -e "\n${YELLOW}5. Performance Metrics${NC}"
echo "---------------------"
START_TIME=$(date +%s%N)
curl -s -X POST http://localhost:7777/query \
    -H "Content-Type: application/json" \
    -d '{"query": "Weather in NYC?"}' > /dev/null 2>&1
END_TIME=$(date +%s%N)
ELAPSED=$((($END_TIME - $START_TIME) / 1000000))
echo -e "Query Response Time: ${GREEN}${ELAPSED}ms${NC}"

# 6. API Documentation
echo -e "\n${YELLOW}6. Available Resources${NC}"
echo "---------------------"
echo "📚 API Documentation: http://localhost:7777/docs"
echo "📊 Langfuse Dashboard: http://localhost:3000"
echo "🔍 Health Check: http://localhost:7777/health"

echo -e "\n${GREEN}✨ Demo test complete!${NC}"
echo ""
echo "To run more queries:"
echo "  - Interactive mode: docker exec -it weather-agent-app python -m weather_agent.chatbot"
echo "  - API mode: Use the /query endpoint as shown above"
echo ""
echo "To view logs:"
echo "  - All services: docker compose logs -f"
echo "  - Weather agent only: docker compose logs -f weather-agent"