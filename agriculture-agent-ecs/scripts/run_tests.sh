#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Running Agriculture Agent Test Suite"
echo "======================================="

# Navigate to project root
cd "$(dirname "$0")/.."

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

# Check if required modules are installed
echo "Checking Python environment..."
python -c "import asyncio, httpx" 2>/dev/null || {
    echo -e "${YELLOW}⚠️  Missing required Python packages${NC}"
    echo "Please install requirements: pip install -r requirements.txt"
    exit 1
}

# Check if AWS credentials are available
if ! aws sts get-caller-identity &> /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  AWS credentials not configured${NC}"
    echo "Some tests may fail. Run ./scripts/aws-setup.sh to configure."
fi

# Check if BEDROCK_MODEL_ID is set
if [ -z "$BEDROCK_MODEL_ID" ]; then
    echo -e "${YELLOW}⚠️  BEDROCK_MODEL_ID not set${NC}"
    echo "Loading from .env file if available..."
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi
fi

# Start MCP servers if not already running
echo -e "\n${GREEN}Starting MCP servers...${NC}"
./scripts/start_servers.sh

# Give servers time to initialize
sleep 2

# Run the test suite
echo -e "\n${GREEN}Running tests...${NC}"
echo "======================================="

# Run main test suite
python tests/run_all_tests.py "$@"
TEST_EXIT_CODE=$?

# Stop MCP servers
echo -e "\n${GREEN}Stopping MCP servers...${NC}"
./scripts/stop_servers.sh

# Report results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${RED}❌ Some tests failed${NC}"
fi

exit $TEST_EXIT_CODE