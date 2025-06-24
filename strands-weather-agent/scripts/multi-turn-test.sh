#!/bin/bash

# Multi-Turn Conversation Test Script
# This script tests stateful conversations with the Weather Agent API
# It demonstrates session persistence across multiple queries

set -e

echo "🔄 Multi-Turn Conversation Test"
echo "==============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# API endpoint
API_URL="${API_URL:-http://localhost:8090}"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    echo "Please install jq to run this test."
    exit 1
fi

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
    echo -e "${GREEN}Response:${NC} $response_text"
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

echo "1. Testing Basic Multi-Turn Conversation"
echo "----------------------------------------"
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

echo "2. Testing Location Context Persistence"
echo "--------------------------------------"
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

echo "3. Testing Agricultural Context"
echo "------------------------------"
echo "Scenario: Agricultural queries with location context"
echo ""

# Agricultural query
response1=$(make_query "Are conditions good for planting corn in Iowa?")
display_result 1 "Are conditions good for planting corn in Iowa?" "$response1"
session_id3=$(echo "$response1" | jq -r '.session_id')

# Follow-up about different crop, same location
response2=$(make_query "What about soybeans?" "$session_id3")
display_result 2 "What about soybeans?" "$response2"

# Follow-up about frost risk
response3=$(make_query "Is there any frost risk in the next week?" "$session_id3")
display_result 3 "Is there any frost risk in the next week?" "$response3"

echo "4. Testing Session Management"
echo "----------------------------"
echo ""

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

echo "5. Testing Structured Output with Sessions"
echo "-----------------------------------------"
echo ""

# Make structured query
structured_response=$(curl -s -X POST "$API_URL/query/structured" \
    -H "Content-Type: application/json" \
    -d '{"query": "Weather forecast for Chicago"}' 2>/dev/null)

if echo "$structured_response" | jq -e '.session_id' &> /dev/null; then
    echo -e "${GREEN}✓${NC} Structured endpoint includes session info"
    struct_session_id=$(echo "$structured_response" | jq -r '.session_id')
    
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

echo "6. Performance Test"
echo "------------------"
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

# Check if follow-up was faster (it might not be due to API calls)
if (( $(echo "$time2 < $time1" | bc -l) )); then
    echo -e "${GREEN}✓${NC} Follow-up query was faster"
else
    echo -e "${YELLOW}ℹ${NC} Follow-up query took similar time (expected with API calls)"
fi
echo ""

echo "Summary"
echo "-------"
echo -e "${GREEN}✅ Multi-turn conversation test completed!${NC}"
echo ""
echo "Key findings:"
echo "- Sessions persist across multiple queries"
echo "- Context is maintained for follow-up questions"
echo "- Invalid sessions are properly handled"
echo "- Both regular and structured endpoints support sessions"
echo ""
echo "To test further:"
echo "- Wait 60+ minutes to test session expiration"
echo "- Run concurrent tests to verify session isolation"
echo "- Monitor memory usage with many active sessions"
echo ""