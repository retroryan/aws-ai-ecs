# Complete Deployment Guide: Hello World Lambda with Function URL

This guide covers the complete workflow from local development to AWS deployment using CDK with security best practices.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development & Testing](#local-development--testing)
3. [Infrastructure Setup](#infrastructure-setup)
4. [AWS Deployment](#aws-deployment)
5. [Testing & Validation](#testing--validation)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Required Software

```bash
# 1. Install Node.js (for CDK CLI)
# Download from: https://nodejs.org/

# 2. Install AWS CDK CLI
npm install -g aws-cdk

# 3. Install AWS CLI
# Download from: https://aws.amazon.com/cli/

# 4. Install Python 3.11+
# Download from: https://python.org/

# 5. Install Docker
# Download from: https://docker.com/
```

### AWS Account Setup

```bash
# 1. Configure AWS credentials
aws configure
# Enter your Access Key ID, Secret Access Key, Region, and Output format

# 2. Verify credentials
aws sts get-caller-identity

# 3. Ensure you have necessary permissions:
# - Lambda: CreateFunction, UpdateFunction, DeleteFunction
# - IAM: CreateRole, AttachRolePolicy, PassRole
# - CloudFormation: CreateStack, UpdateStack, DeleteStack
# - CloudWatch: CreateLogGroup, PutMetricAlarm
```

## 🏠 Local Development & Testing

### Step 1: Setup Local Environment

```bash
# Navigate to project directory
cd /Users/ryanknight/projects/aws/aws-ai-ecs/weather-client

# Verify Lambda code exists
ls -la weather_lambda/
# Should see: lambda_function.py, requirements.txt, Dockerfile, etc.
```

### Step 2: Local Testing with Docker

```bash
# Navigate to Lambda directory
cd weather_lambda

# Run local tests
./test_lambda_local.sh

# Expected output:
# 🚀 Starting Lambda local testing...
# 🔨 Building Docker image...
# 🐳 Starting Lambda container on port 9000...
# ⏳ Waiting for Lambda to be ready...
# 🧪 Testing: Health check
# ✅ Success!
# ... (more test results)
```

### Step 3: Manual Local Testing (Optional)

While the container is running from the previous step:

```bash
# In a new terminal, test endpoints manually
# Health check
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"requestContext":{"http":{"method":"GET","path":"/health"}}}'

# Hello World
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{"requestContext":{"http":{"method":"GET","path":"/hello"}},"queryStringParameters":{"name":"LocalTest"}}'
```

## 🏗️ Infrastructure Setup

### Step 1: Navigate to Infrastructure Directory

```bash
cd infra
ls -la
# Should see: app.py, app_with_nag.py, deploy.py, stacks/, requirements.txt, etc.
```

### Step 2: Review CDK Configuration

```bash
# View CDK configuration
cat cdk.json

# View stack definition
cat stacks/lambda_stack.py

# View deployment script
cat deploy.py
```

## 🚀 AWS Deployment

### Option 1: Automated Deployment (Recommended)

```bash
# Development environment deployment
./deploy.py --environment dev --region us-east-1

# The script will automatically:
# 1. ✅ Setup Python virtual environment
# 2. ✅ Install dependencies
# 3. ✅ Validate AWS credentials
# 4. ✅ Bootstrap CDK (if needed)
# 5. ✅ Validate Lambda code
# 6. ✅ Synthesize CDK stack with security checks
# 7. ✅ Deploy to AWS
# 8. ✅ Run post-deployment tests
```

### Option 2: Manual Deployment

```bash
# 1. Setup Python environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export CDK_DEFAULT_REGION=us-east-1
export ENVIRONMENT=dev

# 4. Bootstrap CDK (first time only)
cdk bootstrap

# 5. Synthesize and review
cdk synth HelloWorldLambdaStack-dev --app "python3 app_with_nag.py"

# 6. Deploy
cdk deploy HelloWorldLambdaStack-dev --app "python3 app_with_nag.py"
```

### Production Deployment

```bash
# Production deployment with additional security
./deploy.py --environment prod --region us-east-1

# Key differences in production:
# - AWS_IAM auth type (requires authentication)
# - Restricted CORS origins
# - Longer log retention
# - Resource retention policies
```

## ✅ Testing & Validation

### Step 1: Verify Deployment

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name HelloWorldLambdaStack-dev \
  --query "Stacks[0].StackStatus"

# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name HelloWorldLambdaStack-dev \
  --query "Stacks[0].Outputs"
```

### Step 2: Test Function URL

```bash
# Extract Function URL from outputs (replace with your actual URL)
FUNCTION_URL="https://your-unique-id.lambda-url.us-east-1.on.aws/"

# Test health endpoint
curl "${FUNCTION_URL}health"

# Expected response:
# {
#   "status": "healthy",
#   "message": "Lambda function is running"
# }

# Test hello endpoint
curl "${FUNCTION_URL}hello?name=AWSDeployment"

# Test POST endpoint
curl -X POST "${FUNCTION_URL}hello" \
  -H "Content-Type: application/json" \
  -d '{"name": "CDK User"}'
```

### Step 3: Automated Testing

```bash
# Run automated tests against deployed function
./deploy.py --test-only --environment dev
```

## 📊 Monitoring & Maintenance

### CloudWatch Monitoring

```bash
# View Lambda logs
aws logs tail /aws/lambda/hello-world-lambda-dev --follow

# View CloudWatch alarms
aws cloudwatch describe-alarms \
  --alarm-names "hello-world-lambda-errors-dev" \
               "hello-world-lambda-duration-dev" \
               "hello-world-lambda-throttles-dev"

# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=hello-world-lambda-dev \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### Cost Monitoring

```bash
# View Lambda costs (requires Cost Explorer API access)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

## 🔄 Updates & Maintenance

### Code Updates

```bash
# 1. Update Lambda code in weather_lambda/lambda_function.py
# 2. Test locally
cd weather_lambda
./test_lambda_local.sh

# 3. Deploy updates
cd ../infra
./deploy.py --environment dev
```

### Infrastructure Updates

```bash
# 1. Modify stacks/lambda_stack.py
# 2. Review changes
cdk diff HelloWorldLambdaStack-dev --app "python3 app_with_nag.py"

# 3. Deploy changes
./deploy.py --environment dev
```

### Security Updates

```bash
# 1. Update dependencies
pip install --upgrade -r requirements.txt

# 2. Run security validation
cdk synth HelloWorldLambdaStack-dev --app "python3 app_with_nag.py"

# 3. Review CDK Nag findings and address any new issues
```

## 🗑️ Cleanup

### Destroy Development Stack

```bash
# Automated cleanup
./deploy.py --environment dev --destroy

# Manual cleanup
cdk destroy HelloWorldLambdaStack-dev --app "python3 app_with_nag.py"
```

### Complete Cleanup

```bash
# 1. Destroy all stacks
./deploy.py --environment dev --destroy

# 2. Clean up local files
rm -rf .venv cdk.out

# 3. Remove Docker images (optional)
docker rmi hello-world-lambda
```

## 🔍 Troubleshooting

### Common Issues & Solutions

#### 1. CDK Bootstrap Required
```bash
Error: Need to perform AWS CDK bootstrap

Solution:
cdk bootstrap aws://YOUR-ACCOUNT-ID/YOUR-REGION
```

#### 2. AWS Credentials Not Found
```bash
Error: Unable to locate credentials

Solutions:
# Option 1: Configure AWS CLI
aws configure

# Option 2: Use environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1

# Option 3: Use AWS profile
export AWS_PROFILE=your-profile
```

#### 3. Lambda Code Not Found
```bash
Error: Cannot find asset at ../weather_lambda

Solution:
# Ensure you're in the infra directory and Lambda code exists
cd infra
ls -la ../weather_lambda/lambda_function.py
```

#### 4. CDK Nag Violations
```bash
Error: AwsSolutions-XXX: Security violation

Solutions:
# Review the specific rule
./deploy.py --help  # Check CDK Nag documentation

# Add suppression with justification (if appropriate)
# Edit app_with_nag.py to add suppression

# Skip CDK Nag for testing (not recommended for production)
./deploy.py --skip-nag --environment dev
```

#### 5. Function URL Not Working
```bash
Error: 403 Forbidden or CORS errors

Solutions:
# Check auth type configuration
aws lambda get-function-url-config --function-name hello-world-lambda-dev

# For AWS_IAM auth type, ensure proper permissions
# For NONE auth type, check resource-based policy

# Verify CORS configuration
# Check browser developer tools for CORS errors
```

### Debug Commands

```bash
# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name HelloWorldLambdaStack-dev

# View Lambda function configuration
aws lambda get-function --function-name hello-world-lambda-dev

# View Lambda function logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/hello-world-lambda"

# Test Lambda function directly (bypass Function URL)
aws lambda invoke \
  --function-name hello-world-lambda-dev \
  --payload '{"requestContext":{"http":{"method":"GET","path":"/health"}}}' \
  response.json && cat response.json
```

## 📞 Support & Resources

### Documentation
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK Nag Rules](https://github.com/cdklabs/cdk-nag)

### Community
- [AWS CDK GitHub](https://github.com/aws/aws-cdk)
- [AWS Developer Forums](https://forums.aws.amazon.com/)
- [Stack Overflow - AWS CDK](https://stackoverflow.com/questions/tagged/aws-cdk)

### AWS Support
- [AWS Support Center](https://console.aws.amazon.com/support/)
- [AWS Trusted Advisor](https://console.aws.amazon.com/trustedadvisor/)

---

## 🎉 Success Checklist

After completing this guide, you should have:

- ✅ **Local Development**: Lambda function running and tested locally
- ✅ **Infrastructure**: CDK stack deployed with security best practices
- ✅ **Function URL**: HTTP endpoint accessible and working
- ✅ **Monitoring**: CloudWatch logs and alarms configured
- ✅ **Security**: CDK Nag validation passed
- ✅ **Testing**: Automated and manual tests passing
- ✅ **Documentation**: Complete understanding of the deployment

Your Hello World Lambda function is now production-ready and following AWS best practices!
