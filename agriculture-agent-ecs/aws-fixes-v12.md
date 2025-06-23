# AWS Deployment Fixes for Agriculture Agent ECS

## Overview

This document outlines the AWS deployment fixes needed for the Agriculture Agent ECS project based on analysis of the agent-ecs-template project and common ECS deployment issues.

## Implementation Status

Last Updated: 2025-06-23

### ✅ Implemented Fixes
- Docker credential handling via AWS CLI export
- Port configuration (Weather Agent on 7075)
- Service dependencies (MainService depends on MCP services)
- Network configuration (AssignPublicIp: ENABLED)
- Deployment scripts (aws-checks.sh, deploy.sh, build-push.sh)
- Image tag management (.image-tags file)
- Docker Compose health checks for MCP servers

### ❌ Not Yet Implemented
- IAM role permissions (still using wildcards)
- Health check timing adjustments
- Service discovery dynamic URLs
- Startup delays
- Container-level health checks for MCP servers
- Enhanced CloudWatch logging
- Target tracking scaling improvements

## Critical Fixes Required

### 1. IAM Role Permissions ❌ NOT IMPLEMENTED

**Current Issue**: Using wildcard permissions for Bedrock (base.cfn:136)
```yaml
Resource: '*'
```

**Fix Required**: Use specific model permissions
```yaml
# In base.cfn - TaskRole policies
Policies:
  - PolicyName: BedrockInvokeAccess
    PolicyDocument:
      Statement:
        - Effect: Allow
          Action:
            - bedrock:InvokeModel
          Resource:
            - !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.nova-lite-v1:0'
            - !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/amazon.nova-pro-v1:0'
            - !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0'
            - !Sub 'arn:aws:bedrock:${AWS::Region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0'
```

### 2. Health Check Timing ❌ NOT IMPLEMENTED

**Current Issue**: Health checks timeout too quickly (base.cfn:215-216)
```yaml
HealthCheckIntervalSeconds: 30
HealthCheckTimeoutSeconds: 5
```

**Fix Required**: Increase timeouts for services that need time to initialize
```yaml
# In base.cfn - TargetGroup
HealthCheckPath: /health
HealthCheckProtocol: HTTP
HealthCheckTimeoutSeconds: 120
HealthCheckIntervalSeconds: 240
HealthyThresholdCount: 2
UnhealthyThresholdCount: 3
```

### 3. Task Definition Environment Variables ❌ NOT IMPLEMENTED

**Current Issue**: Hardcoded MCP service URLs using `.agriculture.local` (services.cfn:244-249)
```yaml
- Name: MCP_FORECAST_URL
  Value: http://forecast.agriculture.local:7071/mcp
```

**Fix Required**: Use proper service discovery names with dynamic namespace
```yaml
# In services.cfn - MainTaskDefinition
Environment:
  - Name: MCP_FORECAST_URL
    Value: !Sub 'http://forecast.${ServiceDiscoveryNamespace}:7071/mcp'
  - Name: MCP_HISTORICAL_URL  
    Value: !Sub 'http://historical.${ServiceDiscoveryNamespace}:7072/mcp'
  - Name: MCP_AGRICULTURAL_URL
    Value: !Sub 'http://agricultural.${ServiceDiscoveryNamespace}:7073/mcp'
```

### 4. Network Configuration ✅ IMPLEMENTED

**Status**: Already correct in services.cfn (lines 282, 302, 322, 346)
```yaml
NetworkConfiguration:
  AwsvpcConfiguration:
    AssignPublicIp: ENABLED
```

### 5. Service Dependencies and Startup Order ✅ PARTIALLY IMPLEMENTED

**Status**: MainService has DependsOn (services.cfn:328-331) but missing startup delay parameter

**Implemented**:
```yaml
MainService:
  DependsOn:
    - ForecastService
    - HistoricalService
    - AgriculturalService
```

**Still Missing**: Startup delay parameter
```yaml
# Add parameter for delayed startup
ClientStartupDelay:
  Type: Number
  Default: 180
  Description: Delay in seconds before starting the main service

# In MainService definition
DependsOn:
  - ForecastService
  - HistoricalService
  - AgriculturalService
```

### 6. Deployment Utilities ✅ IMPLEMENTED

**Status**: All deployment scripts exist and are functional

**Available Scripts**:
- `infra/aws-checks.sh` ✅ Exists
- `infra/build-push.sh` ✅ Exists
- `infra/deploy.sh` ✅ Exists
- `infra/deploy-services.sh` ✅ Exists

#### Example `infra/aws-checks.sh`
```bash
#!/bin/bash
# Validates AWS configuration before deployment

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not installed"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured"
    exit 1
fi

# Check Bedrock access
REGION=${AWS_REGION:-us-east-1}
if ! aws bedrock list-foundation-models --region $REGION &> /dev/null; then
    echo "❌ No access to Bedrock in region $REGION"
    exit 1
fi

echo "✅ AWS configuration validated"
```

### 7. Image Tag Management ✅ IMPLEMENTED

**Status**: `.image-tags` file exists and is actively maintained with proper format

**Current Implementation** (infra/.image-tags):
```
MAIN_IMAGE_TAG=b18a2bc-20250622-233216
FORECAST_IMAGE_TAG=b18a2bc-20250622-233216
HISTORICAL_IMAGE_TAG=b18a2bc-20250622-233216
AGRICULTURAL_IMAGE_TAG=b18a2bc-20250622-233216
BUILD_TIMESTAMP=2025-06-23T05:32:51Z
```

