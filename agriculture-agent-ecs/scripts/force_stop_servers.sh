#!/bin/bash

# Force stop the unified MCP server by killing process on its port
lsof -t -i :7071 | xargs kill -9 2>/dev/null

echo "MCP server forcefully stopped"