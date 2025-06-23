#!/bin/bash

# Force stop all MCP servers by killing processes on their ports
lsof -t -i :7071 | xargs kill -9 2>/dev/null
lsof -t -i :7072 | xargs kill -9 2>/dev/null
lsof -t -i :7073 | xargs kill -9 2>/dev/null

echo "All MCP servers forcefully stopped"