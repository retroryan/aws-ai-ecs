# AI AGENT DEMOS - The New Era of Software Development with AI Services on AWS ECS + Bedrock

This repository demonstrates the future of software development: AI-powered applications running seamlessly on AWS ECS with Bedrock integration. Each project showcases how modern AI services can be containerized and deployed at scale, representing a paradigm shift in how we build intelligent applications.

## Overview

The repository contains three example projects that showcase the evolution of AI application development on AWS infrastructure. Each project demonstrates running AI Services on ECS + Bedrock, highlighting different levels of sophistication in the new era of model-driven development:

### 1. [Python Strands Weather Agent](./strands-weather-agent) ⭐ (Most Important Demo)
**The pinnacle demonstration of model-driven development** - this project showcases the true power of the new era of software development. Built with AWS Strands, it represents a paradigm shift where agents orchestrate complex workflows with minimal code:
- **Model-driven architecture**: Define what you want, let the agent figure out how to get it
- **Agent orchestration**: The agent automatically manages tool selection, execution, and data flow
- **Native MCP support**: Seamless integration with distributed tool servers
- **Minimal code, maximum capability**: Complete weather analysis system in just a few lines
- **Type-safe structured outputs**: Automatic response validation and formatting
- Shows how AWS Strands eliminates hundreds of lines of orchestration code

### 2. [Agent ECS Template](./agent-ecs-template)
A foundational template project for deploying agent-based AI applications to AWS ECS. This project demonstrates:
- Client-server architecture patterns for AI agents
- **Direct AWS Bedrock integration using boto3** for foundational model access
- Proper containerization of AI workloads
- Health monitoring and service management
- CloudFormation infrastructure as code

### 3. [Agriculture Agent ECS](./agriculture-agent-ecs)
A practical implementation of an AI-powered weather and agricultural data agent system. This project features:
- **LangGraph integration with AWS Bedrock** for orchestrating complex AI workflows
- Integration with MCP (Model Context Protocol) servers
- Real-world use case for agricultural data analysis
- Weather data processing and insights
- Production-ready deployment patterns

## Why This Repository?

Getting started with AWS Bedrock and deploying AI applications to production can be challenging. This repository addresses common pain points by providing:

- **Ready-to-Deploy Templates**: Pre-configured CloudFormation templates and deployment scripts
- **Best Practices**: Structured logging, health checks, and error handling patterns
- **Container Optimization**: Docker configurations optimized for AI workloads
- **Cost-Effective Architecture**: ECS deployment patterns that scale efficiently

## The New Era: From Manual Coding to Model-Driven Development

This repository showcases the evolution of AI application development, demonstrating how we're transitioning from traditional programming to model-driven architectures where AI agents orchestrate complex workflows autonomously.

### AWS Bedrock Integration Approaches

1. **Direct boto3 Integration** (Agent ECS Template)
   - Low-level control over Bedrock API calls
   - Traditional approach requiring manual orchestration
   - Good for understanding fundamentals

2. **LangGraph Framework** (Agriculture Agent ECS)
   - Graph-based orchestration of AI workflows
   - Requires explicit workflow definition
   - Step up from manual coding but still requires orchestration logic

3. **AWS Strands** (Strands Weather Agent) ⭐
   - **The future of AI development**: Model-driven architecture
   - **Agent orchestrates everything**: No manual workflow coding needed
   - **Declarative programming**: Specify what you want, not how to get it
   - **Automatic tool discovery and execution**: The agent handles all complexity
   - **10x productivity gain**: Build in hours what used to take weeks

### Why Strands Represents the Paradigm Shift

Traditional development required hundreds of lines of code to coordinate API calls, handle responses, and manage state. With Strands, you simply declare your desired output structure, and the agent orchestrates all the necessary steps internally. This is the new era of software development - where developers focus on business logic while AI handles the implementation details.

**Example: The Power of Model-Driven Development**
```python
# Traditional: 200+ lines of orchestration code
# vs.
# Strands: Complete weather analysis in 4 lines
agent = Agent(name="weather-assistant", foundation_model_config={"model_id": model_id})
response = agent.structured_output(WeatherAnalysis, "Analyze weather for Chicago farming")
# The agent automatically orchestrates tool calls, data gathering, and response formatting
```

## Key Features

- 🚀 **Quick Start**: Get AI applications running on AWS ECS in minutes
- 🤖 **AWS Bedrock Ready**: Pre-configured for Claude, Llama, and other Bedrock models
- 🛠️ **Infrastructure as Code**: Complete CloudFormation templates for reproducible deployments
- 🐳 **Docker-First**: Containerized applications ready for cloud deployment
- 📊 **Monitoring**: Built-in health checks and CloudWatch logging integration
- 🔧 **Extensible**: Use as templates for your own AI projects

## Project Highlights

- 🔌 **MCP Support**: All projects include `.mcp.json` configuration files for seamless integration with LLM providers like Amazon Q Developer and Claude Code
- 📜 **Complete Development Scripts**: Each project contains comprehensive scripts for both local development and AWS deployment workflows
- 🏃 **Local Development**: Run and test AI agents locally before deploying to AWS
- ☁️ **AWS Deployment**: Production-ready deployment scripts with infrastructure automation
- 🛡️ **Best Practices**: Security, logging, and monitoring built into every template

## Getting Started

1. Choose a project template that matches your use case
2. Navigate to the project directory and review its specific documentation
3. Follow the deployment scripts in the `infra/` directory
4. Monitor your deployment through AWS CloudWatch

