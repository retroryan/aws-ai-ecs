#!/bin/bash

# Script to run prompt variation tests
echo "🧪 Running System Prompt Variation Tests"
echo "========================================"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to parent directory
cd "$PARENT_DIR"

# Set Python environment
cd weather_agent
pyenv local 3.12.10
cd ..

# Set PYTHONPATH to ensure imports work
export PYTHONPATH="${PARENT_DIR}:${PYTHONPATH}"

# Check if MCP servers are running
echo "Checking MCP servers..."
if ! pgrep -f "forecast_server.py" > /dev/null; then
    echo "⚠️  MCP servers are not running!"
    echo "Please run: ./scripts/start_servers.sh"
    exit 1
fi

echo "✅ MCP servers are running"
echo ""

# Run the prompt tests
echo "Running prompt variation tests..."
python models_testing/test_prompt_variations.py

echo ""
echo "✅ Prompt testing complete!"