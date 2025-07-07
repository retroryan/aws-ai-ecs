#!/usr/bin/env python3
"""
AWS Deployment Script for Strands Weather Agent Demo.
Demonstrates deploying an AI agent with Langfuse telemetry to AWS ECS.
"""

import argparse
import os
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, Optional, Any

import boto3
from botocore.exceptions import ClientError
from rich.console import Console
from rich.table import Table

from infrastructure import get_config
from infrastructure.utils.logging import log_info, log_warn, log_error, print_section
from infrastructure.utils.validation import check_aws_cli, check_aws_credentials
from infrastructure.utils.console import spinner, print_success, print_error, with_progress
from infrastructure.aws.ecr import ECRManager
from infrastructure.aws.ecs import ECSUtils


console = Console()


class Deployment:
    """Deployment manager for AWS Strands demo using centralized config."""
    
    def __init__(self):
        """Initialize deployment with configuration."""
        # Use centralized configuration
        self.config = get_config()
        self.region = self.config.aws.region
        self.base_stack = self.config.stacks.base_stack_name
        self.services_stack = self.config.stacks.services_stack_name
        
        # AWS clients
        self.cfn = boto3.client("cloudformation", region_name=self.region)
        self.ssm = boto3.client("ssm", region_name=self.region)
        self.ecr = boto3.client("ecr", region_name=self.region)
        self.ecs = boto3.client("ecs", region_name=self.region)
        self.sts = boto3.client("sts", region_name=self.region)
        
        # Managers
        self.ecr_manager = ECRManager(self.region)
        self.ecs_utils = ECSUtils(self.region)
        
        # Get account ID
        self.account_id = self._get_account_id()
    
    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        response = self.sts.get_caller_identity()
        return response['Account']
    
    def validate_prerequisites(self) -> bool:
        """Validate deployment prerequisites."""
        log_info("Validating deployment prerequisites...")
        
        # Check AWS CLI
        if not check_aws_cli():
            return False
        
        # Check AWS credentials
        if not check_aws_credentials():
            return False
        
        # Check Bedrock model access
        model_id = self.config.bedrock.model_id
        try:
            with spinner(f"Checking Bedrock model access for {model_id}..."):
                bedrock = boto3.client('bedrock', region_name=self.region)
                response = bedrock.list_foundation_models()
                
                # Check if model is available
                model_available = any(
                    model['modelId'] == model_id 
                    for model in response.get('modelSummaries', [])
                )
                
                if not model_available:
                    log_error(f"Bedrock model {model_id} is not available in region {self.region}")
                    log_warn("Please request access or update BEDROCK_MODEL_ID in your .env file")
                    return False
        except Exception as e:
            log_error(f"Failed to check Bedrock access: {e}")
            return False
        
        log_info("✓ All prerequisites validated")
        return True
    
    def run_python_script(self, script_path: str, args: list = None) -> bool:
        """Run a Python script with arguments."""
        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)
        
        log_info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        return result.returncode == 0
    
    def deploy_base_infrastructure(self) -> bool:
        """Deploy base infrastructure stack."""
        print_section("Deploying Base Infrastructure")
        
        template_path = Path(__file__).parent / "infrastructure" / "cloudformation" / "templates" / "base.cfn"
        
        if not template_path.exists():
            log_error(f"CloudFormation template not found: {template_path}")
            return False
        
        params = []
        
        try:
            with spinner(f"Deploying stack {self.base_stack}..."):
                with open(template_path, 'r') as f:
                    template_body = f.read()
                
                # Check if stack exists
                try:
                    self.cfn.describe_stacks(StackName=self.base_stack)
                    # Update existing stack
                    self.cfn.update_stack(
                        StackName=self.base_stack,
                        TemplateBody=template_body,
                        Parameters=params,
                        Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
                    )
                    log_info(f"Updating stack {self.base_stack}...")
                except ClientError as e:
                    if 'does not exist' in str(e):
                        # Create new stack
                        self.cfn.create_stack(
                            StackName=self.base_stack,
                            TemplateBody=template_body,
                            Parameters=params,
                            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
                        )
                        log_info(f"Creating stack {self.base_stack}...")
                    elif 'No updates are to be performed' in str(e):
                        # Stack is already up to date
                        log_info(f"Stack {self.base_stack} is already up to date")
                        print_success("Base infrastructure is already deployed and up to date!")
                        return True
                    else:
                        raise
                
                # Wait for stack to complete
                waiter = self.cfn.get_waiter('stack_create_complete')
                log_info("Waiting for stack to complete (this may take 5-10 minutes)...")
                waiter.wait(StackName=self.base_stack)
                
            print_success("Base infrastructure deployed successfully!")
            return True
            
        except Exception as e:
            print_error(f"Failed to deploy base infrastructure: {e}")
            return False
    
    def build_and_push_images(self) -> bool:
        """Build and push Docker images to ECR."""
        print_section("Building and Pushing Docker Images")
        
        script_path = Path(__file__).parent / "commands" / "build_push.py"
        
        if not script_path.exists():
            log_error("build_push.py script not found")
            return False
        
        return self.run_python_script(script_path)
    
    def deploy_services(self) -> bool:
        """Deploy services stack."""
        print_section("Deploying Services")
        
        template_path = Path(__file__).parent / "infrastructure" / "cloudformation" / "templates" / "services.cfn"
        
        if not template_path.exists():
            log_error(f"CloudFormation template not found: {template_path}")
            return False
        
        # Read image tags from .image-tags file
        image_tags_file = Path(__file__).parent / ".image-tags"
        if not image_tags_file.exists():
            log_error(".image-tags file not found. Run build_push.py first.")
            return False
        
        # Parse image tags
        image_tags = {}
        with open(image_tags_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    image_tags[key] = value
        
        # Get base stack outputs
        try:
            response = self.cfn.describe_stacks(StackName=self.base_stack)
            outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
        except Exception as e:
            log_error(f"Failed to get base stack outputs: {e}")
            return False
        
        # Prepare parameters
        params = [
            {"ParameterKey": "BaseStackName", "ParameterValue": self.base_stack},
            {"ParameterKey": "BedrockModelId", "ParameterValue": self.config.bedrock.model_id},
            {"ParameterKey": "BedrockRegion", "ParameterValue": self.config.bedrock.region},
            {"ParameterKey": "BedrockTemperature", "ParameterValue": str(self.config.bedrock.temperature)},
            {"ParameterKey": "LogLevel", "ParameterValue": self.config.deployment.log_level},
            {"ParameterKey": "MainImageTag", "ParameterValue": image_tags.get('MAIN_IMAGE_TAG', 'latest')},
            {"ParameterKey": "ForecastImageTag", "ParameterValue": image_tags.get('FORECAST_IMAGE_TAG', 'latest')},
            {"ParameterKey": "HistoricalImageTag", "ParameterValue": image_tags.get('HISTORICAL_IMAGE_TAG', 'latest')},
            {"ParameterKey": "AgriculturalImageTag", "ParameterValue": image_tags.get('AGRICULTURAL_IMAGE_TAG', 'latest')}
        ]
        
        # Add telemetry parameters
        if os.environ.get('LANGFUSE_PUBLIC_KEY'):
            params.extend([
                {"ParameterKey": "LangfusePublicKey", "ParameterValue": os.environ['LANGFUSE_PUBLIC_KEY']},
                {"ParameterKey": "LangfuseSecretKey", "ParameterValue": os.environ['LANGFUSE_SECRET_KEY']},
                {"ParameterKey": "LangfuseHost", "ParameterValue": os.environ.get('LANGFUSE_HOST', 'https://us.cloud.langfuse.com')},
                {"ParameterKey": "EnableTelemetry", "ParameterValue": "true"}
            ])
        else:
            # Even if telemetry is not configured, we need to set EnableTelemetry to false
            params.append({"ParameterKey": "EnableTelemetry", "ParameterValue": "false"})
        
        try:
            with spinner(f"Deploying stack {self.services_stack}..."):
                with open(template_path, 'r') as f:
                    template_body = f.read()
                
                # Check if stack exists
                try:
                    self.cfn.describe_stacks(StackName=self.services_stack)
                    # Update existing stack
                    self.cfn.update_stack(
                        StackName=self.services_stack,
                        TemplateBody=template_body,
                        Parameters=params,
                        Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
                    )
                    log_info(f"Updating stack {self.services_stack}...")
                except ClientError as e:
                    if 'does not exist' in str(e):
                        # Create new stack
                        self.cfn.create_stack(
                            StackName=self.services_stack,
                            TemplateBody=template_body,
                            Parameters=params,
                            Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
                        )
                        log_info(f"Creating stack {self.services_stack}...")
                    elif 'No updates are to be performed' in str(e):
                        # Stack is already up to date
                        log_info(f"Stack {self.services_stack} is already up to date")
                        print_success("Services are already deployed and up to date!")
                        return True
                    else:
                        raise
                
                # Wait for stack to complete
                waiter = self.cfn.get_waiter('stack_create_complete')
                log_info("Waiting for services to deploy (this may take 10-15 minutes)...")
                waiter.wait(StackName=self.services_stack)
                
            print_success("Services deployed successfully!")
            
            # Wait for services to stabilize
            self._wait_for_services_stable()
            
            return True
            
        except Exception as e:
            print_error(f"Failed to deploy services: {e}")
            return False
    
    def _wait_for_services_stable(self):
        """Wait for ECS services to become stable."""
        log_info("Waiting for services to stabilize...")
        
        # Get cluster name from base stack
        response = self.cfn.describe_stacks(StackName=self.base_stack)
        outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
        cluster_name = outputs.get('ClusterName')
        
        if not cluster_name:
            log_warn("Could not determine cluster name")
            return
        
        # Get service names from services stack
        response = self.cfn.describe_stacks(StackName=self.services_stack)
        outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
        
        services = [
            outputs.get('MainServiceName'),
            outputs.get('ForecastServiceName'),
            outputs.get('HistoricalServiceName'),
            outputs.get('AgriculturalServiceName')
        ]
        
        # Wait for each service
        for service in services:
            if service:
                service_name = service.split('/')[-1]  # Extract service name from ARN
                with spinner(f"Waiting for {service_name} to stabilize..."):
                    self.ecs_utils.wait_for_service_stable(
                        service_name,
                        'main' if 'weather-agent' in service_name else 'mcp',
                        300,  # timeout
                        cluster_name
                    )
    
    def update_services(self) -> bool:
        """Update services with new container images."""
        print_section("Updating Services")
        
        # First build and push new images
        if not self.build_and_push_images():
            return False
        
        # Then update the services stack
        if not self.deploy_services():
            return False
        
        # Force ECS to use the new images
        self._force_ecs_update()
        return True
    
    def _force_ecs_update(self):
        """Force ECS services to pull new images by updating service."""
        try:
            # Get cluster name - it's always "strands-weather-agent"
            cluster_name = "strands-weather-agent"
            
            # List services in the cluster
            response = self.ecs.list_services(cluster=cluster_name)
            service_arns = response.get('serviceArns', [])
            
            for service_arn in service_arns:
                service_name = service_arn.split('/')[-1]
                log_info(f"Updating service: {service_name}")
                
                # Force new deployment
                self.ecs.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    forceNewDeployment=True
                )
            
            if service_arns:
                log_info(f"Forced update for {len(service_arns)} services")
            else:
                log_warn("No services found to update")
                
        except Exception as e:
            log_warn(f"Could not force ECS update: {e}")
            # Non-critical error, continue
    
    def cleanup_services(self) -> bool:
        """Remove services stack only."""
        print_section("Removing Services Stack")
        
        try:
            self.cfn.describe_stacks(StackName=self.services_stack)
            
            # Delete the stack
            with spinner(f"Deleting stack {self.services_stack}..."):
                self.cfn.delete_stack(StackName=self.services_stack)
            
            log_info("Waiting for stack deletion...")
            
            # Wait for deletion
            waiter = self.cfn.get_waiter('stack_delete_complete')
            waiter.wait(StackName=self.services_stack)
            
            print_success("Services stack removed successfully!")
            return True
            
        except ClientError as e:
            if 'does not exist' in str(e):
                log_warn("Services stack not found")
                return True
            else:
                print_error(f"Failed to remove services stack: {e}")
                return False
    
    def cleanup_base(self) -> bool:
        """Remove base infrastructure stack."""
        print_section("Removing Base Infrastructure Stack")
        
        try:
            self.cfn.describe_stacks(StackName=self.base_stack)
            
            # Delete the stack
            with spinner(f"Deleting stack {self.base_stack}..."):
                self.cfn.delete_stack(StackName=self.base_stack)
            
            log_info("Waiting for stack deletion...")
            
            # Wait for deletion
            waiter = self.cfn.get_waiter('stack_delete_complete')
            waiter.wait(StackName=self.base_stack)
            
            print_success("Base infrastructure stack removed successfully!")
            return True
            
        except ClientError as e:
            if 'does not exist' in str(e):
                log_warn("Base stack not found")
                return True
            else:
                print_error(f"Failed to remove base stack: {e}")
                return False
    
    def cleanup_all(self) -> bool:
        """Remove all infrastructure."""
        print_section("Remove All Infrastructure")
        
        console.print("\n⚠️  WARNING: This will remove all infrastructure!", style="yellow bold")
        response = console.input("Are you sure? (yes/no): ")
        
        if response.lower() == "yes":
            # Remove services first
            if not self.cleanup_services():
                return False
            
            # Then remove base infrastructure
            if not self.cleanup_base():
                return False
            
            print_success("All infrastructure removed successfully!")
            return True
        else:
            log_info("Cleanup cancelled")
            return True
    
    def deploy_all(self) -> bool:
        """Deploy complete infrastructure."""
        print_section("Full Deployment")
        
        # Validate prerequisites
        if not self.validate_prerequisites():
            return False
        
        # Deploy base infrastructure
        if not self.deploy_base_infrastructure():
            return False
        
        # Build and push images
        if not self.build_and_push_images():
            return False
        
        # Deploy services
        if not self.deploy_services():
            return False
        
        # Show deployment info
        self._show_deployment_info()
        
        return True
    
    def _show_deployment_info(self):
        """Show deployment information."""
        print_section("Deployment Complete!")
        
        # Get load balancer URL
        response = self.cfn.describe_stacks(StackName=self.base_stack)
        outputs = {o['OutputKey']: o['OutputValue'] for o in response['Stacks'][0]['Outputs']}
        lb_url = outputs.get('ALBDNSName')
        
        if lb_url:
            console.print(f"\n🎉 Your Weather Agent API is available at:")
            console.print(f"   [cyan]http://{lb_url}[/cyan]")
            console.print(f"\nTest it with:")
            console.print(f'   curl -X POST "http://{lb_url}/query" \\')
            console.print(f'       -H "Content-Type: application/json" \\')
            console.print(f'       -d \'{{\"question\": \"What is the weather in Chicago?\"}}\'')
            console.print(f"\nCheck status with:")
            console.print(f"   python status.py")
    
    def run_command(self, command: str) -> bool:
        """Run a deployment command."""
        commands = {
            'all': self.deploy_all,
            'base': self.deploy_base_infrastructure,
            'build': self.build_and_push_images,
            'services': self.deploy_services,
            'update-services': self.update_services,
            'cleanup-services': self.cleanup_services,
            'cleanup-base': self.cleanup_base,
            'cleanup-all': self.cleanup_all
        }
        
        if command not in commands:
            log_error(f"Unknown command: {command}")
            log_info(f"Available commands: {', '.join(commands.keys())}")
            return False
        
        return commands[command]()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Deploy Strands Weather Agent to AWS ECS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  all               - Deploy complete infrastructure (base + build + services)
  base              - Deploy base infrastructure (VPC, ECS cluster, ALB)
  build             - Build and push Docker images to ECR
  services          - Deploy ECS services (requires base and build)
  update-services   - Update services with new images (build + redeploy)
  cleanup-services  - Remove services stack only
  cleanup-base      - Remove base infrastructure stack
  cleanup-all       - Remove all infrastructure (with confirmation)

Examples:
  %(prog)s all                    # Full deployment
  %(prog)s base                   # Deploy infrastructure only
  %(prog)s build                  # Build and push images only
  %(prog)s services               # Deploy services only
  %(prog)s update-services        # Update with new code changes
  %(prog)s cleanup-services       # Remove services only
  %(prog)s cleanup-base           # Remove base infrastructure
  %(prog)s cleanup-all            # Remove everything
  %(prog)s all --region us-east-1 # Deploy to specific region
"""
    )
    parser.add_argument(
        'command',
        choices=['all', 'base', 'build', 'services', 'update-services', 
                 'cleanup-services', 'cleanup-base', 'cleanup-all'],
        help='Deployment command to run'
    )
    parser.add_argument(
        '--region',
        help='AWS region (overrides config)',
        default=None
    )
    
    # Show help if no arguments provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)
    
    args = parser.parse_args()
    
    # Override region if provided
    if args.region:
        os.environ['AWS_REGION'] = args.region
    
    deployment = Deployment()
    success = deployment.run_command(args.command)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()