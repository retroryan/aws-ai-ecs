# AI AGENT DEMOS - The New Era of Software Development with AI Services on AWS ECS + Bedrock

This repository demonstrates the future of software development: AI-powered applications running seamlessly on AWS ECS with Bedrock integration. Each project showcases how modern AI services can be containerized and deployed at scale, representing a paradigm shift in how we build intelligent applications.

## Overview

This repository contains four example projects that showcase the evolution of AI application development on AWS. Each project demonstrates running AI Services on ECS and Bedrock, highlighting different levels of sophistication in the new era of model-driven development.

*   **[Agent ECS Template](./agent-ecs-template)**: A foundational template using **direct `boto3` calls** to AWS Bedrock. It's a great starting point for understanding the basics of AI service integration in a client-server architecture.
*   **[Agriculture Agent ECS](./agriculture-agent-ecs)**: A practical, real-world example using **`LangGraph`** to orchestrate a multi-tool agent system. It introduces MCP servers for distributed tool handling.
*   **[Spring AI Agent ECS](./spring-ai-agent-ecs)**: A Java-based implementation using the **`Spring AI`** framework, showing how to build AI agents in a robust, enterprise-grade environment.
*   **[Strands Weather Agent](./strands-weather-agent)** ⭐ (Most Important Demo): The pinnacle demonstration of model-driven development using **`AWS Strands`**. This project represents a paradigm shift where the agent, not the developer, orchestrates complex workflows with minimal code.

## The Evolution of AI Orchestration

This repository showcases the transition from traditional programming to model-driven architectures where AI agents orchestrate complex workflows autonomously.

1.  **Manual Control: `boto3`** (`agent-ecs-template`)
    *   **What it is**: Low-level, direct SDK calls to the Bedrock API.
    *   **Developer Effort**: High. Requires manual implementation of all orchestration, state management, and tool integration logic.
    *   **Best for**: Simple, single-turn applications or learning the fundamentals of Bedrock.

2.  **Graph-Based Orchestration: `LangGraph`** (`agriculture-agent-ecs`)
    *   **What it is**: A framework for building stateful, multi-actor applications by defining workflows as a graph.
    *   **Developer Effort**: Medium. Reduces boilerplate but still requires the developer to explicitly define the workflow, nodes, and edges.
    *   **Best for**: Complex, multi-step processes where the flow is well-defined and needs to be explicitly managed.

3.  **Agent Framework: `Spring AI`** (`spring-ai-agent-ecs`)
    *   **What it is**: A comprehensive framework for building AI applications in Java, abstracting away low-level details.
    *   **Developer Effort**: Medium. Simplifies integration with models and tools within the Spring ecosystem.
    *   **Best for**: Enterprise Java developers looking to incorporate AI capabilities into new or existing Spring applications.

4.  **Model-Driven Orchestration: `AWS Strands`** (`strands-weather-agent`) ⭐
    *   **What it is**: A framework where the **AI model itself drives the orchestration**. The developer declares the desired output, and the agent figures out how to achieve it.
    *   **Developer Effort**: Low. Eliminates nearly all orchestration code. The developer focuses on defining tools and output schemas.
    *   **Best for**: Building sophisticated, autonomous agents that can dynamically plan and execute complex tasks with minimal human-written code.

### Why Strands Represents the Paradigm Shift

Traditional development required hundreds of lines of code to coordinate API calls, handle responses, and manage state. With Strands, you simply declare your desired output structure, and the agent orchestrates all the necessary steps internally. This is the new era of software development—where developers focus on business logic while AI handles the implementation details.

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

- 🚀 **Quick Start**: Get AI applications running on AWS ECS in minutes.
- 🤖 **AWS Bedrock Ready**: Pre-configured for Claude, Llama, and other Bedrock models.
- 🛠️ **Infrastructure as Code**: Complete CloudFormation templates for reproducible deployments.
- 🐳 **Docker-First**: Containerized applications ready for cloud deployment.
- 📊 **Monitoring**: Built-in health checks and CloudWatch logging integration.
- 🔧 **Extensible**: Use these templates as a starting point for your own AI projects.

