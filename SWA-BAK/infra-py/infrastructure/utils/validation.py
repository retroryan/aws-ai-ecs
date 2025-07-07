"""
Validation utilities for checking prerequisites.
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .logging import log_info, log_warn, log_error


def check_aws_cli() -> bool:
    """Check if AWS CLI is installed."""
    if shutil.which('aws') is None:
        log_error("AWS CLI is not installed")
        log_warn("Please install AWS CLI: https://aws.amazon.com/cli/")
        return False
    return True


def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured."""
    try:
        boto3.client('sts').get_caller_identity()
        return True
    except NoCredentialsError:
        log_error("AWS credentials not configured")
        log_warn("Please configure AWS credentials using 'aws configure'")
        return False
    except Exception as e:
        log_error(f"Error checking AWS credentials: {e}")
        return False


def check_docker() -> bool:
    """Check if Docker is installed and running."""
    if shutil.which('docker') is None:
        log_error("Docker is not installed")
        log_warn("Please install Docker: https://www.docker.com/get-started")
        return False
    
    # Check if Docker daemon is running
    try:
        subprocess.run(['docker', 'info'], capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        log_error("Docker daemon is not running")
        log_warn("Please start Docker Desktop or Docker daemon")
        return False


def check_python() -> bool:
    """Check if Python 3 is installed."""
    if shutil.which('python3') is None:
        log_error("Python 3 is not installed")
        log_warn("Please install Python 3: https://www.python.org/downloads/")
        return False
    return True


def check_jq() -> bool:
    """Check if jq is installed (optional)."""
    if shutil.which('jq') is None:
        log_warn("jq is not installed. Some outputs may be less readable.")
        log_warn("Install jq for better JSON parsing: https://stedolan.github.io/jq/")
        return False
    return True


def check_bedrock_access(region: Optional[str] = None, model_id: str = "amazon.nova-pro-v1:0") -> bool:
    """Check if Bedrock is accessible and model is available."""
    region = region or os.environ.get('AWS_REGION', 'us-east-1')
    
    try:
        # For inference profiles (us. prefix), try to invoke the model directly
        if model_id.startswith('us.'):
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
                
                log_info(f"✓ Bedrock model {model_id} is available")
                return True
            except Exception as e:
                # If invoke fails, model is not available
                log_error(f"Bedrock model {model_id} is not available")
                log_warn(f"Request access at: https://us-east-1.console.aws.amazon.com/bedrock/home?region={region}#/modelaccess")
                return False
        
        # For non-inference profile models, check the list
        bedrock = boto3.client('bedrock', region_name=region)
        response = bedrock.list_foundation_models()
        
        # Check if specific model is available
        model_available = any(
            model['modelId'] == model_id 
            for model in response.get('modelSummaries', [])
        )
        
        if model_available:
            log_info(f"✓ Bedrock model {model_id} is available")
            return True
        else:
            log_error(f"Bedrock model {model_id} is not available")
            log_warn(f"Request access at: https://us-east-1.console.aws.amazon.com/bedrock/home?region={region}#/modelaccess")
            return False
            
    except ClientError as e:
        log_error(f"Unable to access Bedrock in region {region}: {e}")
        log_warn("Make sure you have:")
        log_warn("  - Valid AWS credentials configured")
        log_warn("  - Bedrock access enabled in your AWS account")
        log_warn("  - Correct permissions to access Bedrock")
        return False
    except Exception as e:
        log_error(f"Error checking Bedrock access: {e}")
        return False


def ensure_project_root() -> bool:
    """Ensure we're in the project root directory."""
    # Check if we're in the infra directory and move up if needed
    current_dir = Path.cwd()
    if current_dir.name == 'infra':
        os.chdir(current_dir.parent)
    
    # Verify we're in the right place by checking for key files
    required_files = ['main.py', 'mcp_servers', 'weather_agent']
    for item in required_files:
        if not Path(item).exists():
            log_error("Not in the Strands Weather Agent project root directory")
            return False
    
    return True


def validate_deployment_prerequisites() -> bool:
    """Validate all deployment prerequisites."""
    log_info("Validating deployment prerequisites...")
    
    # Check AWS CLI
    if not check_aws_cli():
        return False
    
    # Check AWS credentials
    if not check_aws_credentials():
        return False
    
    # Check Docker
    if not check_docker():
        return False
    
    # Check jq (optional but recommended)
    check_jq()
    
    log_info("✓ All prerequisites validated")
    return True