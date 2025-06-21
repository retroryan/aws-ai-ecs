# Python ECS Template

## Overview
This is a simple Python Flask application demonstrating a client-server architecture designed to run on AWS ECS behind an Application Load Balancer. This template has been migrated from Spring Boot/Kotlin to Python for simplicity and reduced resource usage.

## Project Structure
- **client/**: Python Flask client that forwards requests to the server
- **server/**: Python Flask server that provides employee skills data  
- **infra/**: Infrastructure scripts and CloudFormation templates for AWS deployment

## Key Technologies
- Python 3.12.10
- Flask 3.1.0
- Docker with linux/amd64 targeting
- AWS ECS Fargate
- Gunicorn production server

## Local Development
```bash
# Run locally with Docker Compose
docker-compose up --build

# Run health checks
curl http://localhost:8080/health
curl http://localhost:8081/health

# Test main functionality
curl -X POST http://localhost:8080/inquire \
    -H "Content-Type: application/json" \
    -d '{"question": "Find employees with Python skills"}'
```

## AWS Deployment
```bash
# Build and push Docker images to ECR
./infra/build-push.sh

# Deploy infrastructure
./infra/deploy.sh

# Update services with new images
./infra/deploy.sh update-services
```

## Environment Variables
- `SERVER_URL`: The URL of the server (used by the client)
  - Local: `http://localhost:8081`
  - ECS: `http://python-server.python-agent-ecs-base:8081`

## Container Details
- **Base Image**: python:3.12.10-slim (~150MB)
- **Client**: Port 8080, forwards requests to server
- **Server**: Port 8081, provides employee skills API
- **Health Checks**: Both services provide `/health` endpoints
- **Production**: Gunicorn with 4 workers, 2 threads each

## Migration Status
✅ **Complete** - Migrated from Spring Boot/Kotlin to Python Flask
- Removed all Maven/Java dependencies
- Simplified architecture with minimal Python dependencies
- Updated CloudFormation templates for Python containers
- Verified local testing with docker-compose

See `python-migration.md` for detailed migration information.