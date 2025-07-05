# AWS AI ECS Project Overview

This is the parent project containing multiple subprojects that demonstrate how to work with common AI frameworks and deploy them to AWS ECS.

## Project Structure

### Current Subprojects

1. **agent-ecs-template**: A template project for deploying agent-based applications to AWS ECS with client-server architecture
2. **strands-weather-agent**: A weather and agricultural data agent system using MCP (Model Context Protocol) servers, AWS Strands, and Ollama for local LLM inference
3. **agriculture-agent-ecs**: A LangGraph-based weather and agricultural data agent with MCP server integration
4. **spring-ai-agent-ecs**: A Java/Spring-based MCP agent implementation using Spring AI framework  
5. **strands-metrics-guide**: Documentation and guidance for AWS Strands metrics and monitoring

## Common Patterns

- All projects follow AWS ECS deployment patterns
- CloudFormation templates for infrastructure as code
- Docker-based containerization
- Health check endpoints for service monitoring
- Structured logging for debugging and monitoring

## Development Guidelines

### When working with these projects:
- Check each subdirectory's CLAUDE.md for project-specific information
- Follow the existing deployment patterns using the infrastructure scripts
- Ensure proper error handling and logging
- Test locally with Docker before deploying to AWS ECS
- Use the provided deployment scripts in each project's infra/ directory

## Deployment

Each subproject contains its own deployment scripts and CloudFormation templates. Navigate to the specific project directory and refer to its documentation for deployment instructions.

## Testing

- Run lint and typecheck commands when available
- Test health endpoints after deployment
- Monitor CloudWatch logs for service health