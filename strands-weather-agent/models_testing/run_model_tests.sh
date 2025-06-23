#!/bin/bash

# Run Model Compliance Tests
# This script tests AWS Bedrock models for structured output compliance

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}AWS Bedrock Model Compliance Testing${NC}"
echo "======================================"

# Get the script directory and parent directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Check if we're in the right place
if [ ! -f "$PARENT_DIR/weather_agent/mcp_agent.py" ]; then
    echo -e "${RED}Error: Cannot find weather_agent directory${NC}"
    exit 1
fi

# Change to parent directory
cd "$PARENT_DIR"

# Set Python environment
echo -e "${YELLOW}Setting Python environment...${NC}"
cd weather_agent
pyenv local 3.12.10
cd ..

# Check if MCP servers are running
echo -e "${YELLOW}Checking MCP servers...${NC}"
if ! lsof -i:8081 > /dev/null 2>&1; then
    echo -e "${RED}MCP servers not running. Starting them...${NC}"
    ./scripts/start_servers.sh
    sleep 5
fi

# Create results directory
mkdir -p "$SCRIPT_DIR/test_results"

# Parse command line arguments
QUICK_MODE=""
SPECIFIC_MODELS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            QUICK_MODE="--quick"
            echo -e "${YELLOW}Running in quick mode (testing key models only)${NC}"
            shift
            ;;
        --models)
            shift
            SPECIFIC_MODELS="--models $@"
            echo -e "${YELLOW}Testing specific models: $@${NC}"
            break
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --quick        Test only key models (Claude 3.7, Nova Premier, Llama 3.3, Cohere R+)"
            echo "  --models ...   Test specific model IDs"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Run the tests
echo -e "${GREEN}Starting model compliance tests...${NC}"
echo "Results will be saved to: $SCRIPT_DIR/test_results/"
echo ""

# Set PYTHONPATH to ensure imports work
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

# Run the test script from the models_testing directory
cd "$SCRIPT_DIR"
if [ -n "$SPECIFIC_MODELS" ]; then
    python test_model_compliance.py $SPECIFIC_MODELS --output test_results
elif [ -n "$QUICK_MODE" ]; then
    python test_model_compliance.py --quick --output test_results
else
    echo -e "${YELLOW}Testing all models. This may take 20-30 minutes...${NC}"
    python test_model_compliance.py --output test_results
fi

# Check if tests completed
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Model compliance testing completed successfully!${NC}"
    echo ""
    echo "Results saved to:"
    ls -la "$SCRIPT_DIR"/test_results/model_compliance_report_*.md | tail -1
    ls -la "$SCRIPT_DIR"/test_results/model_compliance_results_*.json | tail -1
else
    echo ""
    echo -e "${RED}❌ Model compliance testing failed${NC}"
    exit 1
fi