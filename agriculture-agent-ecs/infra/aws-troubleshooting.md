# AWS Agriculture Agent ECS Troubleshooting Guide

## Current Infrastructure Status

### ✅ Completed Items
1. **ECR Repository Setup** - All repositories created and accessible
   - agriculture-agent-main
   - agriculture-agent-weather

2. **Docker Images Built and Pushed** - All images successfully deployed to ECR
   - Images tagged with: a0bdd93-20250622-184247
   - All images also tagged as 'latest'

3. **Infrastructure Naming Simplified** - Removed -dev suffix from all resources
   - Stack names: agriculture-agent-base, agriculture-agent-services
   - All CloudFormation templates updated
   - Documentation updated to reflect new naming

4. **Base Infrastructure Deployed** - VPC, ECS Cluster, IAM Roles created
   - VPC with public subnets configured
   - ECS cluster with Container Insights enabled
   - Service discovery namespace: agriculture.local
   - Application Load Balancer configured

### ⚠️ Current Issues

1. **ECS Services Deployment** - Services stack deployment in progress/stuck
   - Last known issue: Tasks failing to pull images from ECR
   - Root cause: AssignPublicIp was set to DISABLED
   - Fix applied: Changed AssignPublicIp to ENABLED in services.cfn
   - Status: Needs redeployment to test fix

### 📋 TODO List

#### Immediate Actions
- [ ] Cancel stuck services stack deployment
- [ ] Redeploy services with AssignPublicIp fix
- [ ] Verify all services start successfully
- [ ] Test application endpoints

#### Infrastructure Verification
- [ ] Confirm all ECS tasks are running
- [ ] Verify service discovery is working
- [ ] Test inter-service communication
- [ ] Validate ALB health checks

#### Missing Components
- [ ] Add aws-setup.sh script from template project
- [ ] Create bedrock.env configuration file
- [ ] Update deployment scripts with missing utility

#### Testing & Validation
- [ ] Test main agent endpoint via ALB
- [ ] Verify MCP server connectivity
- [ ] Test sample weather queries
- [ ] Monitor CloudWatch logs for errors

## Next Steps

### 1. Fix Services Deployment (Priority: HIGH)
```bash
# Cancel stuck deployment
aws cloudformation cancel-update-stack --stack-name agriculture-agent-services --region us-east-1
# OR if stuck in CREATE_IN_PROGRESS
aws cloudformation delete-stack --stack-name agriculture-agent-services --region us-east-1

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete --stack-name agriculture-agent-services --region us-east-1

# Redeploy with fix
./infra/deploy.sh services
```

### 2. Add Missing AWS Setup Script (Priority: MEDIUM)
Copy and adapt aws-setup.sh from the template project to:
- Validate AWS CLI configuration
- Check Bedrock model access
- Generate bedrock.env file
- List available models

### 3. Verify Deployment (Priority: HIGH)
```bash
# Check deployment status
./infra/deploy.sh status

# Monitor ECS services
aws ecs list-services --cluster agriculture-agent --region us-east-1

# Check task status
aws ecs list-tasks --cluster agriculture-agent --region us-east-1

# View logs
aws logs tail /ecs/agriculture-agent-main --follow
```

### 4. Test Application (Priority: HIGH)
```bash
# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
  --stack-name agriculture-agent-base \
  --query 'Stacks[0].Outputs[?OutputKey==`ALBDNSName`].OutputValue' \
  --output text --region us-east-1)

# Test health endpoint
curl http://$ALB_URL/health

# Test query endpoint
curl -X POST http://$ALB_URL/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the weather in Chicago?"}'
```

## Known Issues & Solutions

### Issue: Tasks Cannot Pull ECR Images
**Symptoms**: ResourceInitializationError, unable to pull secrets or registry auth
**Cause**: Tasks in private subnets without internet access
**Solution**: 
- Set AssignPublicIp: ENABLED in services.cfn (COMPLETED)
- Alternative: Add NAT Gateway (more complex, not needed for demo)

### Issue: Service Discovery Not Working
**Symptoms**: Main agent cannot reach MCP servers
**Cause**: Security group rules or DNS resolution
**Solution**: 
- Verify security group allows port 7071
- Check service discovery namespace is created
- Ensure services register with Cloud Map

### Issue: Bedrock Access Denied
**Symptoms**: AccessDeniedException when invoking models
**Cause**: Model not enabled in Bedrock console
**Solution**: 
- Enable desired models in AWS Bedrock console
- Verify IAM role has bedrock:InvokeModel permission
- Check correct region is being used

## Architecture Comparison Notes

### Template Project vs Agriculture Agent
1. **Service Architecture**:
   - Template: Simple client-server (2 services)
   - Agriculture: Multi-service with discovery (2 services - main + weather)

2. **Network Configuration**:
   - Template: Private subnets (MapPublicIpOnLaunch: false)
   - Agriculture: Public subnets (MapPublicIpOnLaunch: true)

3. **Missing Components**:
   - aws-setup.sh utility script
   - All other infrastructure components are present

## Progress Tracking

### Phase 4 Infrastructure Status
- [x] Initial infrastructure copied from template
- [x] Updated naming conventions for agriculture agent
- [x] Fixed ECR repository creation
- [x] Built and pushed all Docker images
- [x] Deployed base infrastructure
- [x] Removed -dev suffix from all resources
- [ ] Successfully deployed services
- [ ] Verified application functionality
- [ ] Added missing aws-setup.sh utility

### Time Estimates
- Services deployment fix: 15-30 minutes
- Adding aws-setup.sh: 10 minutes
- Full testing and validation: 30-45 minutes
- Total estimated completion: 1-2 hours

## Support Resources
- CloudFormation Console: https://console.aws.amazon.com/cloudformation
- ECS Console: https://console.aws.amazon.com/ecs
- CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/logs
- Bedrock Console: https://console.aws.amazon.com/bedrock

Last Updated: 2025-06-23T00:50:00Z