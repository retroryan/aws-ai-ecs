# AWS Strands Weather Agent - Infrastructure

Deploy a sophisticated AI weather agent to AWS ECS with just a few commands. This demo showcases AWS Strands for agent orchestration, FastMCP for tool servers, and optional Langfuse telemetry integration.

## Quick Start

### Prerequisites

- Python 3.11+
- AWS CLI configured with credentials
- Docker installed and running
- AWS account with Bedrock access enabled

### Installation

```bash
# Clone the repository
git clone <your-repo>
cd strands-weather-agent

# Install dependencies
pip install -r infra/requirements.txt

# Setup AWS, validate environment, and update cloud.env
# This also creates ECR repositories if needed
python infra/commands/setup.py

# The configuration is automatically written to cloud.env
# Edit cloud.env to customize if needed
```

### Deploy Everything

```bash
# Deploy complete infrastructure
python infra/deploy.py all

# Check deployment status
python infra/status.py

# Test the deployed services
python infra/tests/test_services.py
```

## Main Commands

### `deploy.py` - Deploy Infrastructure

Deploy and manage your AWS infrastructure:

```bash
# Deploy everything (recommended for first time)
python deploy.py all

# Deploy only base infrastructure (VPC, ECS cluster, Load Balancer)
python deploy.py base

# Build and push Docker images
python deploy.py build

# Deploy services (requires base infrastructure)
python deploy.py services

# Update running services with new code
python deploy.py update-services
```

### `status.py` - Check Status

View detailed status of your deployment:

```bash
# Check all components
python status.py

# Example output:
# ✓ Base Infrastructure: DEPLOYED
# ✓ Services: RUNNING
# ✓ Health Check: PASSING
# ✓ Recent Errors: NONE
```

### `cleanup.py` - Clean Up Resources

Remove AWS resources when done:

```bash
# Remove everything (with confirmation)
python cleanup.py all

# Remove only CloudFormation stacks
python cleanup.py stacks

# Force cleanup without confirmation
python cleanup.py all --force
```

## Configuration

### Environment Variables (.env)

```bash
# Required
BEDROCK_MODEL_ID=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# Optional
AWS_REGION=us-east-1
BASE_STACK_NAME=strands-weather-agent-base
SERVICES_STACK_NAME=strands-weather-agent-services

# Langfuse Telemetry (optional)
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
LANGFUSE_HOST=https://us.cloud.langfuse.com
ENABLE_TELEMETRY=true
```

### Supported Bedrock Models

Use inference profiles (us. prefix) for cross-region redundancy:

- `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (Recommended)
- `us.anthropic.claude-3-5-haiku-20241022-v1:0` (Fast & economical)
- `us.meta.llama3-1-70b-instruct-v1:0` (Open source)

## Architecture

The deployment creates:

1. **Base Infrastructure**
   - VPC with public/private subnets
   - ECS cluster with Fargate
   - Application Load Balancer
   - CloudWatch log groups

2. **Services**
   - Weather Agent API (port 7777)
   - Unified Weather MCP Server (internal, port 7778)

3. **Networking**
   - Service Connect for internal communication
   - Public ALB for API access
   - Security groups with least privilege

## Additional Commands

Located in the `commands/` directory:

```bash
# Initial AWS setup, validation, and configuration
# This command now includes all validation checks
python commands/setup.py

# Skip validation if you want to regenerate bedrock.env only
python commands/setup.py --skip-validation

# Create ECR repositories
python commands/setup_ecr.py

# Build and push Docker images separately
python commands/build_push.py

# View CloudWatch logs from deployed services
python commands/logs.py --tail --service main

# Export logs to file
python commands/logs.py --export logs.txt --since 1h --filter ERROR
```

## Testing

### Service Integration Tests

```bash
# Test deployed services (after deployment)
python tests/test_services.py

# Run with verbose output
python tests/test_services.py --verbose

# Test with custom API URL (for local testing)
python tests/test_services.py --api-url http://localhost:7777

# Additional options
python tests/test_services.py --fail-fast      # Stop on first failure
python tests/test_services.py --skip-langfuse  # Skip telemetry tests
python tests/test_services.py --region us-east-1  # Override AWS region
```

### Test Configuration

Tests use the same `.env` file as the main infrastructure. Additional test-specific settings:

```bash
# Test behavior
TEST_VERBOSE=true           # Enable verbose output by default
TEST_FAIL_FAST=true        # Stop on first failure
TEST_SKIP_LANGFUSE=true    # Skip Langfuse tests

# Timeouts
TEST_HEALTH_TIMEOUT=10      # Health check timeout (seconds)
TEST_QUERY_TIMEOUT=30       # Query timeout (seconds)
TEST_STARTUP_WAIT=60        # Service startup wait (seconds)

# Override API URL for local testing
API_URL=http://localhost:7777
```

## Demonstrations

Run interactive demos to see key features in action:

```bash
# Interactive demo menu
python demos.py

# Run specific demo directly
python demos.py --telemetry
python demos.py --multi-turn

# Override API URL for demos
python demos.py --api-url http://custom-url
```

Available demos:
- **Telemetry Demo**: Showcases Langfuse telemetry integration and metrics
- **Multi-turn Demo**: Demonstrates stateful conversations with session persistence

## Troubleshooting

### Common Issues

1. **Bedrock Model Access**
   ```bash
   # Check available models and validate setup
   python commands/setup.py
   
   # Test model access during setup
   python commands/setup.py --test-model
   
   # Request model access if needed
   # Visit: https://console.aws.amazon.com/bedrock/home#/modelaccess
   ```

2. **Service Health Issues**
   ```bash
   # Check service status
   python status.py
   
   # Test deployed services with detailed output
   python tests/integration/test_services.py
   
   # View and tail ECS service logs
   python commands/logs.py --tail --service main
   
   # View logs with filtering
   python commands/logs.py --filter ERROR --since 1h
   ```

3. **Build Failures**
   ```bash
   # Ensure ECR repositories exist
   python commands/setup_ecr.py
   
   # Build and push images with proper authentication
   python commands/build_push.py
   ```

## Project Structure

```
infra/
├── deploy.py              # Main deployment script
├── status.py              # Status checker
├── cleanup.py             # Resource cleanup
├── demos.py               # Interactive demo menu
├── requirements.txt       # Python dependencies
├── .env.example          # Example configuration
│
├── infrastructure/       # Core modules
│   ├── config.py        # Configuration management
│   ├── aws/            # AWS service integrations
│   ├── docker/         # Docker operations
│   └── utils/          # Utilities
│
├── commands/           # Additional tools
│   ├── setup.py        # AWS setup, validation, and configuration
│   ├── logs.py         # CloudWatch logs viewer
│   └── ...            # Other command scripts
│
├── tests/             # Test scripts
│   ├── test_services.py    # Service integration tests
│   ├── config.py          # Test configuration
│   └── utils.py           # Shared test utilities
│
└── demos/             # Demonstration scripts
    ├── demo_telemetry.py   # Telemetry showcase
    └── multi-turn-demo.py  # Multi-turn conversations
```

## Cost Considerations

This demo uses:
- Fargate Spot for cost optimization
- Minimal resource allocations
- No NAT Gateway (public subnets only)

Estimated cost: ~$50-100/month if running continuously

## Security Notes

For production use, consider:
- Private subnets with NAT Gateway
- Secrets Manager for credentials
- WAF for API protection
- VPC endpoints for AWS services

## Support

For issues or questions:
1. Check `python status.py` output
2. Review CloudWatch logs
3. See troubleshooting guide above
4. Open an issue on GitHub