Each subproject contains detailed documentation and deployment instructions specific to its use case.

## MCP (Model Context Protocol) Servers Guide

### What are MCP Servers?

MCP servers are a powerful way to extend AI capabilities by providing tools and resources that AI models can use. Think of them as specialized microservices that AI agents can call to perform specific tasks. Each project in this repository includes a `.mcp.json` configuration file that sets up various MCP servers for enhanced functionality.

### Available MCP Servers

The projects in this repository leverage several AWS-focused MCP servers from the [awslabs/mcp](https://github.com/awslabs/mcp) repository:

#### 1. **AWS Strands MCP Server** (`strands`)
- **Purpose**: Provides agent orchestration and tool management capabilities
- **Key Features**: 
  - Native MCP integration for building AI agents
  - Automatic tool discovery and execution
  - Built-in streaming and session management
- **Installation**: `uvx strands-agents-mcp-server`

#### 2. **AWS Documentation MCP Server** (`aws-documentation`)
- **Purpose**: Access and search AWS documentation directly from AI agents
- **Key Features**:
  - `read_documentation`: Convert AWS docs to markdown
  - `search_documentation`: Search across all AWS documentation
  - `recommend`: Get related documentation recommendations
- **Installation**: `uvx awslabs.aws-documentation-mcp-server`

#### 3. **AWS CloudFormation MCP Server** (`aws-cloudformation`)
- **Purpose**: Manage AWS CloudFormation stacks programmatically
- **Key Features**:
  - Create, update, and delete CloudFormation stacks
  - Validate templates
  - Query stack resources and outputs
- **Installation**: `uvx awslabs.cloudformation-mcp-server`

#### 4. **AWS IAM MCP Server** (`aws-iam`)
- **Purpose**: Manage AWS IAM resources
- **Key Features**:
  - List, create, and manage IAM users
  - Handle roles and policies
  - Manage access keys
  - Simulate policy evaluations
- **Installation**: `uvx awslabs.iam-mcp-server`

#### 5. **AWS CDK MCP Server** (`aws-cdk`)
- **Purpose**: Provide guidance on AWS CDK best practices
- **Key Features**:
  - CDK pattern recommendations
  - Infrastructure design validation
  - CDK Nag rule explanations
  - Solutions Constructs discovery
- **Installation**: `uvx awslabs.cdk-mcp-server`

#### 6. **Code Documentation Generation MCP Server** (`code-documentation`)
- **Purpose**: Automatically generate comprehensive project documentation
- **Key Features**:
  - Extract project structure
  - Create documentation plans
  - Generate README files
  - API documentation generation
- **Installation**: `uvx awslabs.code-documentation-generation-mcp-server`

#### 7. **AWS Diagram MCP Server** (`aws-diagram`)
- **Purpose**: Generate AWS architecture diagrams programmatically
- **Key Features**:
  - Create architecture diagrams using Python
  - Generate sequence and flow diagrams
  - Visualize AWS infrastructure
  - Export in various formats
- **Installation**: `uvx awslabs.diagram-mcp-server`

### How MCP Servers Work

1. **Configuration**: Each project contains a `.mcp.json` file that defines which MCP servers to use:
```json
{
  "mcpServers": {
    "aws-documentation": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

2. **Automatic Loading**: When using tools like Claude Code or Amazon Q Developer, these MCP servers are automatically loaded and made available to the AI assistant.

3. **Tool Discovery**: AI agents can discover available tools from each MCP server and use them to accomplish tasks.

### Setting Up MCP Servers

1. **Install uvx** (if not already installed):
```bash
pip install uvx
```

2. **Configure AWS Credentials**: MCP servers that interact with AWS services need proper credentials:
```bash
aws configure
# or use environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2
```

3. **Test MCP Servers**: You can test individual servers:
```bash
uvx awslabs.aws-documentation-mcp-server
```

### Best Practices for MCP Servers

1. **Security**: Never expose MCP servers directly to the internet. They should only be accessible by your AI agents.

2. **Logging**: Set appropriate log levels using `FASTMCP_LOG_LEVEL`:
   - `ERROR`: Production environments
   - `INFO`: Development
   - `DEBUG`: Troubleshooting

3. **Resource Management**: MCP servers are lightweight but should be monitored for resource usage in production.

4. **Error Handling**: Implement proper error handling in your AI agents when calling MCP server tools.

### Example: Using MCP Servers with AWS Strands

The Strands Weather Agent project demonstrates the power of MCP servers. See the comprehensive documentation in [strands-weather-agent/README-V2.md](./strands-weather-agent/README-V2.md) for a detailed example of how MCP servers enable AI agents to:

- Automatically discover and use weather forecast tools
- Query historical weather data
- Provide agricultural insights
- All with minimal orchestration code

The documentation showcases how AWS Strands reduces code complexity by 50% through intelligent agent-driven orchestration with MCP servers.

## Prerequisites

- AWS Account with appropriate permissions
- Docker installed locally
- AWS CLI configured
- Basic understanding of ECS and CloudFormation

## Architecture

Both projects follow a similar architectural pattern:
- Containerized applications deployed to ECS
- Application Load Balancer for traffic distribution
- CloudWatch for logging and monitoring
- VPC with public/private subnet configuration
- Auto-scaling capabilities

## Contributing

This repository is designed to be a learning resource. Feel free to:
- Use these templates as starting points for your projects
- Adapt the patterns to your specific use cases
- Share improvements and optimizations

## Learn More

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [AWS CloudFormation](https://aws.amazon.com/cloudformation/)