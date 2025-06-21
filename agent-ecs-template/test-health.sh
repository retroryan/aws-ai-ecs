#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================="
echo "Client-Server Health Check"
echo "=============================="
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

# Function to check JSON response
check_json_health() {
    local name=$1
    local url=$2
    
    echo ""
    echo "Detailed $name Health Check:"
    echo "----------------------------"
    
    response=$(curl -s "$url")
    
    if command -v jq &> /dev/null; then
        echo "$response" | jq .
    else
        echo "$response"
    fi
    
    # Parse specific fields
    if command -v jq &> /dev/null; then
        status=$(echo "$response" | jq -r '.status // "unknown"')
        
        if [ "$status" = "healthy" ]; then
            echo -e "Status: ${GREEN}$status${NC}"
        else
            echo -e "Status: ${RED}$status${NC}"
        fi
        
        # Check server connectivity for client
        if [[ "$name" == "Client" ]]; then
            connectivity=$(echo "$response" | jq -r '.server_connectivity // "unknown"')
            echo -n "Server Connectivity: "
            
            case "$connectivity" in
                "connected")
                    echo -e "${GREEN}$connectivity${NC}"
                    ;;
                "unreachable"|"timeout")
                    echo -e "${RED}$connectivity${NC}"
                    ;;
                *)
                    echo -e "${YELLOW}$connectivity${NC}"
                    ;;
            esac
            
            # Show server status if available
            server_status=$(echo "$response" | jq -r '.server_status.status // "unknown"')
            if [ "$server_status" != "unknown" ]; then
                echo "Server Status (via client): $server_status"
            fi
        fi
    fi
}

# Main health checks
echo "1. Basic Connectivity Tests"
echo "============================"

check_endpoint "Server Direct" "http://localhost:8081/health" "200"
server_direct=$?

check_endpoint "Client" "http://localhost:8080/health" "200"
client_health=$?

# Detailed health checks
echo ""
echo "2. Detailed Health Information"
echo "=============================="

check_json_health "Server" "http://localhost:8081/health"
check_json_health "Client" "http://localhost:8080/health"

# Functional test
echo ""
echo "3. Functional Test"
echo "=================="
echo "Testing inquiry endpoint with Python skills search..."
echo ""

response=$(curl -s -X POST http://localhost:8080/inquire \
    -H "Content-Type: application/json" \
    -d '{"question": "Find employees with Python skills"}')

if command -v jq &> /dev/null; then
    count=$(echo "$response" | jq -r '.count // 0')
    echo "Results found: $count employees"
    echo ""
    echo "Response:"
    echo "$response" | jq .
else
    echo "Response:"
    echo "$response"
fi

# Summary
echo ""
echo "=============================="
echo "Summary"
echo "=============================="

total_checks=2
passed_checks=$((server_direct == 0 ? 1 : 0))
passed_checks=$((passed_checks + (client_health == 0 ? 1 : 0)))

if [ $passed_checks -eq $total_checks ]; then
    echo -e "${GREEN}✓ All health checks passed!${NC} ($passed_checks/$total_checks)"
    exit 0
else
    echo -e "${RED}✗ Some health checks failed!${NC} ($passed_checks/$total_checks)"
    exit 1
fi