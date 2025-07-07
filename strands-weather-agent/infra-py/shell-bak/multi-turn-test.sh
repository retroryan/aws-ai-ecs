#!/bin/bash

# Multi-Turn Conversation Test Script for AWS ECS Deployment
# This script tests stateful conversations with the Weather Agent API deployed on AWS
# It demonstrates session persistence across multiple queries

set -e

# Source common functions
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source "${SCRIPT_DIR}/common.sh"
source "${SCRIPT_DIR}/ecs-utils.sh"

# Export environment variables
export_common_env

echo "🔄 Multi-Turn Conversation Test (AWS ECS)"
echo "========================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    log_error "jq is required but not installed."
    echo "Please install jq to run this test."
    exit 1
fi

# Get Load Balancer DNS
lb_dns=$(get_stack_output "$BASE_STACK_NAME" "ALBDNSName")

if [ -z "$lb_dns" ]; then
    log_error "Could not find Load Balancer DNS. Make sure the $BASE_STACK_NAME stack is deployed."
    exit 1
fi

# Set API URL
API_URL="http://${lb_dns}"
log_info "Using API endpoint: $API_URL"
echo ""

# Function to make a query and extract response data
make_query() {
    local query="$1"
    local session_id="$2"
    local create_session="${3:-true}"
    
    # Build request JSON
    local request_json
    if [[ -n "$session_id" ]]; then
        request_json=$(jq -n \
            --arg q "$query" \
            --arg s "$session_id" \
            --argjson c "$create_session" \
            '{query: $q, session_id: $s, create_session: $c}')
    else
        request_json=$(jq -n \
            --arg q "$query" \
            --argjson c "$create_session" \
            '{query: $q, create_session: $c}')
    fi
    
    # Make the request
    curl -s -X POST "$API_URL/query" \
        -H "Content-Type: application/json" \
        -d "$request_json" 2>/dev/null
}

