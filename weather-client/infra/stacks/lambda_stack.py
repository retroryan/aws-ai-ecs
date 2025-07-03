"""
AWS CDK Stack for Hello World Lambda Function with Function URL
Following AWS security best practices and Well-Architected principles
"""

import os
from typing import Dict, Any
from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_sqs as sqs,
)


class HelloWorldLambdaStack(Stack):
    """
    CDK Stack for Hello World Lambda Function with Function URL
    
    This stack implements AWS security best practices including:
    - Least privilege IAM permissions
    - CloudWatch logging with retention policies
    - Function URL with proper CORS configuration
    - CloudWatch alarms for monitoring
    - Proper resource tagging
    """

    def __init__(
        self, 
        scope: Construct, 
        construct_id: str, 
        environment: str = "dev",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        self.env_name = environment  # Use env_name instead of environment
        
        # Create the Lambda function and DLQ
        self.lambda_function, self.dlq = self._create_lambda_function()
        
        # Create Function URL
        self.function_url = self._create_function_url()
        
        # Create CloudWatch alarms
        self._create_cloudwatch_alarms()
        
        # Create outputs
        self._create_outputs()

    def _create_lambda_function(self) -> tuple[_lambda.Function, sqs.Queue]:
        """Create the Lambda function with proper configuration"""
        
        # Create CloudWatch Log Group with retention policy
        log_group = logs.LogGroup(
            self,
            "HelloWorldLambdaLogGroup",
            log_group_name=f"/aws/lambda/hello-world-lambda-{self.env_name}",
            retention=logs.RetentionDays.ONE_WEEK if self.env_name == "dev" else logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY if self.env_name == "dev" else RemovalPolicy.RETAIN
        )
        
        # Create Dead Letter Queue for error handling
        dlq = sqs.Queue(
            self,
            "HelloWorldLambdaDLQ",
            queue_name=f"hello-world-lambda-dlq-{self.env_name}",
            retention_period=Duration.days(14),  # Retain failed messages for 14 days
            visibility_timeout=Duration.minutes(15),  # Allow time for investigation
            removal_policy=RemovalPolicy.DESTROY if self.env_name == "dev" else RemovalPolicy.RETAIN
        )
        
        # Create IAM role for Lambda with least privilege
        lambda_role = iam.Role(
            self,
            "HelloWorldLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description=f"IAM role for Hello World Lambda function - {self.env_name}",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "CloudWatchLogsPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            resources=[log_group.log_group_arn]
                        )
                    ]
                )
            }
        )
        
        # Create Lambda function
        lambda_function = _lambda.Function(
            self,
            "HelloWorldLambdaFunction",
            function_name=f"hello-world-lambda-{self.env_name}",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("../weather_lambda"),
            role=lambda_role,
            timeout=Duration.seconds(30),
            memory_size=128,  # Minimal memory for cost optimization
            retry_attempts=0,  # Disable automatic retries for Function URLs
            environment={
                "LOG_LEVEL": "INFO" if self.env_name == "prod" else "DEBUG",
                "ENVIRONMENT": self.env_name,
                "POWERTOOLS_SERVICE_NAME": "hello-world-lambda",
                "POWERTOOLS_METRICS_NAMESPACE": f"HelloWorld/{self.env_name}"
            },
            description=f"Hello World Lambda function with Function URL - {self.env_name}",
            log_group=log_group,
            # Architecture for cost optimization (ARM64 is cheaper)
            architecture=_lambda.Architecture.ARM_64,
            # Enable tracing for observability
            tracing=_lambda.Tracing.ACTIVE,
            # Add Dead Letter Queue for error handling
            dead_letter_queue_enabled=True,
            dead_letter_queue=dlq
        )
        
        return lambda_function, dlq

    def _create_function_url(self) -> _lambda.FunctionUrl:
        """Create Function URL with security best practices"""
        
        # Determine auth type based on environment
        auth_type = _lambda.FunctionUrlAuthType.AWS_IAM if self.env_name == "prod" else _lambda.FunctionUrlAuthType.NONE
        
        # Create Function URL
        function_url = self.lambda_function.add_function_url(
            auth_type=auth_type,
            cors=_lambda.FunctionUrlCorsOptions(
                # CORS configuration following security best practices
                allow_credentials=False,
                allowed_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"],
                allowed_methods=[_lambda.HttpMethod.GET, _lambda.HttpMethod.POST],
                # Restrict origins in production, allow all for development
                allowed_origins=["*"] if self.env_name == "dev" else [
                    # Add your specific domains here for production
                    # "https://yourdomain.com",
                    # "https://www.yourdomain.com"
                ],
                max_age=Duration.hours(1)
            )
        )
        
        # Add resource-based policy for public access (only if auth_type is NONE)
        if auth_type == _lambda.FunctionUrlAuthType.NONE:
            self.lambda_function.add_permission(
                "AllowPublicInvoke",
                principal=iam.ServicePrincipal("*"),
                action="lambda:InvokeFunctionUrl",
                function_url_auth_type=_lambda.FunctionUrlAuthType.NONE
            )
        
        return function_url

    def _create_cloudwatch_alarms(self) -> None:
        """Create CloudWatch alarms for monitoring"""
        
        # Error rate alarm
        error_alarm = cloudwatch.Alarm(
            self,
            "HelloWorldLambdaErrorAlarm",
            alarm_name=f"hello-world-lambda-errors-{self.env_name}",
            alarm_description=f"Lambda function error rate alarm - {self.env_name}",
            metric=self.lambda_function.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=5,  # Alert if more than 5 errors in 5 minutes
            evaluation_periods=2,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Duration alarm
        duration_alarm = cloudwatch.Alarm(
            self,
            "HelloWorldLambdaDurationAlarm",
            alarm_name=f"hello-world-lambda-duration-{self.env_name}",
            alarm_description=f"Lambda function duration alarm - {self.env_name}",
            metric=self.lambda_function.metric_duration(
                period=Duration.minutes(5),
                statistic="Average"
            ),
            threshold=10000,  # Alert if average duration > 10 seconds
            evaluation_periods=3,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )
        
        # Throttle alarm
        throttle_alarm = cloudwatch.Alarm(
            self,
            "HelloWorldLambdaThrottleAlarm",
            alarm_name=f"hello-world-lambda-throttles-{self.env_name}",
            alarm_description=f"Lambda function throttle alarm - {self.env_name}",
            metric=self.lambda_function.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum"
            ),
            threshold=1,  # Alert on any throttling
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING
        )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs"""
        
        CfnOutput(
            self,
            "LambdaFunctionName",
            value=self.lambda_function.function_name,
            description="Name of the Lambda function",
            export_name=f"HelloWorldLambdaFunctionName-{self.env_name}"
        )
        
        CfnOutput(
            self,
            "LambdaFunctionArn",
            value=self.lambda_function.function_arn,
            description="ARN of the Lambda function",
            export_name=f"HelloWorldLambdaFunctionArn-{self.env_name}"
        )
        
        CfnOutput(
            self,
            "FunctionUrl",
            value=self.function_url.url,
            description="Lambda Function URL endpoint",
            export_name=f"HelloWorldLambdaFunctionUrl-{self.env_name}"
        )
        
        CfnOutput(
            self,
            "HealthCheckUrl",
            value=f"{self.function_url.url}/health",
            description="Health check endpoint URL",
            export_name=f"HelloWorldLambdaHealthCheckUrl-{self.env_name}"
        )
        
        CfnOutput(
            self,
            "HelloWorldUrl",
            value=f"{self.function_url.url}hello?name=CDK",
            description="Hello World endpoint URL with example parameter",
            export_name=f"HelloWorldLambdaHelloUrl-{self.env_name}"
        )
        
        CfnOutput(
            self,
            "DeadLetterQueueUrl",
            value=self.dlq.queue_url,
            description="Dead Letter Queue URL for failed Lambda invocations",
            export_name=f"HelloWorldLambdaDLQUrl-{self.env_name}"
        )
