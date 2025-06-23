#!/bin/bash

# Clean up Docker resources and Python cache files

echo "Cleaning up Docker resources..."
docker-compose down -v

echo "Removing Python cache files..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Cleanup complete"