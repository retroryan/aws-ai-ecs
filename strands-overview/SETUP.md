# Strands Weather Agent Setup Guide

## Prerequisites

- Python 3.11 or higher
- AWS account with Bedrock access enabled
- AWS credentials configured (`aws configure`)

## Quick Start

1. **Clone the repository** (if not already done)
   ```bash
   git clone <repository-url>
   cd strands-overview
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and set your preferred Bedrock model
   ```

4. **Start MCP servers**
   ```bash
   ./scripts/start_servers.sh
   ```

5. **Run the demo**
   ```bash
   python strands_demo/demo.py
   ```

## Environment Variables

Configure these in your `.env` file:

- `BEDROCK_MODEL_ID`: The AWS Bedrock model to use
  - Recommended: `us.anthropic.claude-3-7-sonnet-20250219-v1:0`
  - Alternative: `anthropic.claude-3-5-sonnet-20240620-v1:0`
- `BEDROCK_REGION`: AWS region (default: `us-west-2`)
- `BEDROCK_TEMPERATURE`: Model temperature 0-1 (default: `0`)
- `LOG_LEVEL`: Logging verbosity (default: `INFO`)

## Troubleshooting

### MCP Servers Not Starting
- Check if ports 8081-8083 are in use: `lsof -i :8081`
- Kill existing processes: `./scripts/stop_servers.sh`
- Check logs in `logs/` directory

### AWS Bedrock Access Denied
- Verify model access: [AWS Console](https://console.aws.amazon.com/bedrock/home)
- Request model access if needed
- Check AWS credentials: `aws sts get-caller-identity`

### Import Errors
- Ensure you're using Python 3.11+: `python --version`
- Create virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  pip install -r requirements.txt
  ```

### Testing Your Setup
Run the import test to verify everything is configured:
```bash
python test_imports.py
```

## Next Steps

1. Explore the demo script to understand basic usage
2. Check the weather agent implementation in `strands_demo/weather_agent_strands.py`
3. Try modifying queries in `demo.py`
4. Build your own agent using this as a template