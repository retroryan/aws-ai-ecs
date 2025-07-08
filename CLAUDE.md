# AWS AI ECS Project Overview

This is the parent project containing multiple subprojects that demonstrate how to work with common AI frameworks and deploy them to AWS ECS.

## Project Structure

### Current Subprojects

1. **agent-ecs-template**: A template project for deploying agent-based applications to AWS ECS with client-server architecture
2. **strands-ollama-weather-agent**: A weather and agricultural data agent system using MCP (Model Context Protocol) servers, AWS Strands, and Ollama for local LLM inference

## Recent Updates

### strands-weather-agent
- **Major Cleanup**: Significant refactoring and code organization improvements
- **MCP Integration**: Added MCP (Model Context Protocol) JSON configuration and external MCP server support
- **Structured Output**: Improved structured output handling and cleanup
- **Ollama Support**: Enhanced integration with Ollama for local LLM inference
- **Port Migration**: Updated service port configurations for better compatibility
- **Expert System**: Cleaned up expert code architecture for more modular design
- **Documentation**: Added comprehensive architecture analysis and integration success documentation

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