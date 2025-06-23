#!/bin/bash

# Rebuild containers from scratch

echo "Rebuilding containers..."

# Export AWS credentials
export $(aws configure export-credentials --format env-no-export)

# Stop and remove existing containers
docker-compose down

# Build containers without cache
docker-compose build --no-cache

# Start containers
docker-compose up -d

echo "✅ Containers rebuilt and started"
echo ""
echo "Run ./scripts/test-quick.sh to verify services are working"