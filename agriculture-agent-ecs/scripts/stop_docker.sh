#!/bin/bash

# Stop script for Docker Compose services
set -e

echo "Stopping Agriculture Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Set empty AWS variables to suppress warnings when stopping
# (These aren't needed for stopping containers)
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
export AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN:-}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

# Stop services
docker-compose down

echo "Services stopped!"