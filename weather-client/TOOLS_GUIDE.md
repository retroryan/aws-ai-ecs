# AWS Q Tools and MCP Server Management Guide

## Overview
AWS Q CLI supports Model Context Protocol (MCP) servers that provide additional tools and capabilities. These tools extend Q's functionality with specialized knowledge and operations.

## MCP Configuration

### Configuration Files
- **Workspace**: `.amazonq/mcp.json` (project-specific)
- **Global**: `~/.aws/amazonq/mcp.json` (user-wide)
- **Source**: `.mcp.json` (common configuration format)

### Available MCP Servers
Based on the current configuration, these servers are available:

- `aws-cdk` - AWS CDK documentation and best practices
- `aws-documentation` - General AWS documentation  
- `aws-cloudformation` - CloudFormation resources
- `aws-iam` - IAM policies and roles
- `aws-diagram` - AWS architecture diagrams
- `code-documentation` - Code documentation generation
- `strands` - Additional development tools

## MCP Management Commands

### List Servers
```bash
q mcp list
```
Shows all configured MCP servers in workspace and global scopes.

### Check Server Status
```bash
q mcp status --name <server-name>
```
Example: `q mcp status --name aws-cdk`

### Import Configuration
```bash
q mcp import --file <config-file> <scope>
```
- `<scope>`: `workspace` or `global`
- Example: `q mcp import --file .mcp.json workspace`

### Add New Server
```bash
q mcp add --name <server-name> --command <command> --args <args> <scope>
```

### Remove Server
```bash
q mcp remove --name <server-name> <scope>
```

## Setting Up MCP Servers

### From Existing .mcp.json
If you have a `.mcp.json` file with server configurations:

1. Import the configuration:
   ```bash
   q mcp import --file .mcp.json workspace
   ```

2. Verify import:
   ```bash
   q mcp list
   ```

3. Restart Q chat session to load servers:
   ```bash
   # Exit current session
   /quit
   
   # Start new session
   q chat
   ```

### Manual Server Addition
```bash
q mcp add --name aws-cdk \
  --command uvx \
  --args "awslabs.cdk-mcp-server" \
  workspace
```

## Using MCP Tools

Once MCP servers are loaded, tools become available with the naming pattern:
`<server-name>___<tool-name>`

Examples:
- `aws-cdk___search_constructs`
- `aws-documentation___search_docs`
- `aws-iam___generate_policy`

## Troubleshooting

### Servers Not Loading
1. Check if servers are properly configured: `q mcp list`
2. Verify server status: `q mcp status --name <server-name>`
3. Restart Q chat session to reload MCP servers
4. Check that required dependencies (like `uvx`) are installed

### Configuration Issues
- Ensure `.amazonq/mcp.json` exists in your workspace
- Verify JSON syntax in configuration files
- Check file permissions

## Security Considerations

- MCP servers can execute commands and access files
- Review server configurations before importing
- Use workspace scope for project-specific servers
- Use global scope only for trusted, commonly-used servers
- See: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-security.html

## Example .mcp.json Configuration

```json
{
  "mcpServers": {
    "aws-cdk": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      },
      "disabled": false,
      "autoApprove": []
    },
    "aws-documentation": {
      "command": "uvx",
      "args": ["awslabs.aws-documentation-mcp-server"]
    }
  }
}
```

## Best Practices

1. **Scope Management**: Use workspace scope for project-specific tools
2. **Regular Updates**: Keep MCP servers updated via their package managers
3. **Security**: Review and understand what each MCP server does
4. **Performance**: Disable unused servers to improve startup time
5. **Documentation**: Keep track of which servers provide which capabilities
