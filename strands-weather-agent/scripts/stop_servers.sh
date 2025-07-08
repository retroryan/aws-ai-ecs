#!/bin/bash

# FastMCP Server Shutdown Script
# This script stops all running FastMCP servers
# Usage: ./stop_servers.sh [--force]

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
            echo "  --force  Immediately kill all processes on MCP ports without checking PID files"
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

# Force mode: kill all processes on MCP ports
if [ "$FORCE_MODE" = true ]; then
    echo -e "${RED}Force stopping all processes on MCP ports...${NC}"
    echo ""
    
    # Kill processes on each port
    for port in 7778 7779 7780; do
        if lsof -t -i :$port > /dev/null 2>&1; then
            echo -e "Killing processes on port $port..."
            lsof -t -i :$port | xargs kill -9 2>/dev/null
            echo -e "${GREEN}✅ Port $port cleared${NC}"
        else
            echo -e "${YELLOW}⚠️  No process found on port $port${NC}"
        fi
    done
    
    # Clean up PID files
    rm -f "$PROJECT_ROOT"/logs/*.pid 2>/dev/null
    
    echo ""
    echo -e "${GREEN}Force stop completed.${NC}"
    exit 0
fi

# Normal mode
echo -e "${YELLOW}Stopping FastMCP servers...${NC}"
echo ""

# Function to stop a server
stop_server() {
    local name=$1
    local pid_file="$PROJECT_ROOT/logs/${name}.pid"
    
    if [ ! -f "$pid_file" ]; then
        echo -e "${YELLOW}⚠️  ${name} server is not running (no PID file found)${NC}"
        return
    fi
    
    local pid=$(cat "$pid_file")
    
    # Check if process exists
    if ps -p $pid > /dev/null 2>&1; then
        echo -e "Stopping ${name} server (PID: $pid)..."
        kill $pid 2>/dev/null
        
        # Wait for process to terminate
        local count=0
        while ps -p $pid > /dev/null 2>&1 && [ $count -lt 10 ]; do
            sleep 0.5
            count=$((count + 1))
        done
        
        # Force kill if still running
        if ps -p $pid > /dev/null 2>&1; then
            echo -e "${YELLOW}Force stopping ${name} server...${NC}"
            kill -9 $pid 2>/dev/null
        fi
        
        echo -e "${GREEN}✅ ${name} server stopped${NC}"
    else
        echo -e "${YELLOW}⚠️  ${name} server was not running (PID: $pid not found)${NC}"
    fi
    
    # Remove PID file
    rm -f "$pid_file"
}

# Check if logs directory exists
if [ ! -d "$PROJECT_ROOT/logs" ]; then
    echo -e "${YELLOW}No logs directory found. No servers to stop.${NC}"
    exit 0
fi

# Stop all servers
stop_server "forecast"
stop_server "historical"
stop_server "agricultural"

echo ""
echo -e "${GREEN}All servers have been stopped.${NC}"

# Optional: Clean up old log files
echo ""
read -p "Do you want to remove log files? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f "$PROJECT_ROOT"/logs/*.log
    echo -e "${GREEN}Log files removed.${NC}"
fi