# Testing Overview for Strands Weather Agent Infrastructure

This document provides an overview of the testing infrastructure and guidelines for the Strands Weather Agent project.

## Current Test Structure

### 🧪 Test Files

#### **tests/test_services.py**
- **Purpose**: Comprehensive integration test for deployed AWS services
- **Type**: AWS Deployment Test
- **Requirements**: 
  - AWS credentials configured
  - Infrastructure deployed via `python deploy.py all`
  - CloudFormation stacks running
- **Features**:
  - Tests ALB health endpoints
  - Validates ECS service status
  - Tests query endpoints with configurable queries
  - Checks MCP server connectivity
  - Validates Langfuse telemetry (if configured)
  - Collects and reports performance metrics
  - Supports both AWS and local testing via API_URL override
- **Usage**: 
  ```bash
  python tests/test_services.py
  python tests/test_services.py --verbose --fail-fast
  python tests/test_services.py --api-url http://localhost:7777
  ```

#### **tests/config.py**
- **Purpose**: Centralized test configuration management
- **Features**:
  - Uses the same `.env` file as main infrastructure
  - Supports environment variable overrides
  - Configurable timeouts and behavior flags
  - Manages AWS configuration, service names, and test queries
  - Langfuse configuration with optional cloud.env support

#### **tests/utils.py**
- **Purpose**: Shared utilities for test execution
- **Features**:
  - AWS client management with caching
  - CloudFormation stack output retrieval
  - ECS service health checking
  - CloudWatch logs integration
  - Performance metrics formatting
  - Test execution helpers

## Test Configuration

### Environment Variables

Tests use the same `.env` file as the main infrastructure, plus additional test-specific variables:

```bash
# Main configuration (from .env)
AWS_REGION=us-east-1
BASE_STACK_NAME=strands-weather-agent-base
SERVICES_STACK_NAME=strands-weather-agent-services
CLUSTER_NAME=strands-weather-agent

# Test-specific configuration
TEST_VERBOSE=true           # Enable verbose output by default
TEST_FAIL_FAST=true        # Stop on first failure
TEST_SKIP_LANGFUSE=true    # Skip Langfuse telemetry tests

# Timeouts
TEST_HEALTH_TIMEOUT=10      # Health check timeout (seconds)
TEST_QUERY_TIMEOUT=30       # Query timeout (seconds)
TEST_STARTUP_WAIT=60        # Service startup wait (seconds)

# Local testing
API_URL=http://localhost:7777  # Override for local testing

# Langfuse configuration (from cloud.env if present)
LANGFUSE_HOST=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
```

### Command Line Options

The test script supports various command-line overrides:

- `--verbose, -v`: Enable verbose output
- `--fail-fast`: Stop on first test failure
- `--skip-langfuse`: Skip Langfuse telemetry tests
- `--api-url URL`: Override API URL (for local testing)
- `--region REGION`: Override AWS region

## Testing Scenarios

### 1. AWS Deployment Testing
```bash
# Deploy infrastructure
python deploy.py all

# Wait for deployment
python status.py

# Run tests
python tests/test_services.py
```

### 2. Local Development Testing
```bash
# Start local services (in parent directory)
cd ..
./scripts/start_server.sh

# Run tests against local services
cd infra
python tests/test_services.py --api-url http://localhost:7777
```

### 3. Docker Testing
Docker testing is handled by scripts in the parent directory. The infrastructure tests can be pointed at Docker services using the `--api-url` flag.

## Test Execution Flow

1. **Setup Phase**:
   - Load configuration from .env files
   - Initialize AWS clients
   - Get ALB URL or use override
   - Wait for services to be healthy

2. **Test Execution**:
   - Health endpoint validation
   - MCP server connectivity check
   - ECS service status verification
   - Query execution tests
   - Langfuse telemetry validation (optional)

3. **Reporting**:
   - Performance metrics summary
   - Pass/fail statistics
   - Execution time tracking

## Best Practices

### 1. Configuration Management
- Use environment variables for all configuration
- Keep test configuration in sync with main infrastructure
- Use the same `.env` file to avoid duplication

### 2. Error Handling
- Tests should handle AWS API throttling gracefully
- Provide clear error messages for common issues
- Use timeouts to prevent hanging tests

### 3. Test Isolation
- Each test method should be independent
- Clean up any test artifacts
- Don't assume test execution order

## Future Improvements

### Recommended Enhancements

1. **Unit Tests**:
   - Add unit tests for infrastructure modules
   - Test configuration validation
   - Test utility functions

2. **Performance Tests**:
   - Load testing with concurrent queries
   - Stress testing with large payloads
   - Latency profiling

3. **CI/CD Integration**:
   - GitHub Actions workflow for automated testing
   - Test coverage reporting
   - Automated deployment validation

4. **Test Data Management**:
   - Externalize test queries to JSON files
   - Support for test data fixtures
   - Parameterized test scenarios

5. **Monitoring Integration**:
   - CloudWatch metrics validation
   - Alarm testing
   - Cost tracking validation

## Troubleshooting

### Common Issues

1. **ALB URL Not Found**:
   - Ensure infrastructure is deployed
   - Check stack names match configuration
   - Verify AWS credentials and region

2. **Service Health Failures**:
   - Check ECS service logs with `python commands/logs.py`
   - Verify Docker images are built and pushed
   - Check task definitions and IAM roles

3. **Test Timeouts**:
   - Increase timeout values in environment
   - Check network connectivity
   - Verify services are actually running

4. **Langfuse Connection Issues**:
   - Ensure cloud.env exists with credentials
   - Check telemetry is enabled in deployment
   - Verify network access to Langfuse