# Troubleshooting Guide for Strands Weather Agent

## Common Issues

### Model Access and Permissions

1. **Model Access Denied**: 
   - Enable the model in AWS Bedrock console
   - Check IAM permissions
   - Run `./scripts/aws-setup.sh` to diagnose

2. **Missing BEDROCK_MODEL_ID**: The application requires this environment variable
   ```bash
   export BEDROCK_MODEL_ID="amazon.nova-lite-v1:0"
   ```

### Server and Network Issues

1. **Servers not starting**: Check if ports are already in use
   ```bash
   lsof -i :7778
   lsof -i :7779
   lsof -i :7780
   ```

2. **Import errors**: Verify all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

3. **Server connection errors**: Ensure MCP servers are running:
   ```bash
   ./scripts/start_servers.sh
   ps aux | grep python | grep server
   ```

## Docker-Specific Issues

1. **Docker build fails**: Ensure Docker daemon is running
   ```bash
   docker info
   ```

2. **Services not starting**: Check container logs
   ```bash
   docker-compose logs forecast-server
   docker-compose logs weather-agent
   ```

3. **Network issues**: Verify Docker network
   ```bash
   docker network ls
   docker network inspect strands-weather-agent_weather-network
   ```

4. **Environment variables not loading**: Check .env file
   ```bash
   docker-compose config  # Shows resolved configuration
   ```

## AWS Deployment Issues

1. **CloudFormation Stack Fails**:
   - Check CloudFormation events for specific errors
   - Verify AWS quotas (VPCs, EIPs, etc.)
   - Ensure region supports all services

2. **ECS Tasks Not Starting**:
   - Check CloudWatch logs for task errors
   - Verify ECR images exist
   - Check IAM role permissions

3. **ALB Health Checks Failing**:
   - Verify security group allows health check traffic
   - Check service logs for startup errors
   - Ensure health check path returns 200 OK

## Common Docker and AWS Infrastructure Issues

### 🎯 How We Got Docker and AWS Working: A Journey of Fixes

This project went through multiple rounds of debugging to get both Docker and AWS deployments working. Here's the complete story of what went wrong and how we fixed it, so you can avoid the same pain.

### The Investigation Journey

We went through 3 rounds of investigation and fixes before achieving a successful deployment:

#### Round 1: Health Check Configuration Error
**The Problem**: MCP servers had health checks in ECS task definitions, but MCP servers using FastMCP don't provide traditional REST health endpoints - they use JSON-RPC which requires session management.

**The Fix**: Removed health checks from all MCP server task definitions in services.cfn. Only the main service should have health checks.

**Key Learning**: Not all services support simple HTTP health checks. Understand your protocol before adding health checks.

#### Round 2: URL Trailing Slash Mismatch
**The Problem**: Docker Compose used `/mcp/` (with trailing slash) but ECS used `/mcp` (without). This small difference caused connection failures because HTTP routers can treat these as different endpoints.

**The Fix**: Added trailing slashes to all MCP URLs in services.cfn to match Docker configuration.

**Key Learning**: Always ensure exact URL consistency between environments. A single character difference can break everything.

#### Round 3: Network Binding Issue
**The Problem**: MCP servers were listening on `127.0.0.1` (localhost) instead of `0.0.0.0` (all interfaces), making them inaccessible from other containers in the ECS network.

**The Root Cause**: The MCP_HOST environment variable wasn't set in task definitions, so servers defaulted to localhost.

**The Fix**: Added `MCP_HOST=0.0.0.0` and `MCP_PORT=[port]` environment variables to all MCP server task definitions.

**Key Learning**: Containers must bind to 0.0.0.0, not 127.0.0.1. Always explicitly set host bindings in containerized environments.

### The Complete Recipe for Success

Here's exactly how to get Docker and AWS working based on our hard-won experience:

#### 1. Docker Development Setup
```bash
# Always use the start script that exports AWS credentials
./scripts/start_docker.sh

# This script does the magic:
export $(aws configure export-credentials --format env-no-export 2>/dev/null)

# Why this works:
# - Extracts credentials from ANY AWS auth method (SSO, profiles, IAM roles)
# - Passes them as environment variables to Docker
# - Works with temporary credentials and session tokens
```

#### 2. Critical Docker Configuration
```yaml
# docker-compose.yml essentials
services:
  mcp-server:
    environment:
      - MCP_HOST=0.0.0.0  # MUST bind to all interfaces
      - MCP_PORT=7778
      # AWS credentials from start_docker.sh
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7778/health"]
      # Health checks OK in Docker, NOT in ECS for MCP servers
```

