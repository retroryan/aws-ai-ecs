# AWS Deployment Fixes for Agriculture Agent ECS

## Overview

This document outlines the AWS deployment fixes needed for the Agriculture Agent ECS project based on analysis of the agent-ecs-template project and common ECS deployment issues.

## Critical Fixes Required

### 1. IAM Role Permissions

**Current Issue**: Using wildcard permissions for Bedrock
```yaml
Resource: '*'
```

**Fix**: Use specific model permissions
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

### 2. Health Check Timing

**Current Issue**: Health checks timeout too quickly
```yaml
HealthCheckIntervalSeconds: 30
HealthCheckTimeoutSeconds: 5
```

**Fix**: Increase timeouts for services that need time to initialize
```yaml
# In base.cfn - TargetGroup
HealthCheckPath: /health
HealthCheckProtocol: HTTP
HealthCheckTimeoutSeconds: 120
HealthCheckIntervalSeconds: 240
HealthyThresholdCount: 2
UnhealthyThresholdCount: 3
```

### 3. Task Definition Environment Variables

**Current Issue**: Hardcoded MCP service URLs might not resolve correctly

**Fix**: Use proper service discovery names
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

### 4. Network Configuration

**Issue**: Tasks need public IPs to pull from ECR

**Fix**: Already correct in services.cfn
```yaml
NetworkConfiguration:
  AwsvpcConfiguration:
    AssignPublicIp: ENABLED
```

### 5. Service Dependencies and Startup Order

**Missing**: Ordered service deployment

**Add**: Startup delays and dependency management
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

### 6. Missing Deployment Utilities

**Add these scripts from agent-ecs-template**:

#### `infra/aws-checks.sh`
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

### 7. Image Tag Management

**Add**: `.image-tags` file support for version tracking
```bash
# In build-push.sh
TAG=${OVERRIDE_TAG:-$(git rev-parse --short HEAD)}
echo "forecast=$TAG" > .image-tags
echo "historical=$TAG" >> .image-tags
echo "agricultural=$TAG" >> .image-tags
echo "main=$TAG" >> .image-tags
```

### 8. Container-Level Health Checks

**Add to each task definition**:
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

### 9. Logging Configuration

**Enhance CloudWatch logs configuration**:
```yaml
LogConfiguration:
  LogDriver: awslogs
  Options:
    awslogs-group: !Ref LogGroup
    awslogs-region: !Ref AWS::Region
    awslogs-stream-prefix: !Sub '${ServiceName}'
    awslogs-datetime-format: '%Y-%m-%d %H:%M:%S'
```

### 10. Auto-scaling Configuration

**Current**: Only on main service

**Enhancement**: Add target tracking for better scaling
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

## Summary

These fixes address:
- ✅ IAM permission security
- ✅ Service discovery reliability
- ✅ Health check stability
- ✅ Deployment orchestration
- ✅ Monitoring and logging
- ✅ Error handling and rollback

With these changes, the Agriculture Agent ECS deployment will be more robust, secure, and maintainable.