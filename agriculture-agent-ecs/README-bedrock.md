# Model-Agnostic Weather Agent with AWS Bedrock

This project demonstrates model-agnostic AI using LangChain's `init_chat_model` utility with AWS Bedrock. The agent requires AWS Bedrock configuration and supports multiple foundation models through simple environment variable changes.

## Quick Start with AWS Bedrock

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Auto-Configure with Setup Script

Run the provided setup script to automatically detect your AWS configuration and available Bedrock models:

```bash
./aws-setup.sh
```

This script will:
- Check your AWS CLI installation and credentials
- Detect your AWS profile and region
- Find all available Bedrock models in your account
- Generate a `bedrock.env` file with your available models
- Provide instructions for any missing setup

If successful, copy the generated configuration:
```bash
cp bedrock.env .env
```

### 3. Manual Configuration (Alternative)

If you prefer to configure manually, copy `.env.example` to `.env` and configure:

```bash
# Required: Choose a Bedrock model
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
BEDROCK_REGION=us-west-2
BEDROCK_TEMPERATURE=0

# AWS Credentials (if not using IAM role)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
```

**Note:** `BEDROCK_MODEL_ID` is required. The application will exit with an error if not set.

### 3. Available Bedrock Models

You can use any of these models by setting `BEDROCK_MODEL_ID`:

- **Claude Models:**
  - `anthropic.claude-3-5-sonnet-20240620-v1:0` (Recommended)
  - `anthropic.claude-3-haiku-20240307-v1:0` (Fast & cost-effective)
  - `anthropic.claude-3-opus-20240229-v1:0` (Most capable)

- **Other Models:**
  - `meta.llama3-70b-instruct-v1:0`
  - `cohere.command-r-plus-v1:0`
  - `mistral.mistral-large-2407-v1:0`

### 4. Run the Application

```bash
# Start MCP servers
./start_servers.sh

# Run the main application
python main.py
```

If `BEDROCK_MODEL_ID` is not set, the application will display an error message and exit.

## AWS Credentials

### Local Development
Use one of these methods:
1. Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env`
2. Use AWS CLI profiles: `aws configure`
3. Use IAM roles (if running on EC2/ECS)

### ECS Deployment
The application automatically uses the ECS task IAM role. No credentials needed in environment variables.

## Testing Different Models

Compare model performance by switching the `BEDROCK_MODEL_ID`:

```bash
# Test with Claude 3.5 Sonnet
export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20240620-v1:0"
python main.py

# Test with Claude 3 Haiku (faster, cheaper)
export BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
python main.py

# Test with Llama 3
export BEDROCK_MODEL_ID="meta.llama3-70b-instruct-v1:0"
python main.py
```

## Troubleshooting

### Model Not Available Error
Ensure the model is enabled in your AWS Bedrock console for the specified region.

### Authentication Errors
Verify your AWS credentials and that your IAM user/role has Bedrock permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": "*"
        }
    ]
}
```

### Region Issues
Make sure the model is available in your selected region. Check the [AWS Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html) for model availability.

## Architecture

The application uses:
- **LangChain's `init_chat_model`**: Provides a unified interface for different LLM providers
- **AWS Bedrock Converse API**: Offers consistent tool calling across different foundation models
- **Model-agnostic design**: Switch between models by changing a single environment variable

This demonstrates how modern AI applications can be built to work with multiple models without code changes.