#### 3. ECS Task Definition Requirements
```yaml
# Critical environment variables for MCP servers
Environment:
  - Name: MCP_HOST
    Value: 0.0.0.0  # MUST be 0.0.0.0, not 127.0.0.1
  - Name: MCP_PORT
    Value: 7778
# NO HealthCheck section for MCP servers!
```

#### 4. URL Consistency
```yaml
# Ensure trailing slashes match everywhere
# Docker Compose:
- MCP_URL=http://server:7778/mcp/

# ECS Task Definition:
- Name: MCP_URL
  Value: http://server.namespace.local:7778/mcp/  # Same trailing slash!
```

### Deployment Workflow That Actually Works

1. **Make code changes**
2. **ALWAYS rebuild images** (this step is often forgotten!):
   ```bash
   ./infra/deploy.sh build-push
   ```
3. **Deploy to ECS**:
   ```bash
   ./infra/deploy.sh services
   ```
4. **Test the deployment**:
   ```bash
   ./infra/test_services.sh
   ```
5. **Monitor logs if issues**:
   ```bash
   aws logs tail /ecs/strands-weather-agent-main --follow
   ```

### Critical Success Factors

1. **Docker ≠ Production**: What works in Docker might not work in ECS. Always test both.
2. **Rebuild Images**: After ANY code change, rebuild. Stale images are a silent killer.
3. **Network Bindings**: 0.0.0.0 for containers, always. 127.0.0.1 only works locally.
4. **URL Exactness**: Every character matters. `/api` ≠ `/api/`
5. **Health Checks**: Understand your protocol. Not everything supports HTTP GET /health.
6. **Environment Variables**: Explicitly set everything. Don't rely on defaults.
7. **Service Discovery**: Use the correct DNS format: `service.namespace.local`
8. **Logs Are Truth**: When in doubt, check CloudWatch logs. They reveal all.

### The "Never Again" Checklist

Before deploying, verify:
- [ ] All services bind to 0.0.0.0, not 127.0.0.1
- [ ] URLs have consistent trailing slashes across all configs
- [ ] Docker images are freshly built after code changes
- [ ] Health checks are only on services that support them
- [ ] All required environment variables are explicitly set
- [ ] Service discovery names match the pattern: service.namespace.local
- [ ] Security groups allow traffic on all required ports
- [ ] Task definitions have sufficient CPU/memory
- [ ] Execution role can pull images and write logs
- [ ] Task role has permissions for application needs

## Detailed Troubleshooting Guide

### 1. Network Binding Issues
**Problem**: Services listening on `127.0.0.1` (localhost) instead of `0.0.0.0` (all interfaces)
```
# Wrong - only accessible from localhost
Starting server on http://127.0.0.1:8080

# Correct - accessible from other containers
Starting server on http://0.0.0.0:8080
```
**Solution**: Always bind to `0.0.0.0` in containers. Use environment variables like `HOST=0.0.0.0` or check for Docker environment.

### 2. URL Format Mismatches
**Problem**: Trailing slash inconsistencies between environments
```yaml
# Docker Compose
- MCP_URL=http://server:8080/api/

# ECS (missing trailing slash)
- Name: MCP_URL
  Value: http://server:8080/api
```
**Solution**: Be consistent with trailing slashes. Many HTTP routers treat `/api` and `/api/` as different endpoints.

### 3. Service Discovery DNS Issues
**Problem**: Using incorrect DNS names for inter-service communication
```yaml
# Wrong - using external DNS
- API_URL=http://api.example.com:8080

# Correct - using service discovery
- API_URL=http://api.namespace.local:8080
```
**Solution**: Use AWS Service Discovery DNS names (format: `service-name.namespace.local`) for internal communication.

### 4. Health Check Configuration Errors
**Problem**: Adding health checks to services that don't support them
```yaml
# Wrong - MCP servers don't have REST health endpoints
HealthCheck:
  Command: ["CMD", "curl", "-f", "http://localhost:8080/health"]
```
**Solution**: Only add health checks to services with proper health endpoints. Some protocols (like JSON-RPC) don't support simple HTTP health checks.

### 5. Port Mapping Misalignment
**Problem**: Container port doesn't match application port
```yaml
# Container expects port 8080
PortMappings:
  - ContainerPort: 80  # Wrong port!

# Application listening on
app.listen(8080)
```
**Solution**: Ensure container port matches the port your application listens on.

