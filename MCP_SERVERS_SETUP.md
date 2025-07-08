# MCP (Model Context Protocol) Servers Setup Guide

This guide explains how to set up MCP servers for development with Claude Code or Amazon Q Developer. MCP servers extend AI capabilities by providing tools and resources that AI models can use during development.

## What are MCP Servers?

MCP servers are specialized microservices that AI agents can call to perform specific tasks. They enable AI development tools like Claude Code and Amazon Q Developer to access external capabilities through a standardized protocol.

## Available AWS MCP Servers

The projects in this repository leverage several AWS-focused MCP servers from the [awslabs/mcp](https://github.com/awslabs/mcp) repository:

### 1. **AWS Strands MCP Server** (`strands`)
- **Purpose**: Provides agent orchestration and tool management capabilities
- **Key Features**: 
  - Native MCP integration for building AI agents
  - Automatic tool discovery and execution
  - Built-in streaming and session management
- **Installation**: `uvx strands-agents-mcp-server`

### 2. **AWS Documentation MCP Server** (`aws-documentation`)
- **Purpose**: Access and search AWS documentation directly from AI agents
- **Key Features**:
  - `read_documentation`: Convert AWS docs to markdown
  - `search_documentation`: Search across all AWS documentation
  - `recommend`: Get related documentation recommendations
- **Installation**: `uvx awslabs.aws-documentation-mcp-server`

### 3. **AWS CloudFormation MCP Server** (`aws-cloudformation`)
- **Purpose**: Manage AWS CloudFormation stacks programmatically
- **Key Features**:
  - Create, update, and delete CloudFormation stacks
  - Validate templates
  - Query stack resources and outputs
- **Installation**: `uvx awslabs.cloudformation-mcp-server`

### 4. **AWS IAM MCP Server** (`aws-iam`)
- **Purpose**: Manage AWS IAM resources
- **Key Features**:
  - List, create, and manage IAM users
  - Handle roles and policies
  - Manage access keys
  - Simulate policy evaluations
- **Installation**: `uvx awslabs.iam-mcp-server`

### 5. **AWS CDK MCP Server** (`aws-cdk`)
- **Purpose**: Provide guidance on AWS CDK best practices
- **Key Features**:
  - CDK pattern recommendations
  - Infrastructure design validation
  - CDK Nag rule explanations
  - Solutions Constructs discovery
- **Installation**: `uvx awslabs.cdk-mcp-server`

### 6. **Code Documentation Generation MCP Server** (`code-documentation`)
- **Purpose**: Automatically generate comprehensive project documentation
- **Key Features**:
  - Extract project structure
  - Create documentation plans
  - Generate README files
  - API documentation generation
- **Installation**: `uvx awslabs.code-documentation-generation-mcp-server`

### 7. **AWS Diagram MCP Server** (`aws-diagram`)
- **Purpose**: Generate AWS architecture diagrams programmatically
- **Key Features**:
  - Create architecture diagrams using Python
  - Generate sequence and flow diagrams
  - Visualize AWS infrastructure
  - Export in various formats
- **Installation**: `uvx awslabs.diagram-mcp-server`

### 8. **AWS Cost Analysis MCP Server** (`aws-cost-analysis`)
- **Purpose**: Monitor and analyze AWS spending
- **Key Features**:
  - Cost breakdown by service
  - Budget tracking
  - Cost optimization recommendations
- **Installation**: `uvx awslabs.cost-analysis-mcp-server@latest`

## Additional Recommended MCP Servers

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

### 2. **Langfuse MCP Server**
**Purpose**: Integration with Langfuse for LLM observability and monitoring

**Configuration**: Requires Langfuse credentials and custom installation path

## How MCP Servers Work

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

## Setting Up MCP Servers for Development

### Prerequisites

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

### Configuration Options

#### Project-Specific Configuration
Place `.mcp.json` in your project root for project-specific MCP servers. This is ideal when different projects need different sets of tools.

#### Global Configuration
Use your AI editor's global configuration for commonly used servers across all projects.

### Example Comprehensive Configuration

Here's a comprehensive `.mcp.json` configuration that includes multiple servers:

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

## Best Practices

1. **Security**: Never expose MCP servers directly to the internet. They should only be accessible by your AI development tools.

2. **Logging**: Set appropriate log levels using `FASTMCP_LOG_LEVEL`:
   - `ERROR`: Production environments or when you want minimal output
   - `INFO`: Development to see what's happening
   - `DEBUG`: Troubleshooting issues

3. **Resource Management**: MCP servers are lightweight but should be monitored for resource usage in production development environments.

4. **Error Handling**: Implement proper error handling in your AI agents when calling MCP server tools.

5. **Environment Variables**: Store sensitive credentials in environment variables rather than hardcoding them in configuration files.

## Example Usage with AWS Strands

The Strands Weather Agent project demonstrates the power of MCP servers. See the comprehensive documentation in [strands-weather-agent/README-V2.md](./strands-weather-agent/README-V2.md) for a detailed example of how MCP servers enable AI agents to:

- Automatically discover and use weather forecast tools
- Query historical weather data
- Provide agricultural insights
- All with minimal orchestration code

The documentation showcases how AWS Strands reduces code complexity by 50% through intelligent agent-driven orchestration with MCP servers.

## Troubleshooting

### Common Issues

1. **MCP Server Not Found**: Ensure the server is installed and the command path is correct
2. **AWS Credentials Error**: Verify AWS credentials are properly configured
3. **Connection Timeouts**: Check network connectivity and firewall settings
4. **Tool Discovery Failures**: Increase log level to `DEBUG` to see detailed error messages

### Debugging Tips

1. Run MCP servers manually to test functionality
2. Check logs in your AI editor's output panel
3. Verify environment variables are properly set
4. Test with minimal configuration first, then add servers incrementally

For project-specific examples, see the `.mcp.json` files in each subproject directory.