# AWS AI ECS - Getting Started with AWS Bedrock on Amazon ECS

This repository serves as a comprehensive guide for developers looking to quickly get started with AWS Bedrock and deploy AI-powered applications to Amazon ECS (Elastic Container Service). It provides practical examples and templates that demonstrate best practices for containerizing and deploying AI workloads in AWS.

## Overview

The repository contains two example projects that showcase different approaches to building and deploying AI applications on AWS infrastructure:

### 1. Agent ECS Template
A foundational template project for deploying agent-based AI applications to AWS ECS. This project demonstrates:
- Client-server architecture patterns for AI agents
- Proper containerization of AI workloads
- Health monitoring and service management
- CloudFormation infrastructure as code

### 2. Agriculture Agent ECS
A practical implementation of an AI-powered weather and agricultural data agent system. This project features:
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

## Key Features

- 🚀 **Quick Start**: Get AI applications running on AWS ECS in minutes
- 🛠️ **Infrastructure as Code**: Complete CloudFormation templates for reproducible deployments
- 🐳 **Docker-First**: Containerized applications ready for cloud deployment
- 📊 **Monitoring**: Built-in health checks and CloudWatch logging integration
- 🔧 **Extensible**: Use as templates for your own AI projects

## Getting Started

1. Choose a project template that matches your use case
2. Navigate to the project directory and review its specific documentation
3. Follow the deployment scripts in the `infra/` directory
4. Monitor your deployment through AWS CloudWatch

Each subproject contains detailed documentation and deployment instructions specific to its use case.

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