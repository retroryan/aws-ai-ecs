# Telemetry Troubleshooting Guide

Simple troubleshooting steps for the AWS Strands + Langfuse integration demo.

## Quick Checks

### 1. Is telemetry enabled?

```bash
python3 infra/deploy.py status
```

Look for: `✅ Langfuse Telemetry: Enabled`

### 2. Are credentials configured?

```bash
# Check if cloud.env exists
ls -la cloud.env

# Check Parameter Store (requires AWS CLI)
aws ssm get-parameter --name /strands-weather-agent/langfuse/public-key --query 'Parameter.Name' --output text
```

### 3. Are services running?

```bash
python3 infra/test_services.py
```

All services should show `✅` status.

## Common Issues

### Issue: "Langfuse not configured"

**Symptom**: Tests show telemetry is disabled

**Fix**:
1. Create cloud.env: `cp cloud.env.example cloud.env`
2. Add your Langfuse credentials to cloud.env
3. Redeploy: `python3 infra/deploy.py services`

### Issue: "No traces in Langfuse dashboard"

**Symptom**: Queries work but no telemetry appears

**Fix**:
1. Verify telemetry is enabled in deployment
2. Run some test queries: `python3 infra/demo_telemetry.py`
3. Wait 30-60 seconds for traces to appear
4. Check CloudWatch logs for errors

### Issue: "Parameter Store access denied"

**Symptom**: Deployment fails with permissions error

**Fix**:
1. Ensure your AWS credentials have SSM permissions
2. Check the region matches your deployment region
3. Re-run deployment: `python3 infra/deploy.py all`

### Issue: "Services not healthy"

**Symptom**: ECS services show 0/1 running tasks

**Fix**:
1. Check CloudWatch logs for the specific service
2. Verify Docker images were pushed to ECR
3. Ensure your AWS account has Bedrock access enabled

## Testing Telemetry Toggle

To verify telemetry can be enabled/disabled:

```bash
# Deploy with telemetry (default)
python3 infra/deploy.py services

# Test it works
python3 infra/test_services.py

# Deploy without telemetry
python3 infra/deploy.py services --disable-telemetry

# Verify it's disabled
python3 infra/test_services.py
```

## Getting Help

1. Check deployment status: `python3 infra/deploy.py status`
2. Run validation: `./infra/validate_deployment.sh`
3. Review CloudWatch logs in AWS Console
4. Check ECS service events for deployment issues

Remember: This is a demo! Keep it simple and focus on showing the integration value.