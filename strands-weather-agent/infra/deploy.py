#!/usr/bin/env python3
"""
Simple AWS Deployment Script for Strands Weather Agent Demo
Demonstrates deploying an AI agent with Langfuse telemetry to AWS ECS
"""

import argparse
import os
import sys
import subprocess
import json
from pathlib import Path
import boto3
from dotenv import load_dotenv


class SimpleDeployment:
    """Simple deployment manager for AWS Strands demo"""
    
    def __init__(self, region="us-east-1"):
        self.region = region
        self.base_stack = "strands-weather-agent-base"
        self.services_stack = "strands-weather-agent-services"
        
        # AWS clients
        self.cfn = boto3.client("cloudformation", region_name=region)
        self.ssm = boto3.client("ssm", region_name=region)
        self.ecr = boto3.client("ecr", region_name=region)
        
    def run_command(self, cmd, capture=False):
        """Run a shell command"""
        print(f"Running: {cmd}")
        if capture:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout.strip()
        else:
            return subprocess.run(cmd, shell=True).returncode == 0
    
    def setup_ecr(self):
        """Create ECR repositories for Docker images"""
        print("\n📦 Setting up ECR repositories...")
        repos = ["main", "forecast", "historical", "agricultural"]
        
        for repo in repos:
            repo_name = f"strands-weather-agent-{repo}"
            try:
                self.ecr.create_repository(repositoryName=repo_name)
                print(f"✅ Created repository: {repo_name}")
            except self.ecr.exceptions.RepositoryAlreadyExistsException:
                print(f"✅ Repository exists: {repo_name}")
        
        # Authenticate Docker with ECR
        print("\n🔐 Authenticating Docker with ECR...")
        try:
            # Get account ID using STS
            sts = boto3.client('sts', region_name=self.region)
            account_id = sts.get_caller_identity()['Account']
            registry_url = f"{account_id}.dkr.ecr.{self.region}.amazonaws.com"
            
            # Get auth token
            auth_response = self.ecr.get_authorization_token()
            print(f"✅ ECR authentication configured for {registry_url}")
        except Exception as e:
            print(f"⚠️  ECR authentication note: {e}")
    
    def build_and_push(self):
        """Build and push Docker images"""
        print("\n🐳 Building and pushing Docker images...")
        script_path = Path(__file__).parent / "build-push.sh"
        if script_path.exists():
            self.run_command(f"bash {script_path}")
        else:
            print("⚠️  build-push.sh not found, skipping...")
    
    def setup_langfuse_credentials(self):
        """Store Langfuse credentials in Parameter Store if cloud.env exists"""
        cloud_env_path = Path(__file__).parent.parent / "cloud.env"
        
        if not cloud_env_path.exists():
            print("⚠️  cloud.env not found - telemetry will be disabled")
            return False
            
        print("\n🔐 Setting up Langfuse credentials...")
        load_dotenv(cloud_env_path)
        
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        
        if public_key and secret_key:
            try:
                self.ssm.put_parameter(
                    Name="/strands-weather-agent/langfuse/public-key",
                    Value=public_key,
                    Type="SecureString",
                    Overwrite=True
                )
                self.ssm.put_parameter(
                    Name="/strands-weather-agent/langfuse/secret-key",
                    Value=secret_key,
                    Type="SecureString",
                    Overwrite=True
                )
                print("✅ Langfuse credentials stored securely")
                return True
            except Exception as e:
                print(f"❌ Failed to store credentials: {e}")
        
        return False
    
    def deploy_stack(self, template_file, stack_name, parameters=None):
        """Deploy a CloudFormation stack using rain or AWS CLI"""
        print(f"\n☁️  Deploying {stack_name}...")
        
        # Check if rain is available
        if subprocess.run("which rain", shell=True, capture_output=True).returncode == 0:
            # Use rain for deployment
            cmd = f"rain deploy {template_file} {stack_name} --yes"
            if parameters:
                params_str = ",".join([f"{k}={v}" for k, v in parameters.items()])
                cmd += f" --params {params_str}"
            self.run_command(cmd)
        else:
            print("Rain CLI not found, using AWS CLI...")
            # Fallback to AWS CLI
            cmd = f"aws cloudformation deploy --template-file {template_file} --stack-name {stack_name}"
            if parameters:
                params_str = " ".join([f"ParameterKey={k},ParameterValue={v}" for k, v in parameters.items()])
                cmd += f" --parameter-overrides {params_str}"
            cmd += f" --capabilities CAPABILITY_IAM --region {self.region}"
            self.run_command(cmd)
    
    def deploy_base(self):
        """Deploy base infrastructure (VPC, ALB, ECS Cluster)"""
        template = Path(__file__).parent / "base.cfn"
        self.deploy_stack(template, self.base_stack)
    
    def deploy_services(self, enable_telemetry=True):
        """Deploy ECS services with optional telemetry"""
        template = Path(__file__).parent / "services.cfn"
        
        # Load bedrock configuration
        load_dotenv()
        
        params = {
            "BaseStackName": self.base_stack,
            "BedrockModelId": os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0"),
            "BedrockRegion": os.getenv("BEDROCK_REGION", self.region),
            "BedrockTemperature": os.getenv("BEDROCK_TEMPERATURE", "0"),
            "LogLevel": os.getenv("LOG_LEVEL", "INFO"),
            "EnableTelemetry": "true" if enable_telemetry else "false"
        }
        
        # Add Langfuse parameters if telemetry is enabled
        if enable_telemetry:
            cloud_env_path = Path(__file__).parent.parent / "cloud.env"
            if cloud_env_path.exists():
                load_dotenv(cloud_env_path)
                langfuse_host = os.getenv("LANGFUSE_HOST")
                if langfuse_host:
                    params["LangfuseHost"] = langfuse_host
                    params["TelemetryTags"] = os.getenv("TELEMETRY_TAGS", "production,aws-strands,weather-agent")
                    # Note: Public and Secret keys are handled via Parameter Store
        
        self.deploy_stack(template, self.services_stack, params)
    
    def get_status(self):
        """Show deployment status"""
        print("\n📊 Deployment Status")
        print("=" * 50)
        
        # Check base stack
        try:
            base_stack = self.cfn.describe_stacks(StackName=self.base_stack)["Stacks"][0]
            print(f"✅ Base Stack: {base_stack['StackStatus']}")
            
            # Get ALB URL
            for output in base_stack.get("Outputs", []):
                if output["OutputKey"] == "ALBDNSName":
                    print(f"\n🌐 Application URL: http://{output['OutputValue']}")
                    print(f"📚 API Docs: http://{output['OutputValue']}/docs")
                    break
        except:
            print("❌ Base Stack: Not deployed")
        
        # Check services stack
        try:
            services_stack = self.cfn.describe_stacks(StackName=self.services_stack)["Stacks"][0]
            print(f"✅ Services Stack: {services_stack['StackStatus']}")
            
            # Check if telemetry is enabled
            for param in services_stack.get("Parameters", []):
                if param["ParameterKey"] == "EnableTelemetry" and param["ParameterValue"] == "true":
                    print("✅ Langfuse Telemetry: Enabled")
                    break
        except:
            print("❌ Services Stack: Not deployed")
    
    def deploy_all(self, disable_telemetry=False):
        """Deploy everything"""
        print("🚀 Starting full deployment...")
        
        # Setup ECR
        self.setup_ecr()
        
        # Build and push images
        self.build_and_push()
        
        # Setup Langfuse if not disabled
        enable_telemetry = not disable_telemetry
        if enable_telemetry:
            enable_telemetry = self.setup_langfuse_credentials()
        
        # Deploy stacks
        self.deploy_base()
        self.deploy_services(enable_telemetry)
        
        # Show final status
        self.get_status()
        
        print("\n✨ Deployment complete! Test with:")
        print("   python3 infra/test_services.py")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Strands Weather Agent to AWS ECS"
    )
    parser.add_argument(
        "command",
        choices=["all", "base", "services", "status", "setup-ecr"],
        help="Deployment command"
    )
    parser.add_argument(
        "--disable-telemetry",
        action="store_true",
        help="Disable Langfuse telemetry"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region"
    )
    
    args = parser.parse_args()
    
    # Create deployment manager
    deployment = SimpleDeployment(args.region)
    
    # Execute command
    if args.command == "all":
        deployment.deploy_all(args.disable_telemetry)
    elif args.command == "base":
        deployment.deploy_base()
    elif args.command == "services":
        deployment.deploy_services(not args.disable_telemetry)
    elif args.command == "status":
        deployment.get_status()
    elif args.command == "setup-ecr":
        deployment.setup_ecr()


if __name__ == "__main__":
    main()