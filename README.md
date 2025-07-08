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

## MCP (Model Context Protocol) Servers

Each project in this repository includes a `.mcp.json` configuration file that sets up various MCP servers for enhanced AI development capabilities. These servers extend AI capabilities by providing tools and resources that AI models can use during development with Claude Code or Amazon Q Developer.

For detailed setup instructions and available MCP servers, see the [MCP Servers Setup Guide](./MCP_SERVERS_SETUP.md).

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
- [MCP Servers Setup Guide](./MCP_SERVERS_SETUP.md) - Detailed guide for setting up MCP servers with Claude Code or Amazon Q Developer

