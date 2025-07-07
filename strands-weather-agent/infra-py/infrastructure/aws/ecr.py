"""
Amazon ECR (Elastic Container Registry) operations.
"""

import base64
import subprocess
from typing import Optional, Dict, List, Any

import boto3
from botocore.exceptions import ClientError

from ..utils.logging import log_info, log_warn, log_error


class ECRManager:
    """Manages ECR repository operations."""
    
    def __init__(self, region: Optional[str] = None):
        """Initialize ECR manager with specified region."""
        self.region = region or 'us-east-1'
        self.ecr_client = boto3.client('ecr', region_name=self.region)
        self._registry_url = None
    
    @property
    def registry_url(self) -> Optional[str]:
        """Get ECR registry URL."""
        if not self._registry_url:
            try:
                sts = boto3.client('sts')
                account_id = sts.get_caller_identity()['Account']
                self._registry_url = f"{account_id}.dkr.ecr.{self.region}.amazonaws.com"
            except Exception:
                return None
        return self._registry_url
    
    def repository_exists(self, repo_name: str) -> bool:
        """Check if ECR repository exists."""
        try:
            self.ecr_client.describe_repositories(repositoryNames=[repo_name])
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'RepositoryNotFoundException':
                return False
            raise
    
    def create_repository(self, repo_name: str, scan_on_push: bool = True) -> bool:
        """Create ECR repository if it doesn't exist."""
        if self.repository_exists(repo_name):
            log_info(f"ECR repository '{repo_name}' already exists")
            return True
        
        try:
            self.ecr_client.create_repository(
                repositoryName=repo_name,
                imageScanningConfiguration={'scanOnPush': scan_on_push},
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            log_info(f"✓ Created ECR repository '{repo_name}'")
            return True
        except Exception as e:
            log_error(f"Failed to create ECR repository '{repo_name}': {e}")
            return False
    
    def delete_repository(self, repo_name: str, force: bool = False) -> bool:
        """Delete ECR repository."""
        if not self.repository_exists(repo_name):
            log_info(f"ECR repository '{repo_name}' does not exist")
            return True
        
        try:
            self.ecr_client.delete_repository(
                repositoryName=repo_name,
                force=force
            )
            log_info(f"✓ Deleted ECR repository '{repo_name}'")
            return True
        except Exception as e:
            log_error(f"Failed to delete ECR repository '{repo_name}': {e}")
            return False
    
    def get_authorization_token(self) -> Optional[str]:
        """Get Docker authorization token for ECR."""
        try:
            response = self.ecr_client.get_authorization_token()
            auth_data = response['authorizationData'][0]
            return auth_data['authorizationToken']
        except Exception as e:
            log_error(f"Failed to get ECR authorization token: {e}")
            return None
    
    def authenticate_docker(self) -> bool:
        """Authenticate Docker with ECR."""
        token = self.get_authorization_token()
        if not token:
            return False
        
        registry = self.registry_url
        if not registry:
            log_error("Could not determine ECR registry URL")
            return False
        
        try:
            # Login to Docker
            cmd = ['docker', 'login', '--username', 'AWS', '--password-stdin', registry]
            process = subprocess.Popen(
                cmd, 
                stdin=subprocess.PIPE, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate(input=token.encode())
            
            if process.returncode == 0:
                log_info("✓ Docker authenticated with ECR")
                return True
            else:
                log_error(f"Failed to authenticate Docker with ECR: {stderr.decode()}")
                return False
        except Exception as e:
            log_error(f"Failed to authenticate Docker with ECR: {e}")
            return False
    
    def list_repositories(self) -> List[Dict[str, Any]]:
        """List all ECR repositories."""
        repositories = []
        try:
            paginator = self.ecr_client.get_paginator('describe_repositories')
            for page in paginator.paginate():
                repositories.extend(page['repositories'])
            return repositories
        except Exception as e:
            log_error(f"Failed to list ECR repositories: {e}")
            return []
    
    def get_repository_info(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a repository."""
        try:
            response = self.ecr_client.describe_repositories(
                repositoryNames=[repo_name]
            )
            return response['repositories'][0] if response['repositories'] else None
        except ClientError as e:
            if e.response['Error']['Code'] != 'RepositoryNotFoundException':
                log_error(f"Failed to get repository info: {e}")
            return None
    
    def list_images(self, repo_name: str) -> List[Dict[str, Any]]:
        """List all images in a repository."""
        images = []
        try:
            paginator = self.ecr_client.get_paginator('list_images')
            for page in paginator.paginate(repositoryName=repo_name):
                images.extend(page.get('imageIds', []))
            return images
        except Exception as e:
            log_error(f"Failed to list images in repository '{repo_name}': {e}")
            return []