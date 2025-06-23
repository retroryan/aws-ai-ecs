#!/bin/bash

# Stop script for Docker Compose services
set -e

echo "Stopping AWS Strands Weather Agent services..."

# Navigate to project root
cd "$(dirname "$0")/.."

# Stop services
docker compose down

echo "Services stopped!"