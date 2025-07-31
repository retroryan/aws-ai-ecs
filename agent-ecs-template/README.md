# Agent ECS Template

AWS Bedrock integration demo showcasing a client-server architecture on ECS. Users ask domain experts questions powered by AWS Bedrock AI models.

## Quick Start

### Prerequisites
- Docker & AWS CLI installed
- AWS account with Bedrock access enabled

### Local Development
```bash
# Setup and run
./scripts/setup.sh          # One-time AWS Bedrock setup
./scripts/start.sh          # Start services
./scripts/test.sh           # Test endpoints

# Development workflow
./scripts/logs.sh           # View logs
./scripts/rebuild.sh        # Rebuild containers
./scripts/stop.sh           # Stop services
```

### AWS Deployment
```bash
# First deployment
./infra/aws-checks.sh       # Verify prerequisites
./infra/deploy.sh all       # Deploy everything

# Updates
./infra/deploy.sh build-push && ./infra/deploy.sh update-services

# Get endpoint URL
./infra/test_services.sh    # Tests and shows URL
```

## Architecture

```
User → Client (8080) → Server (8081) → AWS Bedrock
         ↓                 ↓
      AWS ALB        Service Connect
```

### Key Components

| Component | Description | Tech Stack |
|-----------|-------------|------------|
| Client | User-facing API gateway | Flask, Python 3.12 |
| Server | Knowledge specialist service | Flask, boto3, Bedrock |
| Infrastructure | ECS Fargate deployment | CloudFormation, Docker |

### Project Structure
```
├── client/          # Flask client (port 8080)
├── server/          # Flask server with Bedrock (port 8081)
├── infra/           # AWS CloudFormation & deployment scripts
├── scripts/         # Local development scripts
└── tests/           # Integration tests
```

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/employees` | GET | List knowledge specialists |
| `/ask/{id}` | POST | Ask specialist a question |

**Example:**
```bash
curl -X POST http://localhost:8080/ask/1 \
  -H "Content-Type: application/json" \
  -d '{"question": "What is machine learning?"}'
```

## Key Commands

### Development
| Task | Command |
|------|---------|
| Run tests | `./scripts/run-tests.sh` |
| View logs | `./scripts/logs.sh` |
| Clean up | `./scripts/clean.sh` |

### Deployment
| Task | Command |
|------|---------|
| Deploy all | `./infra/deploy.sh all` |
| Update code | `./infra/deploy.sh build-push && ./infra/deploy.sh update-services` |
| Check status | `./infra/deploy.sh status` |
| Clean up | `./infra/deploy.sh cleanup-all` |

## Configuration

Environment variables (set automatically):
- `BEDROCK_MODEL_ID`: `amazon.nova-lite-v1:0` (default)
- `BEDROCK_REGION`: AWS region
- `SERVER_URL`: Server endpoint URL

## Troubleshooting

**ECR push fails:** Run `./infra/setup-ecr.sh` to refresh authentication  
**Services not starting:** Check CloudWatch logs at `/ecs/agent-ecs-*`  
**Bedrock errors:** Verify AWS account has Bedrock access enabled

## Resources

- [Detailed Documentation](CLAUDE.md) - Commands, architecture, patterns
- [Infrastructure Guide](INFRA_ARCHITECTURE.md) - CloudFormation details
- [AWS Bedrock Docs](https://docs.aws.amazon.com/bedrock/)

---

**Note:** Demo project without authentication. Not for production use.