#!/bin/bash

# MCP Spring Agriculture Experts Docker Run Script
# This script builds and runs the MCP server locally for demo purposes

# Check if existing container is running
if [ "$(docker ps -aq -f name=spring-agriculture-experts)" ]; then
    echo "Stopping and removing existing spring-agriculture-experts container..."
    docker stop spring-agriculture-experts >/dev/null 2>&1
    docker rm spring-agriculture-experts >/dev/null 2>&1
fi

echo "Building MCP Spring Agriculture Experts Docker image..."
echo "======================================="

# Build the Docker image (from project root)
docker build -t spring-agriculture-experts:dev -f server/Dockerfile .

echo ""
echo "Starting MCP MCP Spring Agriculture Experts container..."
echo "======================================="

# Run the container
docker run -d --name spring-agriculture-experts -p 8010:8010 spring-agriculture-experts:dev

echo ""
echo "MCP MCP Spring Agriculture Experts is starting on port 8010..."
echo "======================================="
echo ""
echo "Useful commands:"
echo "  View logs:        docker logs -f spring-agriculture-experts"
echo "  Check status:     docker ps | grep spring-agriculture-experts"
echo "  Stop container:   docker stop spring-agriculture-experts"
echo "  Remove container: docker rm spring-agriculture-experts"
echo ""
echo "Health check:     curl http://localhost:8010/actuator/health"
echo ""