**Build Script Integration**:
```bash
# In build-push.sh
TAG=${OVERRIDE_TAG:-$(git rev-parse --short HEAD)}
echo "forecast=$TAG" > .image-tags
echo "historical=$TAG" >> .image-tags
echo "agricultural=$TAG" >> .image-tags
echo "main=$TAG" >> .image-tags
```

### 8. Container-Level Health Checks ❌ PARTIALLY IMPLEMENTED

**Status**: Only MainTaskDefinition has health check (services.cfn:256-263). MCP server task definitions missing health checks.

**Implemented for Main Service**:
```yaml
HealthCheck:
  Command:
    - CMD-SHELL
    - curl -f http://localhost:7075/health || exit 1
  Interval: 30
  Timeout: 5
  Retries: 3
  StartPeriod: 60
```

**Missing for MCP Servers**: Need to add to Forecast, Historical, and Agricultural task definitions
```yaml
HealthCheck:
  Command:
    - CMD-SHELL
    - curl -f http://localhost:7075/health || exit 1
  Interval: 30
  Timeout: 10
  Retries: 5
  StartPeriod: 120
```

### 9. Logging Configuration ❌ NOT IMPLEMENTED

**Current Issue**: Missing datetime format in CloudWatch logs configuration

**Fix Required**: Enhance CloudWatch logs configuration
```yaml
LogConfiguration:
  LogDriver: awslogs
  Options:
    awslogs-group: !Ref LogGroup
    awslogs-region: !Ref AWS::Region
    awslogs-stream-prefix: !Sub '${ServiceName}'
    awslogs-datetime-format: '%Y-%m-%d %H:%M:%S'
```

### 10. Auto-scaling Configuration ❌ NOT IMPLEMENTED

**Current Issue**: Basic auto-scaling configuration without enhanced target tracking

**Current Implementation** (services.cfn:369-380):
- Basic target tracking scaling policy
- CPU utilization target: 70%
- Scale in/out cooldowns: 300/60 seconds

**Enhancement Needed**: More sophisticated scaling configuration
```yaml
TargetTrackingScalingPolicy:
  Type: AWS::ApplicationAutoScaling::ScalingPolicy
  Properties:
    PolicyName: !Sub ${AWS::StackName}-target-tracking
    PolicyType: TargetTrackingScaling
    ScalingTargetId: !Ref MainScalableTarget
    TargetTrackingScalingPolicyConfiguration:
      TargetValue: 70.0
      PredefinedMetricSpecification:
        PredefinedMetricType: ECSServiceAverageCPUUtilization
      ScaleInCooldown: 300
      ScaleOutCooldown: 60
```

## Deployment Process Improvements

### 1. Pre-deployment Validation
```bash
# Add to deploy.sh
echo "Running pre-deployment checks..."
./aws-checks.sh || exit 1
```

### 2. Rollback Capability
```bash
# Save previous task definitions
aws ecs describe-task-definition --task-definition $TASK_NAME \
  --query 'taskDefinition' > rollback/$TASK_NAME-$(date +%s).json
```

### 3. Deployment Verification
```bash
# Add service stability check
wait_for_service_stable() {
    local service=$1
    echo "Waiting for $service to stabilize..."
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $service
}
```

### 4. Clean Build Support
```bash
# In build-push.sh
if [ "$FORCE_BUILD" = "true" ]; then
    docker build --no-cache ...
else
    docker build ...
fi
```

## Testing the Fixes

1. **Local Validation**:
   ```bash
   # Test configuration locally
   ./infra/aws-checks.sh
   cfn-lint infra/*.cfn
   ```

2. **Staged Deployment**:
   ```bash
   # Deploy base infrastructure first
   ./deploy.sh base
   
   # Then deploy services
   ./deploy.sh services
   ```

3. **Health Verification**:
   ```bash
   # Check all services are healthy
   ./deploy.sh status
   ```

## Docker Fixes (from key-to-aws-in-docker.md) ✅ ALL IMPLEMENTED

### AWS Credential Handling ✅
**Status**: Fully implemented in `scripts/start.sh`
```bash
export $(aws configure export-credentials --format env-no-export 2>/dev/null)
```

### Port Configuration ✅
**Status**: Weather Agent API correctly using port 7075
- All references updated in docker-compose.yml, Dockerfiles, and infrastructure

### Health Check Fixes ✅
**Status**: MCP servers correctly use `/mcp` endpoint for health checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "-X", "POST", "http://localhost:7071/mcp", 
         "-H", "Content-Type: application/json", 
         "-d", '{"jsonrpc": "2.0", "method": "mcp/list_tools", "id": 1}']
```

### Docker Image Selection ✅
**Status**: docker-compose.yml correctly uses `Dockerfile.main` for the weather agent

## Summary

### Fully Implemented ✅
- Docker credential handling and AWS authentication
- Port configuration (7075 for main API)
- Service dependencies (DependsOn)
- Network configuration (AssignPublicIp)
- Deployment scripts and utilities
- Image tag management
- Docker health checks for MCP servers

### Partially Implemented ⚠️
- Service dependencies (missing startup delays)
- Container health checks (only main service has them)

### Not Implemented ❌
- IAM role permissions (still using wildcards)
- Health check timing adjustments for ALB
- Service discovery dynamic namespace URLs
- Enhanced CloudWatch logging with datetime format
- Advanced auto-scaling configuration

With the remaining fixes implemented, the Agriculture Agent ECS deployment will be more robust, secure, and maintainable.