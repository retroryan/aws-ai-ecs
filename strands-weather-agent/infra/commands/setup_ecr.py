#!/usr/bin/env python3
"""
Setup ECR repositories and Docker authentication for Strands Weather Agent ECS deployment.
"""

import sys
from pathlib import Path
from typing import List, Tuple

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils import (
    log_info, log_warn, log_error, print_section,
    check_aws_cli, check_aws_credentials, check_docker,
    get_aws_region, get_aws_account_id, get_ecr_registry,
    check_ecr_repository, create_ecr_repository,
    authenticate_docker_ecr, config
)
from utils.docker_utils import docker_utils


console = Console()


def delete_ecr_repository(repo_name: str, region: str) -> bool:
    """
    Delete an ECR repository.
    
    Args:
        repo_name: Repository name to delete
        region: AWS region
        
    Returns:
        True if deletion was successful or repo doesn't exist
    """
    try:
        import boto3
        ecr = boto3.client('ecr', region_name=region)
        ecr.delete_repository(repositoryName=repo_name, force=True)
        console.print(f"✅ Deleted", style="green")
        return True
    except Exception as e:
        if 'RepositoryNotFoundException' in str(e):
            console.print(f"⚠️  Repository doesn't exist", style="yellow")
            return True
        else:
            console.print(f"❌ Failed to delete: {e}", style="red")
            return False


def setup_repositories(repos: List[str], region: str) -> Tuple[int, int]:
    """
    Check and create ECR repositories.
    
    Args:
        repos: List of repository names
        region: AWS region
        
    Returns:
        Tuple of (created_count, existing_count)
    """
    created = 0
    existing = 0
    
    for repo in repos:
        console.print(f"Repository {repo}: ", end="")
        
        if check_ecr_repository(repo, region):
            console.print("✅ Already exists", style="green")
            existing += 1
        else:
            if create_ecr_repository(repo, region):
                created += 1
            else:
                raise Exception(f"Failed to create repository {repo}")
    
    return created, existing


def delete_repositories(repos: List[str], region: str) -> None:
    """Delete ECR repositories with confirmation."""
    console.print("🗑️  DELETE MODE - Removing ECR repositories", style="red bold")
    console.print()
    
    # Show repositories to delete
    console.print("⚠️  This will delete the following repositories:", style="yellow")
    for repo in repos:
        console.print(f"   - {repo}")
    console.print()
    
    # Confirm deletion
    if not Confirm.ask("Are you sure you want to delete these repositories?"):
        console.print("Deletion cancelled")
        return
    
    # Delete repositories
    for repo in repos:
        console.print(f"Deleting repository {repo}... ", end="")
        delete_ecr_repository(repo, region)


@click.command()
@click.option('--delete', is_flag=True, help='Remove the ECR repositories')
@click.option('--region', help='AWS region', default=None)
def main(delete: bool, region: str):
    """Setup ECR repositories and Docker authentication for Strands Weather Agent ECS deployment.
    
    This script will:
    - Create ECR repositories if they don't exist
    - Authenticate Docker with ECR
    - Can be run multiple times safely
    """
    
    console.print("=" * 50, style="blue")
    console.print("ECR Setup for Strands Weather Agent ECS", style="bold cyan")
    console.print("=" * 50, style="blue")
    console.print()
    
    # Check required tools
    if not all([check_aws_cli(), check_aws_credentials(), check_docker()]):
        sys.exit(1)
    
    # Get AWS configuration
    current_region = region or get_aws_region()
    account_id = get_aws_account_id()
    
    if not account_id:
        log_error("Unable to get AWS account ID")
        sys.exit(1)
    
    if current_region == "not set":
        log_error("AWS region is not set")
        log_warn("Set region with: export AWS_REGION=us-east-1")
        sys.exit(1)
    
    console.print("📋 AWS Configuration:", style="bold")
    console.print("-" * 20)
    console.print(f"Account ID: {account_id}")
    console.print(f"Region: {current_region}")
    console.print()
    
    # Get repository list from config
    repos = config.ecr.all_repos
    
    if delete:
        # Delete mode
        delete_repositories(repos, current_region)
        console.print()
        console.print("=" * 50, style="blue")
        console.print("✨ Deletion complete!", style="bold green")
        console.print("=" * 50, style="blue")
        return
    
    # Normal mode - Create repositories and authenticate
    
    # Step 1: Check and create repositories
    console.print("📦 Step 1: Checking ECR repositories", style="bold")
    console.print("-" * 35)
    
    try:
        created, existing = setup_repositories(repos, current_region)
        
        console.print()
        if created > 0:
            console.print(f"Created {created} new repository(ies)", style="green")
        if existing > 0:
            console.print(f"Found {existing} existing repository(ies)", style="blue")
    except Exception as e:
        log_error(f"Failed to setup repositories: {e}")
        sys.exit(1)
    
    # Step 2: Authenticate Docker with ECR
    console.print()
    console.print("🔐 Step 2: Authenticating Docker with ECR", style="bold")
    console.print("-" * 40)
    
    ecr_registry = get_ecr_registry()
    if not ecr_registry:
        log_error("Unable to determine ECR registry")
        sys.exit(1)
    
    if not authenticate_docker_ecr(current_region):
        sys.exit(1)
    
    # Step 3: Display repository information
    console.print()
    console.print("📋 Repository Information", style="bold")
    console.print("-" * 24)
    
    # Create a table for better display
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Repository", style="cyan")
    table.add_column("URI", style="green")
    
    for repo in repos:
        repo_uri = f"{ecr_registry}/{repo}"
        table.add_row(repo, repo_uri)
    
    console.print(table)
    
    # Step 4: Show next steps
    console.print()
    console.print("✅ Setup Complete!", style="bold green")
    console.print("=" * 18, style="green")
    console.print()
    console.print("Next steps:", style="bold")
    console.print()
    console.print("1. Build and push Docker images:", style="blue")
    console.print("   python scripts/build_push.py", style="blue")
    console.print()
    console.print("2. Deploy infrastructure:", style="blue")
    console.print("   python scripts/deploy.py all", style="blue")
    console.print()
    console.print("💡 Tip: You can run this script again anytime to refresh your Docker ECR authentication", 
                 style="green")


if __name__ == '__main__':
    main()