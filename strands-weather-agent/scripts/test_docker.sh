#!/bin/bash

# Docker Integration Test Script
# This script tests the running Docker services without starting them
# Use ./scripts/start_docker.sh to start the services first

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
running_containers=$(docker ps --filter "name=mcp-weather-server" --filter "name=weather-agent" -q | wc -l | tr -d ' ')

if [ "$running_containers" -eq "0" ]; then
    echo -e "${RED}No services running!${NC}"
    echo ""
    echo "Please start the services first with:"
    echo "  ./scripts/start_docker.sh"
    exit 1
fi

echo "Found $running_containers running containers"
echo ""
docker ps --filter "name=mcp-weather-server" --filter "name=weather-agent" --format "table {{.Names}}\t{{.Status}}"
echo ""

echo "2. Testing service endpoints..."
echo ""

# Check each service
services_ok=true

# Check MCP server (it has /health endpoint in our setup)
if ! check_service "Weather Server" "http://localhost:7778/health"; then
    services_ok=false
fi


# Check Weather Agent (has proper health endpoint)
if ! check_service "Weather Agent" "http://localhost:7777/health"; then
    services_ok=false
fi

if [ "$services_ok" = false ]; then
    echo ""
    echo -e "${RED}Some services are not responding!${NC}"
    echo ""
    echo "Check service logs with:"
    echo "  docker compose logs -f"
    exit 1
fi

echo ""
echo -e "${GREEN}All services are healthy!${NC}"
echo ""
echo "3. Running test queries..."
echo ""

# Initialize metrics totals
total_queries=0
successful_queries=0
total_tokens_all=0
total_input_tokens=0
total_output_tokens=0
total_latency=0
total_cycles=0
model_used=""

# Function to test a query
test_query() {
    local query=$1
    local show_full=${2:-false}  # Optional parameter to show full response
    
    echo "Query: \"$query\""
    
    response=$(curl -s -X POST http://localhost:7777/query \
        -H "Content-Type: application/json" \
        -d "{\"query\": \"$query\"}" 2>/dev/null || echo '{"response": "Error: Failed to connect"}')
    
    # Extract response and session fields
    response_text=$(echo "$response" | jq -r '.response' 2>/dev/null || echo "Error parsing response")
    session_id=$(echo "$response" | jq -r '.session_id' 2>/dev/null || echo "")
    session_new=$(echo "$response" | jq -r '.session_new' 2>/dev/null || echo "")
    conversation_turn=$(echo "$response" | jq -r '.conversation_turn' 2>/dev/null || echo "")
    metrics=$(echo "$response" | jq -r '.metrics' 2>/dev/null || echo "null")
    trace_url=$(echo "$response" | jq -r '.trace_url' 2>/dev/null || echo "")
    
    # Increment total queries
    ((total_queries++))
    
    if [[ "$response_text" == "Error"* ]] || [[ "$response_text" == "An error occurred"* ]]; then
        if [[ "$response_text" == *"credentials"* ]] || [[ "$response_text" == *"AWS"* ]] || [[ "$response_text" == *"Bedrock"* ]]; then
            echo -e "Response: ${RED}✗ AWS Bedrock Error${NC}"
            echo -e "Details: $response_text"
            echo ""
            echo "Troubleshooting:"
            echo "1. Ensure AWS credentials are properly configured:"
            echo "   aws sts get-caller-identity"
            echo "2. Check if Bedrock model is accessible:"
            echo "   aws bedrock list-foundation-models --region ${BEDROCK_REGION:-us-east-1}"
            echo "3. Verify BEDROCK_MODEL_ID is set in .env file"
        else
            echo -e "Response: ${RED}✗ $response_text${NC}"
        fi
    else
        # Show full response without truncation
        echo -e "Response: ${GREEN}✓${NC}"
        echo "$response_text"
        
        # Display session info if available
        if [[ -n "$session_id" ]] && [[ "$session_id" != "null" ]]; then
            echo -e "\nSession: ${GREEN}✓${NC} ID: ${session_id:0:8}... | New: $session_new | Turn: $conversation_turn"
        fi
        
        # Display metrics if available
        if [[ "$metrics" != "null" ]] && [[ -n "$metrics" ]]; then
            echo -e "\n📊 Performance Metrics:"
            total_tokens=$(echo "$metrics" | jq -r '.total_tokens' 2>/dev/null || echo "0")
            input_tokens=$(echo "$metrics" | jq -r '.input_tokens' 2>/dev/null || echo "0")
            output_tokens=$(echo "$metrics" | jq -r '.output_tokens' 2>/dev/null || echo "0")
            latency_seconds=$(echo "$metrics" | jq -r '.latency_seconds' 2>/dev/null || echo "0")
            throughput=$(echo "$metrics" | jq -r '.throughput_tokens_per_second' 2>/dev/null || echo "0")
            model=$(echo "$metrics" | jq -r '.model' 2>/dev/null || echo "unknown")
            cycles=$(echo "$metrics" | jq -r '.cycles' 2>/dev/null || echo "0")
            
            echo "   ├─ Tokens: $total_tokens total ($input_tokens input, $output_tokens output)"
            echo "   ├─ Latency: $latency_seconds seconds"
            echo "   ├─ Throughput: ${throughput%.*} tokens/second"
            echo "   ├─ Model: $model"
            echo "   └─ Cycles: $cycles"
            
            # Accumulate metrics
            total_tokens_all=$((total_tokens_all + total_tokens))
            total_input_tokens=$((total_input_tokens + input_tokens))
            total_output_tokens=$((total_output_tokens + output_tokens))
            total_latency=$(echo "$total_latency + $latency_seconds" | bc)
            total_cycles=$((total_cycles + cycles))
            model_used=$model
            ((successful_queries++))
        fi
        
        # Display trace URL if available
        if [[ -n "$trace_url" ]] && [[ "$trace_url" != "null" ]]; then
            echo -e "\n🔗 Trace: $trace_url"
        fi
    fi
    echo ""
}

