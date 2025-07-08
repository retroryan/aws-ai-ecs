#!/usr/bin/env python3
"""
AWS Setup Script for Strands Weather Agent Bedrock Configuration.
Checks AWS CLI setup and generates a bedrock.env file with available models.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

import click
import boto3
from rich.console import Console
from rich.table import Table
from botocore.exceptions import ClientError, NoCredentialsError

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from infrastructure.utils import (
    log_info, log_warn, log_error, print_section,
    check_aws_cli, check_aws_credentials, check_bedrock_access
)
from infrastructure.config import get_config
from infrastructure.aws.ecr import ECRManager


console = Console()

# Models supported by the strands weather agent
SUPPORTED_MODELS = [
    "amazon.nova-lite-v1:0",
    "amazon.nova-pro-v1:0",
    "us.amazon.nova-lite-v1:0",
    "us.amazon.nova-pro-v1:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-opus-20240229-v1:0",
    "meta.llama3-70b-instruct-v1:0",
    "meta.llama3-1-70b-instruct-v1:0",
    "us.meta.llama3-1-70b-instruct-v1:0",
    "cohere.command-r-plus-v1:0",
    "cohere.command-r-v1:0"
]

# Model priority for auto-selection
MODEL_PRIORITY = [
    ("amazon.nova-lite-v1:0", "Fast and cost-effective"),
    ("us.amazon.nova-lite-v1:0", "Fast and cost-effective with cross-region"),
    ("anthropic.claude-3-haiku-20240307-v1:0", "Fast Claude model"),
    ("us.anthropic.claude-3-5-haiku-20241022-v1:0", "Fast Claude model with cross-region"),
    ("anthropic.claude-3-5-sonnet-20240620-v1:0", "High quality"),
    ("us.anthropic.claude-3-5-sonnet-20241022-v2:0", "Latest high quality with cross-region"),
    ("amazon.nova-pro-v1:0", "Higher performance"),
    ("us.amazon.nova-pro-v1:0", "Higher performance with cross-region"),
]


def get_aws_region() -> str:
    """Get current AWS region."""
    return os.environ.get('AWS_REGION', 'us-east-1')


def get_aws_account_id() -> str:
    """Get AWS account ID."""
    try:
        sts = boto3.client('sts')
        response = sts.get_caller_identity()
        return response['Account']
    except Exception:
        return 'unknown'


def get_current_profile() -> str:
    """Get current AWS profile."""
    # Check environment variable first
    if profile := os.environ.get('AWS_PROFILE'):
        return profile
    
    # Try to get from boto3 session
    try:
        session = boto3.Session()
        return session.profile_name or 'default'
    except Exception:
        return 'default'


def get_required_region() -> str:
    """Get required region from application configuration."""
    config = get_config()
    return os.environ.get('BEDROCK_REGION', config.aws.region)


def list_available_models_by_provider(region: str) -> Dict[str, List[str]]:
    """List available Bedrock models grouped by provider."""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        response = bedrock.list_foundation_models()
        
        models_by_provider = {}
        for model in response.get('modelSummaries', []):
            provider = model['providerName']
            model_id = model['modelId']
            
            if provider not in models_by_provider:
                models_by_provider[provider] = []
            models_by_provider[provider].append(model_id)
        
        return models_by_provider
    except Exception as e:
        log_error(f"Failed to list Bedrock models: {e}")
        return {}


def check_and_create_ecr_repositories() -> tuple[bool, List[str]]:
    """Check ECR repositories and create if missing."""
    config = get_config()
    ecr_manager = ECRManager(config.aws.region)
    missing_repos = []
    created_repos = []
    
    for repo in config.ecr.all_repos:
        if not ecr_manager.repository_exists(repo):
            missing_repos.append(repo)
            # Create the repository
            if ecr_manager.create_repository(repo):
                created_repos.append(repo)
                log_info(f"✅ Created ECR repository: {repo}")
            else:
                log_error(f"❌ Failed to create ECR repository: {repo}")
    
    return len(missing_repos) == 0 or len(created_repos) == len(missing_repos), created_repos


def validate_setup() -> bool:
    """Run all validation checks before setup."""
    console.print("\n📋 Running validation checks...", style="bold cyan")
    console.print("=" * 40)
    
    # Check AWS CLI
    if not check_aws_cli():
        console.print("❌ AWS CLI is not installed", style="red")
        console.print("Please install: https://aws.amazon.com/cli/")
        return False
    console.print("✅ AWS CLI is installed", style="green")
    
    # Check AWS credentials
    if not check_aws_credentials():
        console.print("❌ AWS credentials not configured", style="red")
        console.print("Please run: aws configure")
        return False
    console.print("✅ AWS credentials configured", style="green")
    
    # Display current configuration
    current_profile = get_current_profile()
    current_region = get_aws_region()
    account_id = get_aws_account_id()
    
    console.print(f"\n📋 Current AWS Configuration:")
    console.print(f"Profile: {current_profile}")
    console.print(f"Region: {current_region}")
    console.print(f"Account ID: {account_id}")
    
    # Check region match
    required_region = get_required_region()
    if current_region != required_region:
        console.print(f"\n⚠️  Region mismatch: Current={current_region}, Required={required_region}", style="yellow")
        console.print(f"💡 Set region with: export AWS_REGION={required_region}")
    
    # Check specific Bedrock models
    console.print("\n🤖 Checking Bedrock model access...")
    models_to_check = [
        ("Amazon Nova Pro", "amazon.nova-pro-v1:0"),
        ("Claude 3.5 Sonnet", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
        ("Claude 3.5 Haiku", "us.anthropic.claude-3-5-haiku-20241022-v1:0"),
    ]
    
    all_models_available = True
    for model_name, model_id in models_to_check:
        if check_bedrock_access(required_region, model_id):
            console.print(f"{model_name}: ✅ Available", style="green")
        else:
            console.print(f"{model_name}: ❌ Not available", style="red")
            all_models_available = False
    
    if not all_models_available:
        console.print("\n⚠️  Some models are not available. Continuing with available models...", style="yellow")
    
    # Check and create ECR repositories
    console.print("\n🐳 Checking ECR repositories...")
    config = get_config()
    ecr_success, created_repos = check_and_create_ecr_repositories()
    
    if created_repos:
        console.print(f"\n✅ Created {len(created_repos)} ECR repositories", style="green")
    elif ecr_success:
        console.print("✅ All ECR repositories already exist", style="green")
    else:
        console.print("❌ Failed to create some ECR repositories", style="red")
        console.print("⚠️  You may need to create them manually for AWS deployment", style="yellow")
    
    console.print("\n✅ Validation complete!\n", style="green bold")
    return True


def get_aws_identity() -> Dict[str, str]:
    """Get current AWS identity information."""
    try:
        sts = boto3.client('sts')
        response = sts.get_caller_identity()
        return {
            'account_id': response['Account'],
            'user_id': response['UserId'],
            'arn': response['Arn']
        }
    except Exception:
        return {
            'account_id': 'unknown',
            'user_id': 'unknown',
            'arn': 'unknown'
        }


def check_bedrock_availability(region: str) -> bool:
    """Check if Bedrock is available in the specified region."""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        bedrock.list_foundation_models()
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ['UnauthorizedOperation', 'AccessDeniedException']:
            log_warn(f"Access denied to Bedrock in region {region}")
            log_warn("Please check your IAM permissions for Bedrock")
        else:
            log_warn(f"Bedrock not available: {error_code}")
        return False
    except Exception as e:
        log_warn(f"Unable to check Bedrock availability: {e}")
        return False


def get_available_models(region: str) -> List[str]:
    """Get list of available Bedrock models."""
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        response = bedrock.list_foundation_models()
        return [model['modelId'] for model in response.get('modelSummaries', [])]
    except Exception:
        return []


def test_model_availability(model_id: str, region: str) -> bool:
    """Test if a model is available by trying to use it."""
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # Use the Converse API which works with all models
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Test"}]
                }
            ],
            inferenceConfig={
                "maxTokens": 10,
                "temperature": 0
            }
        )
        
        return True
    except Exception:
        return False


def find_supported_models(available_models: List[str], region: str) -> List[str]:
    """Find which supported models are available, including inference profiles."""
    available_supported = []
    
    # Check models from list_foundation_models
    for model in SUPPORTED_MODELS:
        if model in available_models:
            available_supported.append(model)
    
    # For inference profiles (us. prefix), test directly
    for model in SUPPORTED_MODELS:
        if model.startswith('us.') and model not in available_supported:
            if test_model_availability(model, region):
                available_supported.append(model)
    
    return available_supported


def select_best_model(available_supported: List[str]) -> Tuple[str, str]:
    """Select the best available model based on priority."""
    for model_id, description in MODEL_PRIORITY:
        if model_id in available_supported:
            return model_id, description
    
    # If no priority model found, use first available
    if available_supported:
        return available_supported[0], "Available model"
    
    # Default fallback
    return "amazon.nova-lite-v1:0", "Default model (may not be available)"


def test_model_access(model_id: str, region: str) -> bool:
    """Test if we can invoke a specific model using the Converse API."""
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # Use the Converse API which works with all models
        response = bedrock_runtime.converse(
            modelId=model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Test"}]
                }
            ],
            inferenceConfig={
                "maxTokens": 10,
                "temperature": 0
            }
        )
        
        return True
    except Exception as e:
        log_warn(f"Unable to invoke {model_id}: {e}")
        return False


def create_bedrock_env(
    model_id: str,
    region: str,
    profile: str,
    account_id: str,
    output_file: Path
) -> None:
    """Create or update cloud.env configuration file, preserving existing values."""
    
    # Read existing values if file exists
    existing_values = {}
    if output_file.exists():
        with open(output_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_values[key] = value
    
    # Update with new Bedrock values
    existing_values.update({
        'AWS_REGION': region,
        'BEDROCK_MODEL_ID': model_id,
        'BEDROCK_REGION': region,
        'BEDROCK_TEMPERATURE': '0',
        'LOG_LEVEL': existing_values.get('LOG_LEVEL', 'INFO')
    })
    
    # Build content preserving order and comments
    content = f"""# Strands + Langfuse Configuration
# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# AWS Bedrock Configuration
AWS_REGION={existing_values.get('AWS_REGION', region)}
BEDROCK_REGION={existing_values.get('BEDROCK_REGION', region)}
BEDROCK_MODEL_ID={existing_values.get('BEDROCK_MODEL_ID', model_id)}
"""
    
    # Add Langfuse configuration if it exists
    if 'LANGFUSE_HOST' in existing_values:
        content += f"""
# Langfuse Configuration
LANGFUSE_HOST={existing_values['LANGFUSE_HOST']}
LANGFUSE_PUBLIC_KEY={existing_values.get('LANGFUSE_PUBLIC_KEY', '')}
LANGFUSE_SECRET_KEY={existing_values.get('LANGFUSE_SECRET_KEY', '')}
"""
    
    # Add any other existing values not already included
    other_keys = set(existing_values.keys()) - {
        'AWS_REGION', 'BEDROCK_REGION', 'BEDROCK_MODEL_ID', 
        'LANGFUSE_HOST', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY'
    }
    
    if other_keys:
        content += "\n# Additional Configuration\n"
        for key in sorted(other_keys):
            content += f"{key}={existing_values[key]}\n"
    
    output_file.write_text(content)
    log_info(f"✅ Successfully updated {output_file}")


@click.command()
@click.option('--region', help='AWS region', default=None)
@click.option('--profile', help='AWS profile', default=None)
@click.option('--output', '-o', help='Output file', default='../cloud.env')
@click.option('--test-model', is_flag=True, help='Test model access')
@click.option('--skip-validation', is_flag=True, help='Skip validation checks')
def main(region: Optional[str], profile: Optional[str], output: str, test_model: bool, skip_validation: bool):
    """AWS Bedrock setup script for Strands Weather Agent.
    
    This script:
    1. Validates AWS configuration and credentials
    2. Checks Bedrock model availability
    3. Creates ECR repositories if needed
    4. Generates bedrock.env configuration file
    """
    
    console.print("=" * 50, style="blue")
    console.print("AWS Setup & Validation for Strands Weather Agent", style="bold cyan")
    console.print("=" * 50, style="blue")
    
    # Set profile if specified
    if profile:
        os.environ['AWS_PROFILE'] = profile
    
    # Set region if specified
    if region:
        os.environ['AWS_REGION'] = region
    
    # Run validation unless skipped
    if not skip_validation:
        if not validate_setup():
            console.print("\n❌ Validation failed. Please fix the issues above.", style="red")
            sys.exit(1)
    
    console.print("\n📝 Generating bedrock.env configuration...")
    console.print("=" * 40)
    
    # Get AWS identity for bedrock.env generation
    current_profile = get_current_profile()
    current_region = get_aws_region()
    account_id = get_aws_account_id()
    identity = get_aws_identity()
    
    # Check Bedrock availability
    console.print(f"Checking Bedrock availability in {current_region}...")
    
    if not check_bedrock_availability(current_region):
        console.print("⚠️  WARNING: Unable to list Bedrock models. This could mean:", style="yellow")
        console.print(f"   - Bedrock is not available in your region ({current_region})")
        console.print("   - You don't have permissions to access Bedrock")
        console.print("   - Your account doesn't have Bedrock enabled")
        console.print()
        console.print("Continuing with default configuration...")
        
        # Create default bedrock.env
        output_file = Path(output)
        create_bedrock_env(
            model_id="amazon.nova-lite-v1:0",
            region=current_region,
            profile=current_profile,
            account_id=identity['account_id'],
            output_file=output_file
        )
        
        console.print()
        console.print("📝 Configuration has been written to cloud.env")
        console.print()
        console.print("⚠️  Please verify that you have access to Bedrock and the model specified.", 
                     style="yellow")
        return
    
    # List available models
    console.print("✅ Bedrock is available!", style="green")
    console.print("Fetching available models...")
    console.print()
    
    available_models = get_available_models(current_region)
    available_supported = find_supported_models(available_models, current_region)
    
    if not available_supported:
        console.print("⚠️  No supported models found. Available models in your region:", style="yellow")
        for model in sorted(available_models):
            console.print(f"  - {model}")
        selected_model = "amazon.nova-lite-v1:0"
        selected_description = "Default model"
        console.print()
        console.print(f"Using default model: {selected_model}")
    else:
        console.print("Available supported models:")
        for model in available_supported:
            console.print(f"  - {model}", style="green")
        
        # Select best model
        selected_model, selected_description = select_best_model(available_supported)
        console.print()
        console.print(f"Selected model: {selected_model} ({selected_description})", style="bold green")
    
    # Create bedrock.env file
    console.print()
    console.print("Creating bedrock.env file...")
    
    output_file = Path(output)
    create_bedrock_env(
        model_id=selected_model,
        region=current_region,
        profile=current_profile,
        account_id=identity['account_id'],
        output_file=output_file
    )
    
    console.print()
    console.print("=" * 35, style="blue")
    console.print("Setup Complete!", style="bold green")
    console.print("=" * 35, style="blue")
    console.print()
    
    console.print("📝 Configuration updated in cloud.env")
    console.print()
    console.print("🚀 The main agent will use these environment variables to connect to AWS Bedrock.")
    console.print()
    console.print("💡 Tips:", style="yellow")
    console.print("   - For ECS deployment, remove AWS_PROFILE and use IAM task roles instead")
    console.print("   - Temperature of 0 provides most consistent responses")
    console.print("   - Nova Lite is recommended for cost-effective operation")
    console.print("   - Claude Sonnet provides the best quality but at higher cost")
    console.print()
    
    # Test model access if requested
    if test_model:
        console.print("Checking access to selected model...")
        if test_model_access(selected_model, current_region):
            console.print(f"✅ Successfully verified access to {selected_model}", style="green")
        else:
            console.print(f"⚠️  WARNING: Unable to invoke {selected_model}", style="yellow")
            console.print("   Please ensure the model is enabled in the AWS Bedrock console")
            console.print(f"   https://console.aws.amazon.com/bedrock/home?region={current_region}#/modelaccess")
    
    console.print()


if __name__ == '__main__':
    main()