### 6. Missing Environment Variables
**Problem**: Required environment variables not set in task definitions
```yaml
# Application expects DATABASE_URL
# But task definition missing:
Environment:
  - Name: API_KEY
    Value: xxx
  # DATABASE_URL missing!
```
**Solution**: Review application requirements and ensure all environment variables are defined in task definitions.

### 7. Security Group Blocking
**Problem**: Security groups not allowing traffic between services
```
# Main service can't connect to backend on port 7778
Connection refused to backend:7778
```
**Solution**: Ensure security groups allow traffic on required ports between services in the same VPC.

### 8. Docker Image Not Updated
**Problem**: Deploying with old Docker images after code changes
```bash
# Code changed but image not rebuilt
./deploy.sh services  # Deploys old image!
```
**Solution**: Always rebuild and push images after code changes:
```bash
./deploy.sh build-push
./deploy.sh services
```

### 9. Insufficient Task Resources
**Problem**: Container runs out of memory or CPU
```yaml
# Too small for application needs
Cpu: '256'
Memory: '512'
```
**Solution**: Monitor resource usage and allocate sufficient CPU/memory. Common minimums:
- Simple services: 256 CPU, 512 MB
- API services: 512 CPU, 1024 MB
- Heavy workloads: 1024+ CPU, 2048+ MB

### 10. Incorrect AWS Region
**Problem**: Resources created in wrong region
```bash
# Resources in us-east-1 but trying to deploy to us-west-2
aws ecs update-service --region us-west-2  # Service not found!
```
**Solution**: Ensure consistent region across all commands and configurations.

### 11. Task Role vs Execution Role Confusion
**Problem**: Using wrong IAM role for permissions
```yaml
# Wrong - Execution role is for pulling images
ExecutionRoleArn: !Ref TaskRole

# Correct
ExecutionRoleArn: !Ref ExecutionRole  # For ECR/CloudWatch
TaskRoleArn: !Ref TaskRole           # For app permissions
```
**Solution**: 
- Execution Role: Permissions for ECS to pull images and write logs
- Task Role: Permissions for your application (S3, DynamoDB, etc.)

### 12. CloudWatch Logs Configuration
**Problem**: Logs not appearing or going to wrong location
```yaml
LogConfiguration:
  LogDriver: awslogs
  Options:
    awslogs-group: /ecs/myapp      # Group doesn't exist
    awslogs-region: us-east-1      # Wrong region
```
**Solution**: Create log groups before deployment and ensure region matches.

### 13. Load Balancer Target Group Issues
**Problem**: ALB can't reach containers
```
# Target group health checks failing
# All targets showing "unhealthy"
```
**Solution**: 
- Verify container port matches target group port
- Ensure health check path returns 200 OK
- Check security group allows ALB to reach containers

### 14. Service Discovery Registration Failures
**Problem**: Services not registering with AWS Cloud Map
```
# Service discovery enabled but DNS not resolving
nslookup myservice.namespace.local  # No results
```
**Solution**: 
- Verify service discovery service is created
- Check task has successfully started
- Ensure service discovery namespace exists

### 15. Environment-Specific Configuration
**Problem**: Hardcoded values that change between environments
```python
# Wrong - hardcoded
api_url = "http://prod-api.example.com"

# Correct - environment variable
api_url = os.getenv("API_URL", "http://localhost:8080")
```
**Solution**: Always use environment variables for configuration that changes between environments.

## Prevention Best Practices

1. **Use Infrastructure as Code**: CloudFormation/CDK for consistent deployments
2. **Test Locally First**: Docker Compose for local testing before ECS deployment
3. **Monitor Logs**: Set up CloudWatch dashboards and alarms
4. **Implement Retry Logic**: Handle transient failures gracefully
5. **Document Dependencies**: List all required environment variables and ports
6. **Use Least Privilege**: Grant minimum required IAM permissions
7. **Version Everything**: Tag Docker images and CloudFormation templates
8. **Automate Deployments**: Use CI/CD pipelines to prevent manual errors
9. **Health Checks**: Implement proper health endpoints for monitoring
10. **Gradual Rollouts**: Use ECS deployment configurations for safe updates

## Quick Debugging Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster my-cluster --services my-service

# View recent logs
aws logs tail /ecs/my-service --follow

# List tasks and their status
aws ecs list-tasks --cluster my-cluster --service-name my-service

# Describe task failure reasons
aws ecs describe-tasks --cluster my-cluster --tasks <task-arn>

# Test service discovery DNS
nslookup myservice.namespace.local

# Check security group rules
aws ec2 describe-security-groups --group-ids <sg-id>

# Verify task definition environment variables
aws ecs describe-task-definition --task-definition my-task
```