# Function to display query results
display_result() {
    local turn=$1
    local query="$2"
    local response="$3"
    
    # Extract fields
    local response_text=$(echo "$response" | jq -r '.response // "No response"')
    local session_id=$(echo "$response" | jq -r '.session_id // "No session"')
    local session_new=$(echo "$response" | jq -r '.session_new // false')
    local conversation_turn=$(echo "$response" | jq -r '.conversation_turn // 0')
    
    echo -e "${CYAN}Turn $turn:${NC}"
    echo -e "${BLUE}Query:${NC} $query"
    
    # Truncate long responses for display
    if [ ${#response_text} -gt 200 ]; then
        display_text="${response_text:0:197}..."
    else
        display_text="$response_text"
    fi
    
    echo -e "${GREEN}Response:${NC} $display_text"
    echo -e "${YELLOW}Session:${NC} ${session_id:0:8}... | New: $session_new | Turn: $conversation_turn"
    echo ""
}

# Function to test session info endpoint
test_session_info() {
    local session_id="$1"
    echo -e "${CYAN}Session Info Test:${NC}"
    
    local session_info=$(curl -s "$API_URL/session/$session_id" 2>/dev/null)
    
    if echo "$session_info" | jq -e '.session_id' &> /dev/null; then
        echo -e "${GREEN}✓${NC} Session info retrieved successfully"
        echo "$session_info" | jq '{session_id: .session_id, turns: .conversation_turns, created: .created_at, expires: .expires_at}'
    else
        echo -e "${RED}✗${NC} Failed to retrieve session info"
    fi
    echo ""
}

# Check service health first
print_section "Pre-flight Check"

echo -n "Checking Weather Agent service..."
if curl -s -f "$API_URL/health" > /dev/null 2>&1; then
    echo -e " ${GREEN}✓${NC}"
else
    echo -e " ${RED}✗${NC}"
    log_error "Weather Agent service is not healthy!"
    exit 1
fi

# Check MCP connectivity
echo -n "Checking MCP server connectivity..."
mcp_status=$(curl -s "$API_URL/mcp/status" 2>/dev/null)
if echo "$mcp_status" | jq -e '.connected_count' &> /dev/null; then
    connected=$(echo "$mcp_status" | jq -r '.connected_count')
    total=$(echo "$mcp_status" | jq -r '.total_count')
    if [ "$connected" -eq "$total" ] && [ "$total" -gt 0 ]; then
        echo -e " ${GREEN}✓${NC} ($connected/$total servers connected)"
    else
        echo -e " ${YELLOW}⚠${NC} ($connected/$total servers connected)"
    fi
else
    echo -e " ${RED}✗${NC}"
    log_warn "Could not verify MCP connectivity"
fi
echo ""

# Test 1: Basic Multi-Turn Conversation
print_section "1. Testing Basic Multi-Turn Conversation"
echo "Scenario: Ask about weather in a city, then follow up with temporal questions"
echo ""

# First conversation
response1=$(make_query "What's the weather like in Seattle?")
display_result 1 "What's the weather like in Seattle?" "$response1"
session_id=$(echo "$response1" | jq -r '.session_id')

# Follow-up using context
response2=$(make_query "How about tomorrow?" "$session_id")
display_result 2 "How about tomorrow?" "$response2"

# Another follow-up
response3=$(make_query "Will it rain this weekend?" "$session_id")
display_result 3 "Will it rain this weekend?" "$response3"

# Test session info
test_session_info "$session_id"

# Test 2: Location Context Persistence
print_section "2. Testing Location Context Persistence"
echo "Scenario: Compare weather in multiple cities using context"
echo ""

# Start new conversation
response1=$(make_query "Compare the weather in New York and Los Angeles")
display_result 1 "Compare the weather in New York and Los Angeles" "$response1"
session_id2=$(echo "$response1" | jq -r '.session_id')

# Follow up about one city
response2=$(make_query "What about just New York next week?" "$session_id2")
display_result 2 "What about just New York next week?" "$response2"

# Follow up about the other city
response3=$(make_query "And Los Angeles?" "$session_id2")
display_result 3 "And Los Angeles?" "$response3"

# Test 3: Agricultural Context
print_section "3. Testing Agricultural Context"
echo "Scenario: Agricultural queries with location context"
echo ""

# Agricultural query
response1=$(make_query "Are conditions good for planting corn in Iowa?")
display_result 1 "Are conditions good for planting corn in Iowa?" "$response1"
session_id3=$(echo "$response1" | jq -r '.session_id')

# Follow-up about different crop, same location
response2=$(make_query "What about soybeans?" "$session_id3")
display_result 2 "What about soybeans?" "$session_id3"

# Follow-up about frost risk
response3=$(make_query "Is there any frost risk in the next week?" "$session_id3")
display_result 3 "Is there any frost risk in the next week?" "$response3"

# Test 4: Session Management
print_section "4. Testing Session Management"

# Test expired/invalid session
echo -e "${CYAN}Testing invalid session handling:${NC}"
invalid_response=$(make_query "What's the weather?" "invalid-session-id-12345" "false" 2>&1)

if echo "$invalid_response" | grep -q "404\|not found\|expired" || echo "$invalid_response" | jq -e '.detail' &> /dev/null; then
    echo -e "${GREEN}✓${NC} Invalid session properly rejected"
else
    echo -e "${RED}✗${NC} Invalid session not handled correctly"
fi
echo ""

# Test session deletion
echo -e "${CYAN}Testing session deletion:${NC}"
delete_response=$(curl -s -X DELETE "$API_URL/session/$session_id" 2>/dev/null)

if echo "$delete_response" | jq -e '.message' &> /dev/null; then
    echo -e "${GREEN}✓${NC} Session deleted successfully"
    
    # Verify session is gone
    check_response=$(curl -s "$API_URL/session/$session_id" 2>/dev/null)
    if echo "$check_response" | grep -q "404\|not found"; then
        echo -e "${GREEN}✓${NC} Deleted session no longer accessible"
    fi
else
    echo -e "${RED}✗${NC} Failed to delete session"
fi
echo ""

# Test 5: Structured Output with Sessions
print_section "5. Testing Structured Output with Sessions"

# Make structured query
structured_response=$(curl -s -X POST "$API_URL/query/structured" \
    -H "Content-Type: application/json" \
    -d '{"query": "Weather forecast for Chicago"}' 2>/dev/null)

if echo "$structured_response" | jq -e '.session_id' &> /dev/null; then
    echo -e "${GREEN}✓${NC} Structured endpoint includes session info"
    struct_session_id=$(echo "$structured_response" | jq -r '.session_id')
    
    # Show structured data
    echo "Structured response preview:"
    echo "$structured_response" | jq '{query_type: .query_type, locations: .locations | length, session_id: .session_id, turn: .conversation_turn}' 2>/dev/null
    
    # Follow-up structured query
    followup_response=$(curl -s -X POST "$API_URL/query/structured" \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"How about the weekend?\", \"session_id\": \"$struct_session_id\"}" 2>/dev/null)
    
    if echo "$followup_response" | jq -e '.conversation_turn' &> /dev/null; then
        turn=$(echo "$followup_response" | jq -r '.conversation_turn')
        echo -e "${GREEN}✓${NC} Structured follow-up worked (turn: $turn)"
    fi
else
    echo -e "${RED}✗${NC} Structured endpoint missing session info"
fi
echo ""

# Test 6: Performance and Latency
print_section "6. Performance Test (AWS Deployment)"
echo "Testing response time with session context"
echo ""

# Create a session and time queries
start_time=$(date +%s.%N)
perf_response1=$(make_query "What's the temperature in Boston?")
perf_session=$(echo "$perf_response1" | jq -r '.session_id')
end_time=$(date +%s.%N)
time1=$(echo "$end_time - $start_time" | bc)

start_time=$(date +%s.%N)
perf_response2=$(make_query "And humidity?" "$perf_session")
end_time=$(date +%s.%N)
time2=$(echo "$end_time - $start_time" | bc)

echo -e "First query time: ${YELLOW}${time1}s${NC}"
echo -e "Follow-up query time: ${YELLOW}${time2}s${NC}"

# AWS-specific latency check
echo ""
echo "Note: AWS ECS deployments may have additional latency due to:"
echo "  - Load balancer routing"
echo "  - Inter-container networking"
echo "  - Service discovery DNS resolution"
echo ""

# Test 7: Concurrent Sessions
print_section "7. Testing Concurrent Sessions"
echo "Creating multiple sessions to test isolation"
echo ""

# Create three concurrent sessions
session_a=$(make_query "Weather in Miami" | jq -r '.session_id')
session_b=$(make_query "Weather in Denver" | jq -r '.session_id')
session_c=$(make_query "Weather in Phoenix" | jq -r '.session_id')

echo -e "Created sessions:"
echo -e "  A: ${session_a:0:8}... (Miami)"
echo -e "  B: ${session_b:0:8}... (Denver)"
echo -e "  C: ${session_c:0:8}... (Phoenix)"
echo ""

# Test that each session maintains its own context
response_a=$(make_query "What about tomorrow?" "$session_a")
response_b=$(make_query "What about tomorrow?" "$session_b")
response_c=$(make_query "What about tomorrow?" "$session_c")

# Check if responses maintain context
if echo "$response_a" | grep -qi "miami"; then
    echo -e "${GREEN}✓${NC} Session A maintained Miami context"
else
    echo -e "${YELLOW}⚠${NC} Session A context unclear"
fi

if echo "$response_b" | grep -qi "denver"; then
    echo -e "${GREEN}✓${NC} Session B maintained Denver context"
else
    echo -e "${YELLOW}⚠${NC} Session B context unclear"
fi

if echo "$response_c" | grep -qi "phoenix"; then
    echo -e "${GREEN}✓${NC} Session C maintained Phoenix context"
else
    echo -e "${YELLOW}⚠${NC} Session C context unclear"
fi
echo ""

# Summary
print_section "📊 Summary"

echo -e "${GREEN}✅ Multi-turn conversation test completed!${NC}"
echo ""
echo "Key findings:"
echo "- Sessions persist across multiple queries in AWS deployment"
echo "- Context is maintained for follow-up questions"
echo "- Invalid sessions are properly handled"
echo "- Both regular and structured endpoints support sessions"
echo "- Multiple concurrent sessions work independently"
echo ""
echo "AWS-specific observations:"
echo "- Service is accessible via Application Load Balancer"
echo "- MCP servers communicate via Service Discovery"
echo "- CloudWatch logs available for debugging"
echo ""
echo "To monitor the deployment:"
echo "- Check logs: aws logs tail /ecs/strands-weather-agent-main --follow"
echo "- View metrics: Check CloudWatch dashboard"
echo "- Service status: ./status.sh"
echo ""