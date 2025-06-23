#!/bin/bash

# Start Docker Compose with AWS credentials
# This replaces the start-with-aws.sh script

echo "Starting Docker Compose with AWS credentials..."

# Export AWS credentials to environment variables
export $(aws configure export-credentials --format env-no-export)

# Start Docker Compose
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check health
echo ""
echo "Checking service health..."
curl -s http://localhost:8081/health | jq
curl -s http://localhost:8080/health | jq

echo ""
echo "Services are ready! You can now:"
echo "  - Run ./scripts/test.sh to test all endpoints"
echo "  - Run ./scripts/test-quick.sh for a quick health check"
echo "  - Access the client at http://localhost:8080"
echo "  - Access the server directly at http://localhost:8081"