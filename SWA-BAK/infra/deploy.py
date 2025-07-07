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
import time
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
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
        
        # Load cloud.env first if it exists (for AWS deployments)
        cloud_env_path = Path(__file__).parent.parent / "cloud.env"
        if cloud_env_path.exists():
            print(f"📄 Loading configuration from cloud.env...")
            load_dotenv(cloud_env_path, override=True)
        else:
            # Fall back to regular .env
            load_dotenv()
        
        # Get Bedrock configuration (now from cloud.env if available)
        bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
        bedrock_region = os.getenv("BEDROCK_REGION", self.region)
        
        print(f"🤖 Using Bedrock model: {bedrock_model_id}")
        print(f"🌍 Bedrock region: {bedrock_region}")
        
        params = {
            "BaseStackName": self.base_stack,
            "BedrockModelId": bedrock_model_id,
            "BedrockRegion": bedrock_region,
            "BedrockTemperature": os.getenv("BEDROCK_TEMPERATURE", "0"),
            "LogLevel": os.getenv("LOG_LEVEL", "INFO"),
            "EnableTelemetry": "true" if enable_telemetry else "false"
        }
        
        # Load image tags from .image-tags file if it exists
        image_tags_file = Path(__file__).parent / ".image-tags"
        if image_tags_file.exists():
            print(f"📦 Loading image tags from {image_tags_file}")
            with open(image_tags_file) as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line:
                        key, value = line.split('=', 1)
                        if key == "MAIN_IMAGE_TAG":
                            params["MainImageTag"] = value
                            print(f"  Main image: {value}")
                        elif key == "FORECAST_IMAGE_TAG":
                            params["ForecastImageTag"] = value
                            print(f"  Forecast image: {value}")
                        elif key == "HISTORICAL_IMAGE_TAG":
                            params["HistoricalImageTag"] = value
                            print(f"  Historical image: {value}")
                        elif key == "AGRICULTURAL_IMAGE_TAG":
                            params["AgriculturalImageTag"] = value
                            print(f"  Agricultural image: {value}")
        else:
            print("⚠️ No .image-tags file found, using 'latest' tags")
            params.update({
                "MainImageTag": "latest",
                "ForecastImageTag": "latest",
                "HistoricalImageTag": "latest",
                "AgriculturalImageTag": "latest"
            })
        
        # Add Langfuse parameters if telemetry is enabled
        if enable_telemetry:
            langfuse_host = os.getenv("LANGFUSE_HOST")
            if langfuse_host:
                params["LangfuseHost"] = langfuse_host
                params["TelemetryTags"] = os.getenv("TELEMETRY_TAGS", "production,aws-strands,weather-agent")
                print(f"📊 Telemetry enabled with host: {langfuse_host}")
                # Note: Public and Secret keys are handled via Parameter Store
        
        self.deploy_stack(template, self.services_stack, params)
    
    def update_services(self, enable_telemetry=True):
        """Update services (redeploy)"""
        print("\n🔄 Updating services...")
        
        # Load cloud.env to ensure we have the latest configuration
        cloud_env_path = Path(__file__).parent.parent / "cloud.env"
        if cloud_env_path.exists():
            print(f"📄 Loading configuration from cloud.env...")
            load_dotenv(cloud_env_path, override=True)
        
        # Build and push new images first
        print("\n📦 Building and pushing updated Docker images...")
        self.build_and_push()
        
        # Then deploy the services with new images
        self.deploy_services(enable_telemetry)
        
        # Force ECS to use the new images by updating services
        print("\n🔄 Forcing ECS services to use new images...")
        self._force_ecs_update()
    
    def _force_ecs_update(self):
        """Force ECS services to pull new images by updating service"""
        try:
            ecs = boto3.client("ecs", region_name=self.region)
            
            # Get cluster name - it's always "strands-weather-agent"
            cluster_name = "strands-weather-agent"
            
            # List services in the cluster
            response = ecs.list_services(cluster=cluster_name)
            service_arns = response.get('serviceArns', [])
            
            for service_arn in service_arns:
                service_name = service_arn.split('/')[-1]
                print(f"  Updating service: {service_name}")
                
                # Force new deployment
                ecs.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    forceNewDeployment=True
                )
            
            if service_arns:
                print(f"✅ Forced update for {len(service_arns)} services")
            else:
                print("⚠️  No services found to update")
                
        except Exception as e:
            print(f"⚠️  Could not force ECS update: {e}")
            # Non-critical error, continue
    
    def cleanup_services(self):
        """Remove services stack only"""
        print(f"\n🗑️  Removing services stack: {self.services_stack}...")
        try:
            self.cfn.describe_stacks(StackName=self.services_stack)
            
            # Delete the stack
            self.cfn.delete_stack(StackName=self.services_stack)
            print("⏳ Waiting for stack deletion...")
            
            # Wait for deletion
            waiter = self.cfn.get_waiter('stack_delete_complete')
            waiter.wait(StackName=self.services_stack)
            print("✅ Services stack removed")
        except ClientError as e:
            if 'does not exist' in str(e):
                print("⚠️  Services stack not found")
            else:
                print(f"❌ Error: {e}")
    
    def cleanup_base(self):
        """Remove base infrastructure stack"""
        print(f"\n🗑️  Removing base stack: {self.base_stack}...")
        try:
            self.cfn.describe_stacks(StackName=self.base_stack)
            
            # Delete the stack
            self.cfn.delete_stack(StackName=self.base_stack)
            print("⏳ Waiting for stack deletion...")
            
            # Wait for deletion
            waiter = self.cfn.get_waiter('stack_delete_complete')
            waiter.wait(StackName=self.base_stack)
            print("✅ Base stack removed")
        except ClientError as e:
            if 'does not exist' in str(e):
                print("⚠️  Base stack not found")
            else:
                print(f"❌ Error: {e}")
    
    def cleanup_all(self):
        """Remove all infrastructure"""
        print("\n⚠️  WARNING: This will remove all infrastructure!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() == "yes":
            self.cleanup_services()
            self.cleanup_base()
            print("\n✅ All infrastructure removed")
        else:
            print("❌ Cleanup cancelled")
    
    def aws_checks(self):
        """Run AWS configuration checks"""
        print("\n🔍 Running AWS configuration checks...")
        
        # Check AWS identity
        try:
            sts = boto3.client('sts', region_name=self.region)
            identity = sts.get_caller_identity()
            print(f"✅ AWS Account: {identity['Account']}")
            print(f"✅ AWS User/Role: {identity['Arn']}")
        except Exception as e:
            print(f"❌ AWS credentials error: {e}")
            return False
        
        # Check Bedrock access
        print("\n🤖 Checking AWS Bedrock access...")
        try:
            bedrock = boto3.client('bedrock', region_name=self.region)
            models = bedrock.list_foundation_models()
            available_models = len(models.get('modelSummaries', []))
            print(f"✅ Bedrock access confirmed - {available_models} models available")
            
            # Check specific model
            model_id = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
            print(f"🔍 Checking model: {model_id}")
            
            # Try to get model info
            try:
                bedrock_runtime = boto3.client('bedrock-runtime', region_name=self.region)
                print(f"✅ Model {model_id} is accessible")
            except Exception as e:
                print(f"⚠️  Model {model_id} check: {e}")
                
        except Exception as e:
            print(f"❌ Bedrock access error: {e}")
            print("   Make sure you have enabled Bedrock in this region")
            return False
        
        # Check ECR access
        print("\n📦 Checking ECR access...")
        try:
            repos = self.ecr.describe_repositories()
            print(f"✅ ECR access confirmed")
        except Exception as e:
            print(f"⚠️  ECR access: {e}")
        
        return True
    
    def build_push(self):
        """Build and push Docker images as a separate command"""
        print("\n🐳 Building and pushing Docker images...")
        script_path = Path(__file__).parent / "build-push.sh"
        if script_path.exists():
            result = self.run_command(f"bash {script_path}")
            if result:
                print("✅ Images built and pushed successfully")
            else:
                print("❌ Build/push failed")
                sys.exit(1)
        else:
            print("❌ build-push.sh not found")
            sys.exit(1)
    
    def get_status(self):
        """Show deployment status"""
        print("\n📊 Deployment Status")
        print("=" * 50)
        
        # Check base stack
        try:
            base_stack = self.cfn.describe_stacks(StackName=self.base_stack)["Stacks"][0]
            status = base_stack['StackStatus']
            print(f"✅ Base Stack: {status}")
            
            # Get ALB URL
            alb_dns = None
            for output in base_stack.get("Outputs", []):
                if output["OutputKey"] == "ALBDNSName":
                    alb_dns = output['OutputValue']
                    print(f"\n🌐 Application URL: http://{alb_dns}")
                    print(f"📚 API Docs: http://{alb_dns}/docs")
                    break
        except ClientError as e:
            if 'does not exist' in str(e):
                print("❌ Base Stack: Not deployed")
            else:
                print(f"❌ Base Stack: Error - {e}")
        
        # Check services stack
        try:
            services_stack = self.cfn.describe_stacks(StackName=self.services_stack)["Stacks"][0]
            status = services_stack['StackStatus']
            print(f"✅ Services Stack: {status}")
            
            # Check parameters
            telemetry_enabled = False
            model_id = None
            for param in services_stack.get("Parameters", []):
                if param["ParameterKey"] == "EnableTelemetry":
                    telemetry_enabled = param["ParameterValue"] == "true"
                elif param["ParameterKey"] == "BedrockModelId":
                    model_id = param["ParameterValue"]
            
            if telemetry_enabled:
                print("✅ Langfuse Telemetry: Enabled")
            else:
                print("⚠️  Langfuse Telemetry: Disabled")
            
            if model_id:
                print(f"🤖 Bedrock Model: {model_id}")
            
            # List ECS services
            try:
                ecs = boto3.client("ecs", region_name=self.region)
                services = ecs.list_services(cluster="strands-weather-agent")
                if services['serviceArns']:
                    print("\n📦 ECS Services:")
                    for arn in services['serviceArns']:
                        service_name = arn.split('/')[-1]
                        print(f"   - {service_name}")
            except Exception as e:
                print(f"⚠️  Could not list ECS services: {e}")
                
        except ClientError as e:
            if 'does not exist' in str(e):
                print("❌ Services Stack: Not deployed")
            else:
                print(f"❌ Services Stack: Error - {e}")
        
        print("\n💡 Tips:")
        print("   - Test the deployment: python3 infra/test_services.py")
        print("   - View logs: aws logs tail /aws/ecs/strands-weather-agent --follow")
        print("   - Update with code changes: python3 infra/deploy.py update-services")
    
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


def show_help():
    """Show detailed help message"""
    print("Strands Weather Agent Infrastructure Deployment Script")
    print("=" * 55)
    print("\nUsage: python3 infra/deploy.py [command] [options]")
    print("\nCommands:")
    print("  aws-checks       Check AWS configuration and Bedrock access")
    print("  setup-ecr        Setup ECR repositories and Docker authentication")
    print("  build-push       Build and push Docker images to ECR")
    print("  all              Deploy all infrastructure (base + services)")
    print("  base             Deploy only base infrastructure")
    print("  services         Deploy only services (requires base)")
    print("  update-services  Build new images and redeploy services")
    print("  status           Show current deployment status")
    print("  cleanup-services Remove services stack only")
    print("  cleanup-base     Remove base infrastructure stack")
    print("  cleanup-all      Remove all infrastructure")
    print("  help             Show this help message")
    print("\nOptions:")
    print("  --disable-telemetry  Disable Langfuse telemetry")
    print("  --region REGION      AWS region (default: us-east-1)")
    print("\nEnvironment Variables:")
    print("  AWS_REGION          AWS region (default: us-east-1)")
    print("  BEDROCK_MODEL_ID    Bedrock model to use (default: amazon.nova-lite-v1:0)")
    print("  BEDROCK_REGION      Bedrock region (default: us-east-1)")
    print("  BEDROCK_TEMPERATURE Model temperature (default: 0)")
    print("  LOG_LEVEL           Logging level (default: INFO)")
    print("\nExamples:")
    print("  python3 infra/deploy.py aws-checks                    # Check AWS setup")
    print("  python3 infra/deploy.py setup-ecr                     # Setup ECR repositories")
    print("  python3 infra/deploy.py build-push                    # Build and push images")
    print("  python3 infra/deploy.py all                           # Full deployment")
    print("  python3 infra/deploy.py all --disable-telemetry       # Deploy without telemetry")
    print("  python3 infra/deploy.py update-services               # Build & redeploy services")
    print("  python3 infra/deploy.py status                        # Check deployment status")
    print("  python3 infra/deploy.py cleanup-services              # Remove services only")
    print("  python3 infra/deploy.py cleanup-base                  # Remove base infrastructure")
    print("  python3 infra/deploy.py cleanup-all                   # Remove all infrastructure")
    print("\n📖 For more info: https://github.com/aws-samples/strands-weather-agent")


def main():
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        show_help()
        sys.exit(0)
    
    parser = argparse.ArgumentParser(
        description="Deploy Strands Weather Agent to AWS ECS",
        add_help=False  # We handle help ourselves
    )
    parser.add_argument(
        "command",
        choices=[
            "all", "base", "services", "status", "setup-ecr",
            "aws-checks", "build-push", "update-services",
            "cleanup-services", "cleanup-base", "cleanup-all", "help"
        ],
        help="Deployment command"
    )
    parser.add_argument(
        "--disable-telemetry",
        action="store_true",
        help="Disable Langfuse telemetry"
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "us-east-1"),
        help="AWS region"
    )
    
    args = parser.parse_args()
    
    # Handle help command
    if args.command == "help":
        show_help()
        sys.exit(0)
    
    # Create deployment manager
    deployment = SimpleDeployment(args.region)
    
    # Execute command
    if args.command == "all":
        deployment.deploy_all(args.disable_telemetry)
    elif args.command == "base":
        deployment.deploy_base()
    elif args.command == "services":
        deployment.deploy_services(not args.disable_telemetry)
    elif args.command == "update-services":
        deployment.update_services(not args.disable_telemetry)
    elif args.command == "status":
        deployment.get_status()
    elif args.command == "setup-ecr":
        deployment.setup_ecr()
    elif args.command == "aws-checks":
        deployment.aws_checks()
    elif args.command == "build-push":
        deployment.build_push()
    elif args.command == "cleanup-services":
        deployment.cleanup_services()
    elif args.command == "cleanup-base":
        deployment.cleanup_base()
    elif args.command == "cleanup-all":
        deployment.cleanup_all()


if __name__ == "__main__":
    main()