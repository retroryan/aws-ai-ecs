# Spring AI Agent ECS Project

## Overview
This is a Spring Boot application that demonstrates an MCP (Model Context Protocol) Agent using Spring AI with AWS Bedrock. The project consists of a client-server architecture where both components run on AWS ECS behind an Application Load Balancer.

## Project Structure
- **client/**: Spring Boot MCP client that acts as a Bedrock agent with REST API
- **server/**: Spring Boot MCP server that provides agriculture expert skills data
- **infra.cfn**: CloudFormation template for AWS infrastructure

## Key Technologies
- Spring Boot 3.5.0
- Spring AI 1.0.0
- Kotlin 2.1.21
- Java 21
- AWS Bedrock (Nova Pro model)
- AWS ECS
- Docker

## Build Commands
```bash
# Run MCP Server locally
./mvnw -pl server spring-boot:run

# Run MCP Client/Agent locally
# Note: Spring Boot's run command runs in foreground mode and won't return to the shell prompt
# The application is running successfully even though it appears to "hang"
./mvnw -pl client spring-boot:run

# Build Docker images for AWS deployment (use infra/build-push.sh instead)
# NOTE: The commands below build for local architecture and won't work on ECS Fargate
# Use ./infra/build-push.sh which properly targets linux/amd64 architecture
export ECR_REPO=<your account id>.dkr.ecr.us-east-1.amazonaws.com
./mvnw -pl server spring-boot:build-image -Dspring-boot.build-image.imageName=$ECR_REPO/mcp-agent-spring-ai-server
./mvnw -pl client spring-boot:build-image -Dspring-boot.build-image.imageName=$ECR_REPO/mcp-agent-spring-ai-client
```

## Testing
```bash
# Local testing
curl -X POST --location "http://localhost:8011/inquire" \
    -H "Content-Type: application/json" \
    -d '{"question": "Get agriculture experts that have skills related to Crop Science"}'
```

## Environment Variables
- `SPRING_AGRICULTURE_EXPERTS_URL`: The URL of the Spring Agriculture Experts server (used by the client)

## Important Notes
- Requires AWS Bedrock access (Nova Pro model)
- Uses ECR for container registry
- Deployed with Rain CLI tool
- Client runs on port 8011, Server on port 8010
- Server Docker setup uses Spring Boot buildpacks for proper layering and JVM configuration
- When running locally with `mvnw spring-boot:run`, the application runs in foreground mode and won't return to shell prompt