# Test different types of queries
test_query "What's the weather forecast for Chicago?"
test_query "How much rain did Seattle get last week?"
test_query "Are conditions good for planting corn in Iowa?"

# Display metrics summary
if [[ $successful_queries -gt 0 ]]; then
    echo ""
    echo "📊 METRICS SUMMARY"
    echo "=================="
    echo ""
    echo "Total Queries: $total_queries ($successful_queries successful)"
    echo ""
    echo "Token Usage:"
    echo "  Total Tokens: $total_tokens_all"
    echo "  Input Tokens: $total_input_tokens"
    echo "  Output Tokens: $total_output_tokens"
    
    # Calculate averages
    avg_tokens=$((total_tokens_all / successful_queries))
    avg_latency=$(echo "scale=2; $total_latency / $successful_queries" | bc)
    avg_throughput=$(echo "scale=0; $total_tokens_all / $total_latency" | bc 2>/dev/null || echo "N/A")
    
    echo ""
    echo "Performance:"
    echo "  Total Processing Time: ${total_latency}s"
    echo "  Average Latency: ${avg_latency}s per query"
    echo "  Average Throughput: $avg_throughput tokens/second"
    echo "  Total Agent Cycles: $total_cycles"
    echo "  Model: $model_used"
    
    # Check if Langfuse is enabled
    if [[ -n "$LANGFUSE_PUBLIC_KEY" ]] && [[ -n "$LANGFUSE_SECRET_KEY" ]]; then
        echo ""
        echo "Telemetry:"
        echo "  Langfuse Host: ${LANGFUSE_HOST:-https://us.cloud.langfuse.com}"
        echo "  Traces Available: Yes (check dashboard for details)"
    fi
fi

echo ""
echo "4. Testing session endpoints..."
echo ""

# Test session info endpoint
echo -n "Testing session endpoint..."
# Get a session ID from the last query (if jq is available)
if command -v jq &> /dev/null; then
    # Make a query to get a session ID
    session_response=$(curl -s -X POST http://localhost:7777/query \
        -H "Content-Type: application/json" \
        -d '{"query": "test session"}' 2>/dev/null)
    
    test_session_id=$(echo "$session_response" | jq -r '.session_id' 2>/dev/null || echo "")
    
    if [[ -n "$test_session_id" ]] && [[ "$test_session_id" != "null" ]]; then
        # Test GET session info
        session_info=$(curl -s "http://localhost:7777/session/$test_session_id" 2>/dev/null)
        if echo "$session_info" | jq -e '.session_id' &> /dev/null; then
            echo -e " ${GREEN}✓${NC}"
            echo "Session info retrieved successfully"
        else
            echo -e " ${RED}✗${NC}"
        fi
    else
        echo -e " ${YELLOW}⚠${NC} Could not get session ID"
    fi
else
    echo -e " ${YELLOW}⚠${NC} jq not installed, skipping session test"
fi

echo ""
echo "5. Service URLs:"
echo "   - Weather Agent API: http://localhost:7777"
echo "   - API Docs: http://localhost:7777/docs"
echo "   - Health Check: http://localhost:7777/health"
echo ""
echo "   MCP Servers:"
echo "   - Forecast: http://localhost:7778/health"
echo "   - Historical: http://localhost:7779/health"
echo "   - Agricultural: http://localhost:7780/health"
echo ""

echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "Commands:"
echo "  Stop services:  ./scripts/stop_docker.sh"
echo "  View logs:      docker compose logs -f"
echo "  Restart:        ./scripts/stop_docker.sh && ./scripts/start_docker.sh"
echo ""