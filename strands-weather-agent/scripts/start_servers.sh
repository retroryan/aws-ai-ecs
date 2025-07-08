#!/bin/bash

# FastMCP Server Startup Script
# This script starts all FastMCP servers in the background with logging

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_ROOT/logs"

echo -e "${GREEN}Starting FastMCP servers...${NC}"
echo ""

# Function to start a server
start_server() {
    local name=$1
    local script=$2
    local port=$3
    local pid_file="$PROJECT_ROOT/logs/${name}.pid"
    local log_file="$PROJECT_ROOT/logs/${name}.log"
    
    # Check if server is already running
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  ${name} server is already running (PID: $pid)${NC}"
            return
        fi
    fi
    
    # Start the server
    echo -e "Starting ${name} server on port ${port}..."
    (cd "$PROJECT_ROOT" && python $script > "$log_file" 2>&1) &
    local pid=$!
    
    # Save PID
    echo $pid > "$pid_file"
    
    # Wait a moment to check if it started successfully
    sleep 2
    
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "${GREEN}✅ ${name} server started successfully (PID: $pid)${NC}"
    else
        echo -e "${RED}❌ Failed to start ${name} server. Check ${log_file} for details.${NC}"
        rm -f "$pid_file"
    fi
}

# Start all servers
start_server "forecast" "mcp_servers/forecast_server.py" "7778"
start_server "historical" "mcp_servers/historical_server.py" "7779" 
start_server "agricultural" "mcp_servers/agricultural_server.py" "7780"

echo ""
echo -e "${GREEN}All servers have been started.${NC}"
echo ""
echo "Server endpoints:"
echo "  - Forecast:     http://127.0.0.1:7778/mcp"
echo "  - Historical:   http://127.0.0.1:7779/mcp"
echo "  - Agricultural: http://127.0.0.1:7780/mcp"
echo ""
echo "Logs are available in the logs/ directory:"
echo "  - logs/forecast.log"
echo "  - logs/historical.log"
echo "  - logs/agricultural.log"
echo ""
echo "To stop all servers, run: ./scripts/stop_servers.sh"