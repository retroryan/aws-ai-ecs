#!/bin/bash

# Kill processes on MCP server ports
lsof -t -i :7778 | xargs kill -9 2>/dev/null
lsof -t -i :7779 | xargs kill -9 2>/dev/null
lsof -t -i :7780 | xargs kill -9 2>/dev/null

echo "✓ Finished stopping servers"