## Project Highlights

- 🔌 **MCP Support**: All projects include `.mcp.json` configuration files for seamless integration with LLM providers like Amazon Q Developer and Claude Code.
- 📜 **Complete Development Scripts**: Each project contains comprehensive scripts for both local development and AWS deployment workflows.
- 🏃 **Local Development**: Run and test AI agents locally before deploying to AWS.
- ☁️ **AWS Deployment**: Production-ready deployment scripts with infrastructure automation.
- 🛡️ **Best Practices**: Security, logging, and monitoring built into every template.

## Getting Started

1.  **Explore the sub-projects** in this repository to find the one that best fits your use case and desired level of abstraction.
2.  **Navigate to the project's directory** and follow the detailed instructions in its local `README.md` file to run and deploy the application.

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

## Contributing

This repository is designed to be a learning resource. Feel free to:
- Use these templates as starting points for your projects
- Adapt the patterns to your specific use cases
- Share improvements and optimizations

## Learn More

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [AWS CloudFormation](https://aws.amazon.com/cloudformation/)

## Recommended MCP Server Tools for Development

Model Context Protocol (MCP) servers provide powerful integrations that enhance AI development workflows. Here are some recommended MCP servers that complement the AWS-focused tools in this repository:

### 1. **Context7 MCP Server** ([upstash/context7](https://github.com/upstash/context7))
**Purpose**: Provides up-to-date documentation and code examples for 50+ libraries and frameworks directly to LLMs.

**Key Features**:
- Access to current documentation for popular frameworks (Next.js, React, AWS services, etc.)
- Code snippets and API references
- Version-specific documentation
- Seamless integration with AI code editors

**Installation**: 
```bash
npx -y @upstash/context7-mcp
```

### 2. **AWS Labs MCP Servers** ([awslabs/mcp](https://github.com/awslabs/mcp))
**Purpose**: A comprehensive collection of AWS-specific MCP servers for infrastructure management and development.

**Notable Servers**:
- **AWS Cost Analysis**: Monitor and analyze AWS spending
- **AWS Documentation**: Search and access AWS docs
- **CloudFormation**: Manage infrastructure as code
- **IAM**: Handle AWS security and permissions
- **CDK**: AWS CDK best practices and guidance

### 3. **Strands Agents MCP Server** ([strands-agents/mcp-server](https://github.com/strands-agents/mcp))
**Purpose**: Enhanced agent orchestration and tool management for AWS Strands-based applications.

**Key Features**:
- Native integration with AWS Strands framework
- Automatic tool discovery and execution
- Built-in streaming and session management
- Simplified agent development

### Example MCP Configuration

Here's a comprehensive `.mcp.json` configuration that includes these recommended servers:

```json
{
  "mcpServers": {
    "context7": {
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "aws-cost-analysis": {
      "command": "uvx",
      "args": ["awslabs.cost-analysis-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR",
        "AWS_PROFILE": "your-aws-profile"
      }
    },
    "aws-documentation": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    },
    "strands": {
      "command": "uvx",
      "args": ["strands-agents-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "INFO"
      }
    },
    "langfuse": {
      "command": "node",
      "args": ["/path/to/mcp-server-langfuse/build/index.js"],
      "env": {
        "LANGFUSE_PUBLIC_KEY": "your-public-key",
        "LANGFUSE_SECRET_KEY": "your-secret-key",
        "LANGFUSE_BASEURL": "https://cloud.langfuse.com"
      }
    }
  }
}
```

### Usage Tips

1. **Project-Specific Configuration**: Place `.mcp.json` in your project root for project-specific MCP servers
2. **Global Configuration**: Use your AI editor's global config for commonly used servers
3. **Environment Variables**: Store sensitive credentials in environment variables
4. **Logging Levels**: Adjust `FASTMCP_LOG_LEVEL` based on your needs:
   - `ERROR`: Production use
   - `INFO`: Development
   - `DEBUG`: Troubleshooting

For a real-world example, see the [strands-weather-agent/.mcp.json](./strands-weather-agent/.mcp.json) configuration that demonstrates how these servers work together in a production application.