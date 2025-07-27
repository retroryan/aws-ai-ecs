#!/bin/bash

# FastMCP Server Shutdown Script
# This script stops the running weather MCP server
# Usage: ./stop_server.sh [--force]

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Parse command line arguments
FORCE_MODE=false
for arg in "$@"; do
    case $arg in
        --force)
            FORCE_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--force]"
            echo "  --force  Immediately kill all processes on MCP port without checking PID file"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Force mode: kill all processes on MCP port
if [ "$FORCE_MODE" = true ]; then
    echo -e "${RED}Force stopping all processes on MCP port...${NC}"
    echo ""
    
    # Kill processes on port 7778
    if lsof -t -i :7778 > /dev/null 2>&1; then
        echo -e "Killing processes on port 7778..."
        lsof -t -i :7778 | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✅ Port 7778 cleared${NC}"
    else
        echo -e "${YELLOW}⚠️  No process found on port 7778${NC}"
    fi
    
    # Clean up PID file
    rm -f "$PROJECT_ROOT"/logs/weather.pid 2>/dev/null
    
    echo ""
    echo -e "${GREEN}Force stop completed.${NC}"
    exit 0
fi

# Normal mode
echo -e "${YELLOW}Stopping weather MCP server...${NC}"
echo ""

# Function to stop the server
stop_server() {
    local name="weather"
    local pid_file="$PROJECT_ROOT/logs/${name}.pid"
    
    if [ ! -f "$pid_file" ]; then
        echo -e "${YELLOW}⚠️  Weather server is not running (no PID file found)${NC}"
        return
    fi
    
    local pid=$(cat "$pid_file")
    
    # Check if process exists
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "Stopping weather server (PID: $pid)..."
        kill $pid 2>/dev/null
        
        # Wait for process to terminate
        local count=0
        while ps -p $pid > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 0.5
            count=$((count + 1))
        done
        
        # Force kill if still running
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Force stopping weather server...${NC}"
            kill -9 $pid 2>/dev/null
        fi
        
        echo -e "${GREEN}✅ Weather server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  Weather server was not running (PID: $pid not found)${NC}"
    fi
    
    # Remove PID file
    rm -f "$pid_file"
}

# Check if logs directory exists
if [ ! -d "$PROJECT_ROOT/logs" ]; then
    echo -e "${YELLOW}No logs directory found. No server to stop.${NC}"
    exit 0
fi

# Stop the server
stop_server

echo ""
echo -e "${GREEN}Server has been stopped.${NC}"

# Optional: Clean up old log files
echo ""
read -p "Do you want to remove log files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f "$PROJECT_ROOT"/logs/weather.log
    echo -e "${GREEN}Log file removed.${NC}"
fi