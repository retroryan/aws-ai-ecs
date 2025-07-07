"""
Docker utility functions for building and pushing images.
"""

import os
import subprocess
import json
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime

import docker
from docker.errors import BuildError, APIError, DockerException

from .common import log_info, log_warn, log_error, log_step
from .aws_utils import aws_utils


class DockerUtils:
    """Docker utilities for building and managing containers."""
    
    def __init__(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
            self.docker_available = True
        except DockerException as e:
            log_error(f"Failed to initialize Docker client: {e}")
            self.docker_available = False
    
    def check_docker(self) -> bool:
        """Check if Docker is available and running."""
        if not self.docker_available:
            log_error("Docker client not initialized")
            return False
        
        try:
            self.client.ping()
            return True
        except Exception as e:
            log_error(f"Docker is not running or accessible: {e}")
            log_warn("Please start Docker Desktop or Docker daemon")
            return False
    
    def build_image(
        self,
        path: str,
        tag: str,
        dockerfile: str = 'Dockerfile',
        platform: str = 'linux/amd64',
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = False
    ) -> bool:
        """
        Build a Docker image.
        
        Args:
            path: Build context path
            tag: Image tag
            dockerfile: Dockerfile name
            platform: Target platform
            build_args: Build arguments
            no_cache: Whether to use cache
            
        Returns:
            True if build was successful
        """
        if not self.check_docker():
            return False
        
        log_info(f"Building Docker image: {tag}")
        log_info(f"Build context: {path}")
        log_info(f"Platform: {platform}")
        
        try:
            # Use subprocess for better platform support
            cmd = [
                'docker', 'build',
                '--platform', platform,
                '-t', tag,
                '-f', dockerfile
            ]
            
            if no_cache:
                cmd.append('--no-cache')
            
            if build_args:
                for key, value in build_args.items():
                    cmd.extend(['--build-arg', f'{key}={value}'])
            
            cmd.append(path)
            
            # Run build command
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                log_info(f"✓ Successfully built image: {tag}")
                return True
            else:
                log_error(f"Failed to build image: {process.stderr}")
                return False
                
        except Exception as e:
            log_error(f"Error building image: {e}")
            return False
    
    def tag_image(self, source_tag: str, target_tag: str) -> bool:
        """Tag a Docker image."""
        if not self.check_docker():
            return False
        
        try:
            image = self.client.images.get(source_tag)
            image.tag(target_tag)
            log_info(f"✓ Tagged {source_tag} as {target_tag}")
            return True
        except Exception as e:
            log_error(f"Failed to tag image: {e}")
            return False
    
    def push_image(self, tag: str, auth_config: Optional[Dict[str, str]] = None) -> bool:
        """
        Push Docker image to registry.
        
        Args:
            tag: Image tag to push
            auth_config: Authentication configuration
            
        Returns:
            True if push was successful
        """
        if not self.check_docker():
            return False
        
        log_info(f"Pushing image: {tag}")
        
        try:
            # Use subprocess for more reliable pushing
            cmd = ['docker', 'push', tag]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                log_info(f"✓ Successfully pushed image: {tag}")
                return True
            else:
                log_error(f"Failed to push image: {process.stderr}")
                return False
                
        except Exception as e:
            log_error(f"Error pushing image: {e}")
            return False
    
    def login_ecr(self, region: str, registry: str) -> bool:
        """
        Login to Amazon ECR.
        
        Args:
            region: AWS region
            registry: ECR registry URL
            
        Returns:
            True if login was successful
        """
        log_info("Authenticating Docker with ECR...")
        
        try:
            # Get ECR authorization token
            ecr_client = aws_utils.get_client('ecr', region)
            response = ecr_client.get_authorization_token()
            
            # Extract token
            auth_data = response['authorizationData'][0]
            token = auth_data['authorizationToken']
            
            # Login using docker CLI (more reliable than SDK)
            cmd = ['docker', 'login', '--username', 'AWS', '--password-stdin', registry]
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=token)
            
            if process.returncode == 0:
                log_info("✓ Docker authenticated with ECR")
                return True
            else:
                log_error(f"Failed to authenticate Docker with ECR: {stderr}")
                return False
                
        except Exception as e:
            log_error(f"Error authenticating with ECR: {e}")
            return False
    
    def image_exists_locally(self, tag: str) -> bool:
        """Check if Docker image exists locally."""
        if not self.check_docker():
            return False
        
        try:
            self.client.images.get(tag)
            return True
        except docker.errors.ImageNotFound:
            return False
        except Exception as e:
            log_warn(f"Error checking image existence: {e}")
            return False
    
    def remove_image(self, tag: str, force: bool = False) -> bool:
        """Remove a Docker image."""
        if not self.check_docker():
            return False
        
        try:
            self.client.images.remove(tag, force=force)
            log_info(f"✓ Removed image: {tag}")
            return True
        except docker.errors.ImageNotFound:
            log_warn(f"Image not found: {tag}")
            return True  # Not an error if already removed
        except Exception as e:
            log_error(f"Failed to remove image: {e}")
            return False
    
    def get_image_info(self, tag: str) -> Optional[Dict]:
        """Get information about a Docker image."""
        if not self.check_docker():
            return None
        
        try:
            image = self.client.images.get(tag)
            return {
                'id': image.id,
                'tags': image.tags,
                'size': image.attrs['Size'],
                'created': image.attrs['Created'],
                'architecture': image.attrs.get('Architecture', 'unknown'),
                'os': image.attrs.get('Os', 'unknown')
            }
        except Exception as e:
            log_error(f"Error getting image info: {e}")
            return None
    
    def cleanup_old_images(self, repository: str, keep_last: int = 5) -> None:
        """
        Clean up old Docker images from a repository.
        
        Args:
            repository: Repository name (without tag)
            keep_last: Number of recent images to keep
        """
        if not self.check_docker():
            return
        
        try:
            # Get all images for the repository
            images = []
            for image in self.client.images.list():
                for tag in image.tags:
                    if tag.startswith(f"{repository}:"):
                        images.append({
                            'tag': tag,
                            'created': image.attrs['Created'],
                            'id': image.id
                        })
            
            # Sort by creation date
            images.sort(key=lambda x: x['created'], reverse=True)
            
            # Remove old images
            for image in images[keep_last:]:
                log_info(f"Removing old image: {image['tag']}")
                self.remove_image(image['tag'], force=True)
                
        except Exception as e:
            log_warn(f"Error cleaning up old images: {e}")
    
    def build_and_push(
        self,
        context_path: str,
        repository: str,
        tag: str,
        dockerfile: str = 'Dockerfile',
        platform: str = 'linux/amd64',
        build_args: Optional[Dict[str, str]] = None,
        region: Optional[str] = None,
        no_cache: bool = False
    ) -> bool:
        """
        Build and push a Docker image to ECR.
        
        Args:
            context_path: Build context path
            repository: ECR repository URL
            tag: Image tag
            dockerfile: Dockerfile name
            platform: Target platform
            build_args: Build arguments
            region: AWS region
            no_cache: Whether to use cache
            
        Returns:
            True if both build and push were successful
        """
        full_tag = f"{repository}:{tag}"
        
        # Build image
        if not self.build_image(
            path=context_path,
            tag=full_tag,
            dockerfile=dockerfile,
            platform=platform,
            build_args=build_args,
            no_cache=no_cache
        ):
            return False
        
        # Login to ECR if repository is ECR
        if '.dkr.ecr.' in repository:
            # Extract registry from repository URL
            registry = repository.split('/')[0]
            region = region or registry.split('.')[3]
            
            if not self.login_ecr(region, registry):
                return False
        
        # Push image
        return self.push_image(full_tag)


# Create a singleton instance for convenience
docker_utils = DockerUtils()