#!/bin/bash

# Test Runner Script for AWS Strands Weather Agent
# This script starts MCP servers, runs tests, then stops servers

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

echo -e "${GREEN}🧪 AWS Strands Weather Agent Test Runner${NC}"
echo "========================================"
echo ""

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    "$SCRIPT_DIR/stop_servers.sh"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Step 1: Check if servers are already running
echo -e "${YELLOW}Checking for existing servers...${NC}"
if [ -f "$PROJECT_ROOT/logs/forecast.pid" ] || [ -f "$PROJECT_ROOT/logs/historical.pid" ] || [ -f "$PROJECT_ROOT/logs/agricultural.pid" ]; then
    echo -e "${YELLOW}Found existing server processes. Stopping them...${NC}"
    "$SCRIPT_DIR/stop_servers.sh"
    sleep 2
fi

# Step 2: Start MCP servers
echo -e "\n${GREEN}Starting MCP servers...${NC}"
"$SCRIPT_DIR/start_servers.sh"

# Wait for servers to be ready
echo -e "\n${YELLOW}Waiting for servers to be ready...${NC}"
sleep 5

# Test server health
echo -e "\n${YELLOW}Testing server health...${NC}"
for port in 7778 7779 7780; do
    if curl -s -f "http://localhost:$port/health" > /dev/null; then
        echo -e "${GREEN}✅ Server on port $port is healthy${NC}"
    else
        echo -e "${RED}❌ Server on port $port is not responding${NC}"
    fi
done

# Step 3: Run tests from weather_agent directory
echo -e "\n${GREEN}Running tests...${NC}"
cd "$PROJECT_ROOT/weather_agent"

# Check Python version
if command -v pyenv &> /dev/null; then
    echo -e "${YELLOW}Setting Python version with pyenv...${NC}"
    pyenv local 3.12.10
fi

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo -e "${YELLOW}No virtual environment found. Creating one...${NC}"
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    # Activate existing virtual environment
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    elif [ -d "venv" ]; then
        source venv/bin/activate
    fi
fi

# Install/update requirements
echo -e "${YELLOW}Installing/updating requirements...${NC}"
pip install -q -r requirements.txt

# Set required environment variables if not already set
if [ -z "$BEDROCK_MODEL_ID" ]; then
    export BEDROCK_MODEL_ID="us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    echo -e "${YELLOW}Using default BEDROCK_MODEL_ID: $BEDROCK_MODEL_ID${NC}"
fi

if [ -z "$BEDROCK_REGION" ]; then
    export BEDROCK_REGION="us-east-1"
    echo -e "${YELLOW}Using default BEDROCK_REGION: $BEDROCK_REGION${NC}"
fi

# Run the test suite
echo -e "\n${GREEN}Executing test suite...${NC}"
echo "----------------------------------------"
# Run the comprehensive test script from tests directory
cd "$PROJECT_ROOT"
python tests/test_mcp_agent_strands.py

# Capture test exit code
TEST_EXIT_CODE=$?

# Step 4: Run demo if tests passed
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}Tests passed! Running demo...${NC}"
    echo "----------------------------------------"
    
    # Run a quick demo
    echo -e "${YELLOW}Running structured output demo...${NC}"
    python examples/structured_output_demo.py
    
    echo -e "\n${GREEN}✅ All tests and demos completed successfully!${NC}"
else
    echo -e "\n${RED}❌ Tests failed! Check the output above for details.${NC}"
fi

# Return the test exit code
exit $TEST_EXIT_CODE