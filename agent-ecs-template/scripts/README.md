# Scripts Directory

This directory contains all the scripts for managing the AWS Bedrock demo application.

## Quick Start

```bash
# Initial setup (one-time)
./scripts/setup.sh

# Start services
./scripts/start.sh

# Run tests
./scripts/test.sh
```

## Available Scripts

### Core Operations

- **`setup.sh`** - Initial AWS Bedrock configuration
  - Runs aws-setup.sh to configure Bedrock access
  - Copies bedrock.env to server/.env if needed

- **`start.sh`** - Start services with AWS credentials
  - Exports AWS credentials to environment
  - Starts Docker Compose services
  - Checks health status

- **`stop.sh`** - Stop all services
  - Stops and removes Docker containers
  - Cleans up network

### Testing

- **`test.sh`** - Run comprehensive endpoint tests
  - Tests all API endpoints
  - Validates responses
  - Tests error cases

- **`test-quick.sh`** - Run quick health check
  - Basic connectivity tests
  - Health endpoint checks
  - Sample API call

- **`test-endpoints.sh`** - Detailed endpoint testing
  - Tests server and client endpoints
  - Multiple specialist queries
  - Error handling validation

- **`test-health.sh`** - Health check testing
  - Service connectivity
  - Detailed health information
  - Functional tests

### Development Tools

- **`logs.sh`** - Show Docker Compose logs
  - Follow log output
  - Press Ctrl+C to exit

- **`clean.sh`** - Clean up resources
  - Remove Docker volumes
  - Delete Python cache files
  - Clean build artifacts

- **`rebuild.sh`** - Rebuild containers from scratch
  - Stop existing containers
  - Build without cache
  - Start fresh containers

### AWS Configuration

- **`aws-setup.sh`** - AWS Bedrock setup wizard
  - Checks AWS CLI configuration
  - Lists available Bedrock models
  - Creates bedrock.env configuration file

## Usage Examples

### First Time Setup
```bash
# Configure AWS Bedrock
./scripts/setup.sh

# Start services
./scripts/start.sh

# Verify everything is working
./scripts/test-quick.sh
```

### Daily Development
```bash
# Start services in the morning
./scripts/start.sh

# Watch logs while developing
./scripts/logs.sh

# Run tests after changes
./scripts/test.sh

# Stop services when done
./scripts/stop.sh
```

### Troubleshooting
```bash
# Clean everything and start fresh
./scripts/clean.sh
./scripts/rebuild.sh

# Check service health
./scripts/test-quick.sh

# View logs for errors
./scripts/logs.sh
```

## Notes

- AWS credentials must be configured for Bedrock features to work
- Scripts assume they're run from the project root directory
- All scripts use bash and should work on macOS and Linux
- Windows users should use WSL or Git Bash