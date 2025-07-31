#!/usr/bin/env python3
"""
Clean up AWS resources for Strands Weather Agent.
"""

import sys
from typing import Optional

import click
import boto3
from botocore.exceptions import ClientError

from infrastructure import get_config
from infrastructure.utils.logging import log_info, log_warn, log_error, print_section
from infrastructure.utils.console import spinner, print_success, print_error, confirm
from infrastructure.aws.ecr import ECRManager


class Cleanup:
    """Clean up AWS resources."""
    
    def __init__(self):
        """Initialize cleanup."""
        self.config = get_config()
        self.region = self.config.aws.region
        self.ecr_manager = ECRManager(self.region)
        
        # Initialize boto3 clients
        self.cfn = boto3.client('cloudformation', region_name=self.region)
    
    def delete_stack(self, stack_name: str) -> bool:
        """Delete a CloudFormation stack."""
        try:
            # Check if stack exists
            self.cfn.describe_stacks(StackName=stack_name)
        except ClientError as e:
            if 'does not exist' in str(e):
                log_info(f"Stack {stack_name} does not exist")
                return True
            raise
        
        try:
            with spinner(f"Deleting stack {stack_name}..."):
                self.cfn.delete_stack(StackName=stack_name)
                
                # Wait for deletion
                waiter = self.cfn.get_waiter('stack_delete_complete')
                log_info(f"Waiting for {stack_name} deletion to complete...")
                waiter.wait(StackName=stack_name)
            
            print_success(f"Stack {stack_name} deleted successfully!")
            return True
            
        except Exception as e:
            print_error(f"Failed to delete stack {stack_name}: {e}")
            return False
    
    def delete_ecr_repositories(self) -> bool:
        """Delete all ECR repositories."""
        repositories = self.config.ecr.all_repos
        
        all_success = True
        for repo in repositories:
            try:
                with spinner(f"Deleting ECR repository {repo}..."):
                    self.ecr_manager.delete_repository(repo, force=True)
                print_success(f"Deleted ECR repository {repo}")
            except Exception as e:
                print_error(f"Failed to delete ECR repository {repo}: {e}")
                all_success = False
        
        return all_success
    
    def cleanup_stacks(self) -> bool:
        """Delete CloudFormation stacks in correct order."""
        print_section("Cleaning Up CloudFormation Stacks")
        
        # Delete services stack first (depends on base)
        if not self.delete_stack(self.config.stacks.services_stack_name):
            log_error("Failed to delete services stack")
            return False
        
        # Delete base stack
        if not self.delete_stack(self.config.stacks.base_stack_name):
            log_error("Failed to delete base stack")
            return False
        
        return True
    
    def cleanup_all(self) -> bool:
        """Clean up all resources."""
        print_section("Full Cleanup")
        
        log_warn("This will delete all AWS resources created by this deployment!")
        log_warn("This action cannot be undone.")
        
        if not confirm("Are you sure you want to continue?"):
            log_info("Cleanup cancelled")
            return False
        
        # Clean up stacks
        if not self.cleanup_stacks():
            return False
        
        # Clean up ECR repositories
        if confirm("Delete ECR repositories and all Docker images?"):
            if not self.delete_ecr_repositories():
                log_warn("Some ECR repositories may not have been deleted")
        
        print_success("Cleanup completed!")
        return True
    
    def cleanup_images(self) -> bool:
        """Clean up only Docker images from ECR."""
        print_section("Cleaning Up Docker Images")
        
        repositories = self.config.ecr.all_repos
        
        for repo in repositories:
            images = self.ecr_manager.list_images(repo)
            if images:
                log_info(f"Found {len(images)} images in {repo}")
                if confirm(f"Delete all images from {repo}?"):
                    # Note: This is a simplified version. In production, you'd want
                    # to implement batch deletion of images
                    log_warn("Image deletion not implemented in this demo")
            else:
                log_info(f"No images found in {repo}")
        
        return True


@click.command()
@click.argument('target', default='all', type=click.Choice(['all', 'stacks', 'images']))
@click.option('--force', is_flag=True, help='Skip confirmation prompts')
@click.option('--region', help='AWS region', envvar='AWS_REGION')
def main(target: str, force: bool, region: Optional[str] = None):
    """Clean up AWS resources for Strands Weather Agent.
    
    Targets:
      all     - Delete all resources (stacks and ECR repositories)
      stacks  - Delete only CloudFormation stacks
      images  - Delete only Docker images from ECR
    """
    try:
        # Override region if provided
        if region:
            config = get_config()
            config.aws.region = region
        
        cleanup = Cleanup()
        
        # Handle force flag by monkey-patching confirm
        if force:
            import infrastructure.utils.console
            infrastructure.utils.console.confirm = lambda msg, default=False: True
        
        if target == 'all':
            success = cleanup.cleanup_all()
        elif target == 'stacks':
            success = cleanup.cleanup_stacks()
        elif target == 'images':
            success = cleanup.cleanup_images()
        else:
            print_error(f"Unknown target: {target}")
            success = False
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print_error("\nCleanup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Cleanup failed: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()