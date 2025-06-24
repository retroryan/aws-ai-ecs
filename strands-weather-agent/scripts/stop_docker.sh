#!/bin/bash

# Stop script for Docker Compose services
set -e

echo "Stopping Strands Weather Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Export empty AWS variables to suppress warnings during shutdown
# These aren't needed for stopping services
export AWS_ACCESS_KEY_ID=""
export AWS_SECRET_ACCESS_KEY=""
export AWS_SESSION_TOKEN=""

# Stop services
docker compose down

echo "Services stopped!"