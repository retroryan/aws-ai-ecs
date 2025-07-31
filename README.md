# AWS AI on ECS: From Manual Integration to Autonomous Agents

This repository demonstrates the evolution of AI application development on AWS, showcasing three architectures that represent different stages of AI sophistication. Each project deploys to AWS ECS with Bedrock integration, illustrating the progression from imperative programming to declarative, model-driven development.

## The Three Approaches

### 1. [Agent ECS Template](./agent-ecs-template): Direct Integration
A foundational Flask application that makes direct boto3 calls to AWS Bedrock. Users query domain specialists (aerospace, agriculture, etc.) through a client-server architecture. This approach requires manual orchestration of all API calls, response parsing, and error handling.

**Key Pattern**: Imperative programming where developers explicitly control every interaction with the AI model.

### 2. [Agriculture Agent ECS](./agriculture-agent-ecs): Graph-Based Orchestration  
A LangGraph implementation that introduces stateful, multi-step workflows with persistent memory. The agent autonomously selects and executes tools from MCP servers to answer weather and agricultural queries. Features include conversation checkpointing, time-travel debugging, and durable state management.

**Key Pattern**: Graph-based orchestration where developers define nodes and edges, but the framework handles execution flow and state transitions.

### 3. [Strands Weather Agent](./strands-weather-agent): Model-Driven Development
An AWS Strands implementation where the AI model itself drives the entire orchestration. Developers simply declare available tools and desired output schemas - the agent handles all planning, execution, and response formatting autonomously.

**Key Pattern**: Declarative programming where developers specify "what" they want, not "how" to achieve it.

## Architectural Comparison

| Aspect | Agent ECS Template | Agriculture Agent (LangGraph) | Strands Weather Agent |
|--------|-------------------|------------------------------|---------------------|
| **Orchestration** | Manual via code | Framework-managed graph | Model-driven autonomy |
| **Code Complexity** | High - explicit control flow | Medium - graph definition | Low - declarative schemas |
| **Tool Integration** | Direct function calls | MCP servers with adapters | Native MCP protocol |
| **State Management** | Stateless requests | Persistent checkpointer | In-memory sessions |
| **Developer Effort** | Write all logic | Define graph structure | Define tools & schemas |
| **Flexibility** | Complete control | Structured workflows | AI-determined paths |
| **Error Handling** | Manual implementation | Framework patterns | Model self-correction |
| **Best For** | Learning fundamentals | Production systems needing audit trails | Rapid prototyping & autonomous agents |

## Technical Architecture

All projects share common AWS infrastructure patterns:

```
User → ALB → ECS Service → AWS Bedrock
              ↓
         MCP Servers (for projects 2 & 3)
```

### MCP (Model Context Protocol) Integration
Projects 2 and 3 implement MCP servers as separate containerized microservices:
- **Distributed Architecture**: Tools run as independent services, not embedded functions
- **Dynamic Discovery**: Agents discover available tools at runtime
- **Protocol Standardization**: Same MCP servers work with both LangGraph and Strands

### Key Infrastructure Components
- **ECS Fargate**: Serverless container orchestration
- **Service Connect**: Internal service discovery
- **CloudFormation**: Infrastructure as code
- **IAM Roles**: Least-privilege Bedrock access

## Development Philosophy

This repository illustrates a fundamental shift in software development:

1. **Traditional** (Template): Developers write explicit instructions for every operation
2. **Transitional** (LangGraph): Developers define workflows, frameworks handle execution  
3. **Emergent** (Strands): Developers declare capabilities, AI determines implementation

The progression shows how AI is moving from being a tool we control to becoming an autonomous problem-solver that we guide through constraints and objectives.

## Getting Started

Each project includes:
- Local development with Docker Compose
- Comprehensive test suites
- One-command AWS deployment
- Health monitoring and logging

Navigate to any project directory and follow its README for specific instructions. All projects support:

```bash
# Local development
./scripts/start_docker.sh
./scripts/test_docker.sh
./scripts/stop_docker.sh

# AWS deployment  
./infra/deploy.sh all
./infra/deploy.sh cleanup-all
```

## Model Support

All projects work with AWS Bedrock models that support tool/function calling:
- Amazon Nova (lite, pro)
- Anthropic Claude (Haiku, Sonnet)
- Meta Llama (70B, 405B)
- Cohere Command R+

## Prerequisites

- AWS Account with Bedrock access
- Docker and Docker Compose
- AWS CLI configured
- Python 3.11+ (for local development)

## Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [AWS Strands Documentation](https://github.com/awslabs/multi-agent-orchestrator)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Note**: These are demonstration projects. Production deployments require additional security, monitoring, and error handling considerations.