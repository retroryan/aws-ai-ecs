# Infrastructure Architecture

This document provides a high-level overview of the AWS infrastructure for the Spring AI MCP Agent deployment using CloudFormation and helper scripts.

## CloudFormation Architecture

The infrastructure is split into two CloudFormation stacks for modularity and faster deployments:

### Base Stack (infra/base.cfn)

The base stack creates the foundational AWS infrastructure that rarely changes:

**Networking Components:**
- **VPC** (10.0.0.0/16): Virtual Private Cloud with DNS support
- **Internet Gateway**: Provides internet connectivity
- **Private Subnets**: Two subnets (10.0.1.0/24, 10.0.2.0/24) across availability zones
- **Route Tables**: Configured for private subnet routing through the Internet Gateway
- **Security Groups**:
  - Server SG: Allows port 8081 from Client SG only
  - Client SG: Allows port 8080 from ALB, outbound HTTPS for Bedrock, port 8081 for MCP Server
  - ALB SG: Allows port 80 from anywhere

**ECS Foundation:**
- **ECS Cluster**: Container orchestration platform
- **Service Connect Namespace**: Enables service discovery between containers
- **CloudWatch Log Group**: Centralized logging for ECS tasks

**IAM Roles:**
- **Execution Roles**: Separate roles for server and client containers
- **Task Role**: Permissions to invoke Amazon Bedrock Nova Pro model

**Load Balancing:**
- **Application Load Balancer**: Internet-facing ALB for public access
- **Target Group**: Routes traffic to port 8080 with health checks
- **HTTP Listener**: Accepts traffic on port 80

### Services Stack (infra/services.cfn)

The services stack deploys the actual application containers:

**Task Definitions:**
- **Server Task**: 256 CPU / 512 MB memory, port 8081
- **Client Task**: 256 CPU / 1024 MB memory, port 8080

**ECS Services:**
- **MCP Server Service**: 
  - Service Connect enabled with discovery name `mcp-server`
  - Runs independently with public IP assignment
- **MCP Client Service**:
  - Service Connect enabled
  - Connected to ALB for external access
  - Environment variable: `MCP_SERVICE_URL=http://mcp-server.spring-ai-mcp-base:8081`
  - Depends on server service for startup sequencing

## Infrastructure Helper Scripts

The `infra/` directory contains automation scripts that simplify deployment:

### aws-checks.sh
Validates AWS environment readiness:
- Verifies AWS CLI authentication
- Checks IAM permissions
- Validates Bedrock access and Nova Pro availability
- Confirms ECR repositories exist
- Tests ECS task execution role permissions

### setup-ecr.sh
Automates container registry setup:
- Creates ECR repositories for server and client images
- Configures Docker authentication with ECR
- Sets up lifecycle policies
- Outputs ECR_REPO environment variable

### build-push.sh
Builds and deploys container images:
- Builds Spring Boot Docker images using buildpacks
- **IMPORTANT**: Explicitly sets target architecture to linux/amd64 for ECS Fargate compatibility
- Uses Paketo buildpack environment variables BP_BUILD_PLATFORM and BP_RUN_PLATFORM
- Tags images appropriately with git commit hash and timestamp
- Pushes to ECR with proper authentication

### test_services.sh
Validates deployment success:
- Retrieves ALB URL from CloudFormation
- Sends test request to MCP agent endpoint
- Confirms end-to-end functionality

### deploy.sh
Master orchestration script with commands:
- `aws-checks`: Validate environment
- `setup-ecr`: Create repositories
- `build-push`: Build and push images
- `all`: Deploy complete infrastructure
- `base`: Deploy only base stack
- `services`: Deploy only services
- `update-services`: Update services after code changes
- `status`: Show deployment status
- `cleanup-*`: Remove infrastructure

## Reusability for Other Projects

This infrastructure pattern is highly reusable for deploying any client-server containerized application:

### Adaptation Steps:

1. **Replace Application Code**:
   - Swap the Spring AI MCP client/server with your applications
   - Ensure your apps expose appropriate ports (default: 8080 for client, 8081 for server)

2. **Update Task Definitions**:
   - Modify CPU/memory requirements in `services.cfn`
   - Add/remove environment variables as needed
   - Adjust health check endpoints

3. **Configure Networking**:
   - Update security group rules for your application ports
   - Modify ALB target group settings if using different ports

4. **Service Discovery**:
   - Use the Service Connect namespace for internal communication
   - Reference services by their discovery names (e.g., `http://my-backend-service:8081`)

5. **Minimal Changes Required**:
   - Most scripts work as-is
   - Update ECR repository names in `setup-ecr.sh`
   - Modify test endpoints in `test_services.sh`

### Example Use Cases:
- Microservices with REST APIs
- Web application with backend API
- Data processing pipeline with worker services
- Any containerized client-server architecture

## Lessons Learned

