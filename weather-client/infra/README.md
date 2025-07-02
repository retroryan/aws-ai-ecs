# Weather Client Lambda Infrastructure

AWS CDK infrastructure for deploying a Lambda function with Function URL - a simple Hello World service with health checks.

## Prerequisites

- Python 3.11+
- AWS CLI configured with credentials
- AWS CDK v2 (`npm install -g aws-cdk`)

## Quick Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Validate environment
./validate-setup.sh

# Deploy to dev environment
./deploy.py --environment dev
```

## Deploy Commands

```bash
# Deploy with approval prompt
./deploy.py --environment dev

# Deploy without approval prompt
./deploy.py --environment dev --auto-approve

# Destroy stack
./deploy.py --environment dev --destroy
```

## Test Endpoints

After deployment, test the Lambda function:

```bash
# Get the function URL from CloudFormation outputs
FUNCTION_URL=$(aws cloudformation describe-stacks \
  --stack-name HelloWorldLambdaStack-dev \
  --query "Stacks[0].Outputs[?OutputKey=='FunctionUrl'].OutputValue" \
  --output text)

# Test hello endpoint
curl "${FUNCTION_URL}hello?name=CDK"

# Test health check
curl "${FUNCTION_URL}health"

# Test POST request
curl -X POST "${FUNCTION_URL}hello" \
  -H "Content-Type: application/json" \
  -d '{"name": "CDK User"}'
```