"""
Common utilities and logging functions for AWS infrastructure operations.
"""

import os
import sys
import logging
from typing import Optional, Any
from datetime import datetime

from ..config import config


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.deployment.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


def log_info(message: str) -> None:
    """Log an info message."""
    logger.info(message)
    print(f"ℹ️  {message}")


def log_warn(message: str) -> None:
    """Log a warning message."""
    logger.warning(message)
    print(f"⚠️  {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """Log an error message."""
    logger.error(message)
    print(f"❌ {message}", file=sys.stderr)


def log_step(message: str) -> None:
    """Log a step in a process."""
    logger.info(f"STEP: {message}")
    print(f"▶️  {message}")


def log_success(message: str) -> None:
    """Log a success message."""
    logger.info(f"SUCCESS: {message}")
    print(f"✅ {message}")


def get_aws_region() -> str:
    """Get the configured AWS region."""
    return config.aws.region


def get_aws_profile() -> Optional[str]:
    """Get the configured AWS profile."""
    return config.aws.profile


def format_timestamp() -> str:
    """Get a formatted timestamp string."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured."""
    import boto3
    try:
        sts = boto3.client('sts')
        sts.get_caller_identity()
        return True
    except Exception as e:
        log_error(f"AWS credentials not configured: {e}")
        return False


def get_aws_account_id() -> Optional[str]:
    """Get the AWS account ID."""
    import boto3
    try:
        sts = boto3.client('sts')
        response = sts.get_caller_identity()
        return response['Account']
    except Exception as e:
        log_error(f"Failed to get AWS account ID: {e}")
        return None


def get_ecr_registry() -> Optional[str]:
    """Get the ECR registry URL."""
    account_id = get_aws_account_id()
    region = get_aws_region()
    if account_id and region:
        return f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    return None


def check_ecr_repository(repo_name: str, region: Optional[str] = None) -> bool:
    """Check if an ECR repository exists."""
    import boto3
    from botocore.exceptions import ClientError
    
    region = region or get_aws_region()
    try:
        ecr = boto3.client('ecr', region_name=region)
        ecr.describe_repositories(repositoryNames=[repo_name])
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'RepositoryNotFoundException':
            return False
        log_error(f"Error checking ECR repository: {e}")
        return False


def authenticate_docker_ecr(region: Optional[str] = None) -> bool:
    """Authenticate Docker with ECR."""
    import subprocess
    
    region = region or get_aws_region()
    registry = get_ecr_registry()
    
    if not registry:
        log_error("Unable to determine ECR registry")
        return False
    
    try:
        # Get ECR login token
        cmd = f"aws ecr get-login-password --region {region} | docker login --username AWS --password-stdin {registry}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            log_info("Successfully authenticated with ECR")
            return True
        else:
            log_error(f"Failed to authenticate with ECR: {result.stderr}")
            return False
    except Exception as e:
        log_error(f"Error authenticating with ECR: {e}")
        return False