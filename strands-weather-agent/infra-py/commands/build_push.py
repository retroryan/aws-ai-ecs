#!/usr/bin/env python3
"""
Build and push Docker images for Strands Weather Agent to Amazon ECR.
Builds for AMD64/x86_64 architecture (required for ECS Fargate).
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time
import os

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from infrastructure.config import config
from infrastructure.utils.logging import log_info, log_warn, log_error, print_section
from infrastructure.utils.validation import check_aws_cli, check_aws_credentials, check_docker
from infrastructure.aws.common import (
    get_aws_region, get_aws_account_id, get_ecr_registry,
    check_ecr_repository, authenticate_docker_ecr
)
from infrastructure.aws.ecr import ECRManager


console = Console()

# Components to build
COMPONENTS = ["main", "forecast", "historical", "agricultural"]


class ImageBuilder:
    """Handles Docker image building and pushing."""
    
    def __init__(self, logs_dir: Path):
        """Initialize builder with logs directory."""
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.version_tag = self._generate_version_tag()
        self.build_failed = False
        
    def _generate_version_tag(self) -> str:
        """Generate version tag based on git commit and timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        
        try:
            # Get git commit hash
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                git_commit = result.stdout.strip()
            else:
                git_commit = "unknown"
        except Exception:
            git_commit = "unknown"
        
        return f"{git_commit}-{timestamp}"
    
    def build_image(
        self,
        component: str,
        image_name: str,
        dockerfile: Path,
        progress: Progress,
        task_id
    ) -> bool:
        """Build a Docker image with progress tracking."""
        log_file = self.logs_dir / f"build-{component}.log"
        
        try:
            # Build command - use parent directory as build context
            build_context = Path(__file__).parent.parent.parent
            cmd = [
                'docker', 'build',
                '--platform', 'linux/amd64',
                '-t', f"{image_name}:{self.version_tag}",
                '-f', str(dockerfile),
                str(build_context)
            ]
            
            # Run build with output to log file
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # Wait for completion with progress updates
                while process.poll() is None:
                    time.sleep(0.5)
                
                if process.returncode == 0:
                    progress.update(task_id, description=f"[green]✓[/green] Built {component}")
                    
                    # Tag as latest
                    subprocess.run([
                        'docker', 'tag',
                        f"{image_name}:{self.version_tag}",
                        f"{image_name}:latest"
                    ], check=True)
                    return True
                else:
                    progress.update(task_id, description=f"[red]✗[/red] Failed to build {component}")
                    return False
                    
        except Exception as e:
            progress.update(task_id, description=f"[red]✗[/red] Error building {component}")
            log_error(f"Error building {component}: {e}")
            return False
    
    def push_image(
        self,
        component: str,
        image_name: str,
        progress: Progress,
        task_id
    ) -> bool:
        """Push Docker image to ECR with progress tracking."""
        log_file = self.logs_dir / f"push-{component}.log"
        
        try:
            # Push version tag
            with open(log_file, 'w') as log:
                # Push versioned image
                cmd_version = ['docker', 'push', f"{image_name}:{self.version_tag}"]
                process_version = subprocess.Popen(
                    cmd_version,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                while process_version.poll() is None:
                    time.sleep(0.5)
                
                if process_version.returncode != 0:
                    progress.update(task_id, description=f"[red]✗[/red] Failed to push {component}")
                    
                    # Check for auth expiry
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                        if "authorization token has expired" in log_content.lower():
                            log_error("Docker authentication token has expired!")
                            log_warn("Please run: python scripts/setup_ecr.py")
                    return False
                
                # Push latest tag
                cmd_latest = ['docker', 'push', f"{image_name}:latest"]
                process_latest = subprocess.Popen(
                    cmd_latest,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                while process_latest.poll() is None:
                    time.sleep(0.5)
                
                if process_latest.returncode == 0:
                    progress.update(task_id, description=f"[green]✓[/green] Pushed {component}")
                    return True
                else:
                    progress.update(task_id, description=f"[red]✗[/red] Failed to push {component} latest")
                    return False
                    
        except Exception as e:
            progress.update(task_id, description=f"[red]✗[/red] Error pushing {component}")
            log_error(f"Error pushing {component}: {e}")
            return False
    
    def save_image_tags(self, ecr_registry: str, components: List[str]) -> None:
        """Save image tags to .image-tags file for deployment."""
        tags_file = Path(__file__).parent.parent / '.image-tags'
        
        with open(tags_file, 'w') as f:
            # Write component tags
            for component in components:
                key = f"{component.upper()}_IMAGE_TAG"
                f.write(f"{key}={self.version_tag}\n")
            
            # Write build metadata
            f.write(f"BUILD_TIMESTAMP={datetime.utcnow().isoformat()}Z\n")
            f.write(f"ECR_REGISTRY={ecr_registry}\n")
            f.write(f"ECR_REPO_PREFIX={config.ecr.repo_prefix}\n")
        
        log_info(f"💾 Saved image tags to {tags_file}")


def validate_environment() -> Tuple[str, str, str]:
    """Validate AWS environment and return configuration."""
    # Check required tools
    if not all([check_aws_cli(), check_aws_credentials(), check_docker()]):
        sys.exit(1)
    
    # Get AWS configuration
    region = config.aws.region
    account_id = get_aws_account_id()
    
    if not account_id:
        log_error("Unable to get AWS account ID")
        sys.exit(1)
    
    if region == "not set":
        log_error("AWS region is not set")
        log_warn("Set region with: export AWS_REGION=us-east-1")
        sys.exit(1)
    
    ecr_registry = get_ecr_registry()
    if not ecr_registry:
        log_error("Unable to determine ECR registry")
        sys.exit(1)
    
    return region, account_id, ecr_registry


def check_ecr_repositories(components: List[str], region: str) -> bool:
    """Check if all required ECR repositories exist."""
    console.print("🔍 Checking ECR repositories...", style="bold")
    console.print("-" * 30)
    
    missing_repos = []
    
    for component in components:
        repo_name = f"{config.ecr.repo_prefix}-{component}"
        
        if check_ecr_repository(repo_name, region):
            console.print(f"Repository {repo_name}: ✅ Exists", style="green")
        else:
            console.print(f"Repository {repo_name}: ❌ Not found", style="red")
            missing_repos.append(repo_name)
    
    if missing_repos:
        console.print()
        log_error(f"Missing ECR repositories: {', '.join(missing_repos)}")
        log_warn("Run 'python scripts/setup_ecr.py' first to create repositories")
        return False
    
    return True


def check_dockerfiles(components: List[str]) -> Dict[str, Path]:
    """Check if all required Dockerfiles exist."""
    dockerfiles = {}
    missing = []
    
    for component in components:
        # Look for Dockerfiles in the parent directory
        dockerfile = Path(__file__).parent.parent.parent / "docker" / f"Dockerfile.{component}"
        if dockerfile.exists():
            dockerfiles[component] = dockerfile
        else:
            missing.append(str(dockerfile))
    
    if missing:
        log_error(f"Missing Dockerfiles: {', '.join(missing)}")
        return {}
    
    return dockerfiles


@click.command()
@click.option('--components', '-c', multiple=True, help='Specific components to build')
@click.option('--skip-push', is_flag=True, help='Build only, do not push')
@click.option('--force-auth', is_flag=True, help='Force ECR re-authentication')
@click.option('--clean-logs', is_flag=True, help='Clean log files after success')
def main(components: tuple, skip_push: bool, force_auth: bool, clean_logs: bool):
    """Build and push Docker images for Strands Weather Agent to ECR."""
    
    console.print("=" * 50, style="blue")
    console.print("Build & Push Strands Weather Agent Images to ECR", style="bold cyan")
    console.print("=" * 50, style="blue")
    console.print()
    
    # Use specified components or all
    build_components = list(components) if components else COMPONENTS
    
    # Validate environment
    region, account_id, ecr_registry = validate_environment()
    
    # Initialize builder
    logs_dir = Path(__file__).parent.parent / 'logs'
    builder = ImageBuilder(logs_dir)
    
    # Display configuration
    console.print("📋 Configuration:", style="bold")
    console.print("-" * 16)
    console.print(f"Account ID: {account_id}")
    console.print(f"Region: {region}")
    console.print(f"ECR Registry: {ecr_registry}")
    console.print(f"Version Tag: {builder.version_tag}")
    console.print(f"Components: {', '.join(build_components)}")
    console.print()
    
    # Check ECR repositories
    if not check_ecr_repositories(build_components, region):
        sys.exit(1)
    
    # Check Dockerfiles
    dockerfiles = check_dockerfiles(build_components)
    if not dockerfiles:
        sys.exit(1)
    
    # Authenticate with ECR
    if not skip_push:
        console.print()
        console.print("🔐 Authenticating Docker with ECR...", style="bold")
        console.print("-" * 40)
        
        # Always authenticate with ECR when not skipping push
        if not authenticate_docker_ecr(region):
            log_error("Failed to authenticate Docker with ECR")
            log_warn("Check your AWS credentials and permissions")
            sys.exit(1)
    
    # Build and push images
    console.print()
    console.print("🏗️  Building and pushing Docker images...", style="bold")
    console.print("=" * 40, style="blue")
    
    success_components = []
    failed_components = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
        transient=False
    ) as progress:
        
        for component in build_components:
            console.print(f"\n📦 Processing {component}...")
            console.print("-" * 28)
            
            image_name = f"{ecr_registry}/{config.ecr.repo_prefix}-{component}"
            dockerfile = dockerfiles[component]
            
            # Build image
            build_task = progress.add_task(f"Building {component}...", total=None)
            if builder.build_image(component, image_name, dockerfile, progress, build_task):
                console.print(f"   Image built: {image_name}:{builder.version_tag}")
                
                if not skip_push:
                    # Push image
                    push_task = progress.add_task(f"Pushing {component}...", total=None)
                    if builder.push_image(component, image_name, progress, push_task):
                        console.print(f"   Image URI: {image_name}:{builder.version_tag}")
                        console.print(f"   Also tagged as: {image_name}:latest")
                        success_components.append(component)
                    else:
                        failed_components.append(component)
                        console.print(f"   Check {builder.logs_dir}/push-{component}.log for details", 
                                    style="yellow")
                else:
                    success_components.append(component)
            else:
                failed_components.append(component)
                console.print(f"   Check {builder.logs_dir}/build-{component}.log for details", 
                            style="yellow")
    
    # Clean up logs on success
    if not failed_components and clean_logs:
        console.print()
        console.print("🧹 Cleaning up log files...")
        for log_file in builder.logs_dir.glob("build-*.log"):
            log_file.unlink()
        for log_file in builder.logs_dir.glob("push-*.log"):
            log_file.unlink()
    
    console.print()
    console.print("=" * 50, style="blue")
    
    if failed_components:
        log_error(f"Build/push failed for: {', '.join(failed_components)}")
        log_warn("Check the log files for details")
        sys.exit(1)
    else:
        console.print("✅ All images built and pushed successfully!", style="green bold")
        console.print()
        
        # Display image tags
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Component", style="cyan")
        table.add_column("Image URI", style="green")
        
        for component in success_components:
            image_uri = f"{ecr_registry}/{config.ecr.repo_prefix}-{component}:{builder.version_tag}"
            table.add_row(component, image_uri)
        
        console.print("📝 Image Tags:", style="bold")
        console.print(table)
        
        # Save image tags for deployment
        if not skip_push:
            builder.save_image_tags(ecr_registry, success_components)
        
        console.print()
        console.print("📝 Next steps:", style="bold")
        console.print("-" * 13)
        console.print("Update services with new images:")
        console.print("python deploy.py update-services", style="blue")
        console.print("(This will automatically use the image tags from this build)")
    
    console.print("=" * 50, style="blue")


if __name__ == '__main__':
    main()