### Environment Variable Handling
- Spring Boot property placeholders (`${property.name}`) don't automatically map to environment variables
- Must use `${ENV_VAR_NAME}` directly for environment variable injection in Spring configuration

### Service Discovery Best Practices
- Within the same ECS Service Connect namespace, use short discovery names without namespace suffix
- Example: `mcp-server` instead of `mcp-server.namespace`

### Container Image Considerations
- Spring Boot buildpack (Paketo) images are minimal and lack common debugging tools
- This affects health check implementation - use application endpoints instead of shell commands

### Debugging Distributed Systems
- Comprehensive startup logging is crucial for environment-specific troubleshooting
- Log environment variables, connection URLs, and configuration during initialization

### CloudFormation Architecture
- Splitting infrastructure into base and services stacks provides:
  - Faster iteration on service updates (5 min vs 60+ min)
  - Better separation of concerns
  - Easier debugging of deployment issues

### Deployment Sequencing
- Proper service dependencies prevent race conditions
- Consider startup delays or health checks for dependent services
- ECS Service Connect handles service discovery registration automatically

### Container Architecture Targeting
- Spring Boot's build-image goal defaults to building for the local machine's architecture
- On Apple Silicon Macs (ARM64), this creates images incompatible with ECS Fargate (AMD64)
- The build-push.sh script explicitly sets BP_BUILD_PLATFORM and BP_RUN_PLATFORM to "linux/amd64"
- Without this configuration, containers would fail to start on ECS with exec format errors

## Guide for LLMs: Customizing This Infrastructure

This section provides guidance for AI assistants helping users adapt this infrastructure for new projects.

### Quick Context Understanding

When analyzing this infrastructure for customization:

1. **Start with CLAUDE.md** - This file contains project-specific context and requirements
2. **Check the existing services** - Look at `client/` and `server/` directories to understand current implementation
3. **Review CloudFormation parameters** - Both `base.cfn` and `services.cfn` have configurable parameters at the top

### Key Files to Modify

For most customizations, focus on these files:

```
infra/
├── services.cfn          # Container definitions, environment variables
├── base.cfn             # Only if networking/security changes needed
├── build-push.sh        # Update image names and build commands
├── test_services.sh     # Update test endpoints and validation
└── setup-ecr.sh        # Update repository names
```

### Common Customization Patterns

#### 1. Different Port Requirements
- Update security groups in `base.cfn` (search for "SecurityGroup")
- Modify task definitions in `services.cfn` (search for "PortMappings")
- Update ALB target group in `base.cfn` (search for "TargetGroup")

#### 2. Environment Variables
- Add to task definitions in `services.cfn` under "Environment"
- Remember: Spring Boot uses `${ENV_VAR}` not `${property.name}` for env vars

#### 3. Resource Requirements
- Modify CPU/Memory in `services.cfn` task definitions
- Common combinations: 256/512, 512/1024, 1024/2048

#### 4. Adding New Services
- Copy existing service pattern in `services.cfn`
- Add new security group rules in `base.cfn` if needed
- Update Service Connect configuration for discovery

### Debugging Tips for LLMs

When users report deployment issues:

1. **First check**: `./infra/deploy.sh status` output
2. **Common issues**:
   - ECR authentication expired → run `setup-ecr.sh` again
   - Service won't start → check CloudWatch logs in AWS Console
   - Health checks failing → verify endpoint paths and ports
   - Service discovery failing → confirm Service Connect names

### Testing Modifications

Before full deployment:
1. Run `./infra/aws-checks.sh` to verify prerequisites
2. Test containers locally with `docker run` if possible
3. Deploy to services stack only first: `./infra/deploy.sh services`
4. Use `./infra/test_services.sh` to validate

### Preserving User Data

When modifying infrastructure:
- Base stack changes are disruptive (VPC, subnets, etc.)
- Services stack can be updated without data loss
- Always check for stateful resources before deletion

### Useful CloudFormation Patterns

For adding new resources, these patterns from the existing templates are helpful:

```yaml
# Service discovery reference
Environment:
  - Name: MY_SERVICE_URL
    Value: !Sub "http://my-service.${BaseStackName}:8080"

# Conditional resource creation
Condition: CreateResource
Resources:
  ConditionalResource:
    Type: AWS::...
    Condition: CreateResource

# Cross-stack references
!ImportValue 
  Fn::Sub: "${BaseStackName}-SecurityGroup"
```

### Questions to Ask Users

When helping with customization:
1. "What ports do your applications use?"
2. "Do the services need to communicate with each other?"
3. "What environment variables does your application need?"
4. "Are there any external services or databases to connect to?"
5. "What are the memory/CPU requirements?"

### Final Notes

- Always preserve the modular stack design (base + services)
- Keep helper scripts functional - they're key to user experience
- Document any significant changes in CLAUDE.md
- Test incrementally - deploy services first, then test, then proceed