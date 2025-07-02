#!/usr/bin/env python3
"""
AWS CDK App for Hello World Lambda Function with Function URL
"""

import os
import aws_cdk as cdk
from constructs import Construct
from stacks.lambda_stack import HelloWorldLambdaStack

# Get environment variables for configuration
ENVIRONMENT = os.getenv('ENVIRONMENT', 'dev')
AWS_ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT')
AWS_REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')

app = cdk.App()

# Create the Lambda stack
lambda_stack = HelloWorldLambdaStack(
    app, 
    f"HelloWorldLambdaStack-{ENVIRONMENT}",
    env=cdk.Environment(
        account=AWS_ACCOUNT,
        region=AWS_REGION
    ),
    environment=ENVIRONMENT,
    description=f"Hello World Lambda Function with Function URL - {ENVIRONMENT} environment"
)

# Add tags to all resources
cdk.Tags.of(app).add("Project", "HelloWorldLambda")
cdk.Tags.of(app).add("Environment", ENVIRONMENT)
cdk.Tags.of(app).add("ManagedBy", "CDK")
cdk.Tags.of(app).add("Owner", "Development")

app.synth()
