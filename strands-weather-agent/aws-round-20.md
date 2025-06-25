# AWS Round 20: Strands Weather Agent Services Deployment Investigation

## Investigation Overview
Investigating deployment failures for strands-weather-agent-services using the infra/deploy.sh services script.

## Investigation Progress

### Initial Assessment
- Date: 2025-06-24
- Issue: strands-weather-agent-services not deploying when using infra/deploy.sh services script
- Goal: Identify root cause and implement fixes

### Investigation Steps

#### Step 1: Examining the Deploy Script and CloudFormation Status
- The deploy.sh script uses Rain CLI to deploy CloudFormation stacks
- Checked current stack status: CREATE_IN_PROGRESS
- Stack was initiated at 2025-06-24T15:44:07
- Parameters show it's using amazon.nova-lite-v1:0 model

**Current Service Creation Status:**
- ForecastService: CREATE_COMPLETE
- HistoricalService: CREATE_COMPLETE  
- AgriculturalService: CREATE_COMPLETE
- MainService: CREATE_IN_PROGRESS (as of 15:46:36)

#### Step 2: Identified Root Cause
**Main Agent Container Exit Code 3 - Connection Failures**

CloudWatch logs show the main agent is failing to initialize MCP clients:
```
client failed to initialize
httpcore.ConnectError: All connection attempts failed
```

The main agent is trying to connect to MCP servers via service discovery URLs:
- http://forecast.strands-weather.local:8081/mcp
- http://historical.strands-weather.local:8082/mcp
- http://agricultural.strands-weather.local:8083/mcp

### Detailed Comparison: Agriculture Agent vs Strands Weather Agent

#### Key Differences Found

##### 1. **Port Configuration Mismatch**
- **Agriculture Agent**: Uses ports 7071, 7072, 7073
- **Strands Weather Agent**: Uses ports 8081, 8082, 8083
- **CRITICAL ISSUE**: The security group in strands-weather-agent base.cfn only allows ports 8081-8083, but the target group and ALB listener expect port 8000, while the main service runs on port 8090!

##### 2. **Security Group Configuration Issues**

**Agriculture Agent (base.cfn)**:
```yaml
ServiceSecurityGroup:
  SecurityGroupIngress:
    - Description: Allow traffic from ALB
      FromPort: 7075
      ToPort: 7075
      IpProtocol: tcp
      SourceSecurityGroupId: !Ref ALBSecurityGroup
    - Description: Allow inter-service communication
      FromPort: 7071
      ToPort: 7073
      IpProtocol: tcp
      CidrIp: 10.0.0.0/16
```

**Strands Weather Agent (base.cfn)** - PROBLEMATIC:
```yaml
ServiceSecurityGroup:
  SecurityGroupIngress:
    - Description: Allow traffic from ALB
      FromPort: 8000  # Wrong port - main service uses 8090
      ToPort: 8000
      IpProtocol: tcp
      SourceSecurityGroupId: !Ref ALBSecurityGroup
    - Description: Allow inter-service communication
      FromPort: 8081
      ToPort: 8083  # Missing port 8090 for main service
      IpProtocol: tcp
      CidrIp: 10.0.0.0/16
```

##### 3. **ALB Target Group Port Mismatch**

**Agriculture Agent**:
- ALB Target Group: Port 7075 (matches main service)
- Main Service Container: Port 7075 ✓

**Strands Weather Agent**:
- ALB Target Group: Port 8000 ❌
- Main Service Container: Port 8090 ❌
- **This is a critical mismatch!**

##### 4. **MCP Client Implementation Differences**

**Agriculture Agent**: Uses LangGraph with langchain-mcp-adapters
```python
# Uses MultiServerMCPClient from langchain_mcp_adapters
self.mcp_client = MultiServerMCPClient(server_config)
```

**Strands Weather Agent**: Uses AWS Strands native MCP
```python
# Uses MCPClient from strands.tools.mcp
client = MCPClient(
    lambda url=url: streamablehttp_client(url)
)
```

##### 5. **Default URL Configuration**

**Agriculture Agent**:
```python
"MCP_FORECAST_URL", "http://127.0.0.1:7071/mcp"  # Uses 127.0.0.1
```

**Strands Weather Agent**:
```python
"MCP_FORECAST_URL", "http://localhost:8081/mcp"  # Uses localhost
```

### Root Cause Analysis

The deployment is failing because:

