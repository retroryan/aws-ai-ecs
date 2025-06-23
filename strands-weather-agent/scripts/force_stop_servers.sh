#!/bin/bash

# Kill processes on MCP server ports
lsof -t -i :8081 | xargs kill -9 2>/dev/null
lsof -t -i :8082 | xargs kill -9 2>/dev/null
lsof -t -i :8083 | xargs kill -9 2>/dev/null