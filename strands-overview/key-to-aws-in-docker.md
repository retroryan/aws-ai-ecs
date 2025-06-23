# Key to AWS Credentials in Docker

## The Problem

When running AWS applications in Docker containers, the containers cannot access AWS credentials configured on the host machine. This leads to the common error:
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

## The Solution

The key to fixing AWS credential errors in Docker is using the AWS CLI's `export-credentials` command to automatically extract and pass credentials as environment variables.

### Implementation

#### 1. The Magic Command
```bash
export $(aws configure export-credentials --format env-no-export)
```

This command:
- Extracts credentials from your current AWS CLI configuration
- Exports them as environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
- Works with ALL authentication methods:
  - AWS CLI profiles
  - AWS SSO (Single Sign-On)
  - Temporary credentials
  - IAM roles
  - MFA-enabled accounts

#### 2. The Start Script (`scripts/start.sh`)
```bash
#!/bin/bash

# Export AWS credentials from AWS CLI configuration
echo "Exporting AWS credentials..."
if command -v aws &> /dev/null; then
    if aws sts get-caller-identity &> /dev/null; then
        # This is the key line that makes it all work
        export $(aws configure export-credentials --format env-no-export 2>/dev/null)
        
        # Display current AWS identity
        AWS_IDENTITY=$(aws sts get-caller-identity --query 'Arn' --output text)
        echo "✓ Using AWS identity: $AWS_IDENTITY"
    fi
fi

# Now start Docker Compose with credentials available
docker-compose up -d
```

#### 3. Docker Compose Configuration
```yaml
services:
  weather-agent:
    environment:
      # These will now receive values from the exported credentials
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
      - AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
```

## Why This Works

1. **No Manual Configuration**: Users don't need to manually set AWS credentials
2. **No Credential Storage**: Credentials are never stored in files
3. **Universal Compatibility**: Works with any AWS authentication method
4. **Security**: Credentials are only passed at runtime as environment variables
5. **Temporary Credentials**: Handles session tokens for SSO/temporary credentials

## Common Pitfalls Avoided

1. **Don't use AWS profiles in Docker**: Containers can't access ~/.aws/config
2. **Don't hardcode credentials**: Security risk and maintenance nightmare
3. **Don't use volume mounts for ~/.aws**: Doesn't work with SSO or temporary credentials
4. **Don't forget AWS_SESSION_TOKEN**: Required for temporary credentials

## Additional Docker Fixes

### Port Configuration
- Weather Agent API runs on port 8090
- MCP servers run on ports 8081-8083:
  - Forecast Server: 8081
  - Historical Server: 8082
  - Agricultural Server: 8083

### Health Check Fixes
- MCP servers use `/mcp` endpoint with JSON-RPC for health checks:
  ```bash
  curl -X POST http://localhost:8081/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}'
  ```

### Docker Image Selection
- docker-compose.yml uses `Dockerfile.main` for the Weather Agent API
- Dockerfile.main creates the FastAPI server needed for the API

### Test Script Improvements
- Updated test_docker.sh to handle:
  - Already running containers
  - Proper health checks for all services
  - AWS credential errors as warnings (expected without config)
  - Better error reporting and logging

## Testing the Fix

1. Start services with credentials:
   ```bash
   ./scripts/start.sh
   ```

2. Test the API:
   ```bash
   curl -X POST http://localhost:8090/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the weather in Chicago?"}'
   ```

3. Verify no credential errors in logs:
   ```bash
   docker logs weather-agent-app | grep -i credential
   ```

## Result

With these fixes, the Strands Overview project now:
- ✅ Automatically passes AWS credentials to Docker containers
- ✅ Supports all AWS authentication methods
- ✅ Maintains security best practices
- ✅ Works seamlessly with local development
- ✅ Provides clear feedback about AWS identity being used