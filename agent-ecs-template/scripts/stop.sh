#!/bin/bash

# Stop Docker Compose services
echo "Stopping Docker Compose services..."

# Stop and remove containers
docker-compose down

# Check if containers are stopped
if [ $? -eq 0 ]; then
    echo "✅ Services stopped successfully"
else
    echo "❌ Error stopping services"
    exit 1
fi

# Optional: Remove volumes (uncomment if needed)
# echo "Removing volumes..."
# docker-compose down -v

echo ""
echo "All services have been stopped."