1. **Port Configuration Conflicts**: The security group and ALB target group are configured for the wrong ports
2. **Main Service Can't Start**: The main agent exits with code 3 because it can't connect to MCP servers
3. **Network Connectivity**: MCP servers might be starting but the main service can't reach them due to security group rules

### Verification Steps Completed

✅ CloudFormation stack is deploying (CREATE_IN_PROGRESS)
✅ ECR repositories exist and contain Docker images (latest tag pushed at 2025-06-24T09:43:25)
✅ MCP services (forecast, historical, agricultural) deployed successfully
❌ Main service keeps failing and restarting due to connection errors

## Proposed Fixes

### Fix 1: Update Security Group Rules in base.cfn

```yaml
ServiceSecurityGroup:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupName: strands-weather-agent-service-sg
    GroupDescription: Security group for ECS services
    VpcId: !Ref ApplicationVPC
    SecurityGroupIngress:
      - Description: Allow traffic from ALB
        FromPort: 8090  # Changed from 8000 to match main service
        ToPort: 8090
        IpProtocol: tcp
        SourceSecurityGroupId: !Ref ALBSecurityGroup
      - Description: Allow inter-service communication
        FromPort: 8081
        ToPort: 8090  # Extended range to include main service port
        IpProtocol: tcp
        CidrIp: 10.0.0.0/16
```

### Fix 2: Update ALB Target Group Port in base.cfn

```yaml
ALBTargetGroup:
  Type: AWS::ElasticLoadBalancingV2::TargetGroup
  Properties:
    Name: strands-weather-agent
    Port: 8090  # Changed from 8000 to match main service
    Protocol: HTTP
    VpcId: !Ref ApplicationVPC
    TargetType: ip
    HealthCheckPath: /health
    HealthCheckProtocol: HTTP
    HealthCheckIntervalSeconds: 30
    HealthCheckTimeoutSeconds: 5
    HealthyThresholdCount: 2
    UnhealthyThresholdCount: 3
    Matcher:
      HttpCode: '200'
```

### Fix 3: Add Startup Delay or Retry Logic

The main service should wait for MCP servers to be fully available. Options:

1. **Add StartPeriod to MainTaskDefinition** (already set to 60s, might need increase)
2. **Implement retry logic in the application** when initializing MCP clients
3. **Use ECS service dependencies** more effectively

### Fix 4: Consider Adding Health Checks to MCP Services

Currently, only the main service has a health check. Adding health checks to MCP services would ensure they're ready before the main service tries to connect:

```yaml
HealthCheck:
  Command:
    - CMD-SHELL
    - curl -f http://localhost:8081/health || exit 1
  Interval: 30
  Timeout: 5
  Retries: 3
  StartPeriod: 30
```

### Fix 5: Update Service Discovery Configuration

Ensure the MCP services register with service discovery correctly. The current configuration looks correct, but we should verify the DNS resolution is working.

## Immediate Action Items

1. **Update base.cfn** with the correct port configurations
2. **Redeploy the base stack** to apply security group changes
3. **Update and redeploy services** to ensure they pick up the new configuration
4. **Monitor CloudWatch logs** to verify connectivity is established

## Testing Strategy

After applying fixes:
1. Check that all ECS services reach RUNNING state
2. Verify main service can connect to MCP servers
3. Test the application via ALB endpoint
4. Monitor for any remaining connection errors

## Port Configuration Summary (All Fixed)

### Port Assignments:
- **Main API**: 8090
- **Forecast Server**: 8081
- **Historical Server**: 8082
- **Agricultural Server**: 8083

### Configuration Files Updated:
1. **base.cfn**:
   - ✅ Security Group: Now allows ALB → 8090 and inter-service 8081-8083, 8090
   - ✅ ALB Target Group: Changed from 8000 to 8090

2. **services.cfn**:
   - ✅ All container ports correctly set (8081, 8082, 8083, 8090)
   - ✅ MCP URLs use correct ports in environment variables

3. **Docker Configuration**:
   - ✅ All Dockerfiles expose correct ports
   - ✅ Application code uses correct default ports

## Next Steps

1. **Redeploy the base stack** to apply the security group and ALB changes:
   ```bash
   ./infra/deploy.sh base
   ```

2. **Redeploy the services** to ensure they use the updated configuration:
   ```bash
   ./infra/deploy.sh services
   ```

3. **Monitor the deployment** to ensure all services start successfully.
