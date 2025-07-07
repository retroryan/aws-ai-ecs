"""
ECS and ECR utility functions.
Replaces ecs-utils.sh functionality with Python implementation.
"""

import time
import json
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta

import boto3
import requests
from botocore.exceptions import ClientError

from .common import (
    log_info, log_warn, log_error, log_step,
    config, get_aws_region
)


class ECSUtils:
    """Utilities for ECS operations."""
    
    def __init__(self, region: Optional[str] = None):
        """Initialize ECS utilities with specified region."""
        self.region = region or get_aws_region()
        self.ecs_client = boto3.client('ecs', region_name=self.region)
        self.ecr_client = boto3.client('ecr', region_name=self.region)
        self.logs_client = boto3.client('logs', region_name=self.region)
    
    # =====================================================================
    # ECR Repository Management
    # =====================================================================
    
    def ensure_ecr_repositories_exist(
        self,
        repositories: List[str],
        region: Optional[str] = None
    ) -> bool:
        """
        Ensure ECR repositories exist.
        
        Args:
            repositories: List of repository names to create
            region: AWS region (uses instance region if not specified)
            
        Returns:
            True if all repositories exist or were created successfully
        """
        region = region or self.region
        log_info("Ensuring ECR repositories exist...")
        
        success = True
        for repo in repositories:
            if not self._create_ecr_repository_if_not_exists(repo, region):
                success = False
        
        if success:
            log_info("ECR repositories are ready")
        return success
    
    def _create_ecr_repository_if_not_exists(
        self,
        repo_name: str,
        region: Optional[str] = None
    ) -> bool:
        """Create ECR repository if it doesn't exist."""
        try:
            self.ecr_client.describe_repositories(repositoryNames=[repo_name])
            log_info(f"ECR repository '{repo_name}' already exists")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'RepositoryNotFoundException':
                try:
                    self.ecr_client.create_repository(repositoryName=repo_name)
                    log_info(f"✓ Created ECR repository '{repo_name}'")
                    return True
                except Exception as create_error:
                    log_error(f"Failed to create ECR repository '{repo_name}': {create_error}")
                    return False
            else:
                log_error(f"Error checking repository '{repo_name}': {e}")
                return False
    
    # =====================================================================
    # ECS Service Operations
    # =====================================================================
    
    def update_service_desired_count(
        self,
        service_name: str,
        desired_count: int,
        cluster_name: str,
        region: Optional[str] = None
    ) -> bool:
        """
        Update ECS service desired count.
        
        Args:
            service_name: Name of the ECS service
            desired_count: Desired number of tasks
            cluster_name: ECS cluster name
            region: AWS region
            
        Returns:
            True if update was successful
        """
        log_info(f"Updating {service_name} desired count to {desired_count}")
        
        try:
            response = self.ecs_client.update_service(
                cluster=cluster_name,
                service=service_name,
                desiredCount=desired_count
            )
            
            actual_count = response['service']['desiredCount']
            if actual_count == desired_count:
                log_info(f"✓ Successfully updated {service_name} desired count to {desired_count}")
                return True
            else:
                log_error(f"Failed to update desired count for {service_name}: got {actual_count}")
                return False
                
        except Exception as e:
            log_error(f"Failed to update desired count for {service_name}: {e}")
            return False
    
    def get_recent_tasks(
        self,
        service_name: str,
        desired_status: str = 'RUNNING',
        cluster_name: Optional[str] = None,
        max_items: int = 10
    ) -> List[str]:
        """
        Get recent tasks for a service.
        
        Args:
            service_name: ECS service name
            desired_status: Task status to filter by (RUNNING, STOPPED, etc.)
            cluster_name: ECS cluster name
            max_items: Maximum number of tasks to return
            
        Returns:
            List of task ARNs
        """
        cluster_name = cluster_name or config.DEFAULT_CLUSTER_NAME
        
        try:
            response = self.ecs_client.list_tasks(
                cluster=cluster_name,
                serviceName=service_name,
                desiredStatus=desired_status,
                maxResults=max_items
            )
            return response.get('taskArns', [])
        except Exception as e:
            log_error(f"Error getting tasks for {service_name}: {e}")
            return []
    
    def check_service_status(
        self,
        service_name: str,
        cluster_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get ECS service status information.
        
        Args:
            service_name: ECS service name
            cluster_name: ECS cluster name
            
        Returns:
            Service information dict or empty dict if not found
        """
        cluster_name = cluster_name or config.DEFAULT_CLUSTER_NAME
        
        try:
            response = self.ecs_client.describe_services(
                cluster=cluster_name,
                services=[service_name]
            )
            
            if response['services']:
                return response['services'][0]
            return {}
        except Exception:
            return {}
    
    # =====================================================================
    # ECS Health Monitoring
    # =====================================================================
    
    def check_task_health(
        self,
        service_name: str,
        service_type: str,
        cluster_name: Optional[str] = None
    ) -> bool:
        """
        Check health of tasks for a service.
        
        Args:
            service_name: ECS service name
            service_type: Type of service (for logging)
            cluster_name: ECS cluster name
            
        Returns:
            True if all tasks are healthy
        """
        cluster_name = cluster_name or config.DEFAULT_CLUSTER_NAME
        task_arns = self.get_recent_tasks(service_name, 'RUNNING', cluster_name)
        
        if not task_arns:
            log_warn(f"No running tasks found for {service_type}")
            return False
        
        try:
            response = self.ecs_client.describe_tasks(
                cluster=cluster_name,
                tasks=task_arns
            )
            
            total_tasks = 0
            healthy_tasks = 0
            
            for task in response.get('tasks', []):
                total_tasks += 1
                task_arn = task['taskArn']
                last_status = task.get('lastStatus', 'UNKNOWN')
                health_status = task.get('healthStatus', 'UNKNOWN')
                
                log_info(f"Task {task_arn.split('/')[-1]}: Status={last_status}, Health={health_status}")
                
                if last_status == 'RUNNING':
                    # Check container statuses
                    all_containers_healthy = True
                    
                    for container in task.get('containers', []):
                        container_name = container['name']
                        container_status = container.get('lastStatus', 'UNKNOWN')
                        exit_code = container.get('exitCode')
                        
                        if container_status != 'RUNNING' or (exit_code is not None and exit_code != 0):
                            log_warn(f"Container {container_name} is not healthy: "
                                   f"status={container_status}, exit_code={exit_code}")
                            all_containers_healthy = False
                            break
                    
                    if all_containers_healthy:
                        healthy_tasks += 1
            
            log_info(f"{service_type}: {healthy_tasks}/{total_tasks} tasks are healthy")
            
            return healthy_tasks == total_tasks and total_tasks > 0
            
        except Exception as e:
            log_error(f"Error checking task health: {e}")
            return False
    
    def capture_service_logs(
        self,
        service_type: str,
        log_group: str,
        since_minutes: int = 5,
        limit: int = 50
    ) -> None:
        """
        Capture and display recent service logs.
        
        Args:
            service_type: Type of service (for display)
            log_group: CloudWatch log group name
            since_minutes: How many minutes back to look
            limit: Maximum number of log entries to retrieve
        """
        log_info(f"=== Recent {service_type} Logs ===")
        
        try:
            # Calculate start time
            start_time = datetime.now() - timedelta(minutes=since_minutes)
            start_time_ms = int(start_time.timestamp() * 1000)
            
            # Get log streams
            response = self.logs_client.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=5
            )
            
            if not response.get('logStreams'):
                log_warn(f"No log streams found for {service_type}")
                return
            
            stream_name = response['logStreams'][0]['logStreamName']
            
            # Get recent events
            events_response = self.logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                startTime=start_time_ms,
                limit=limit
            )
            
            # Display last 20 events
            events = events_response.get('events', [])[-20:]
            for event in events:
                log_info(event['message'])
                
        except Exception as e:
            log_warn(f"Error retrieving logs for {service_type}: {e}")
    
    def wait_for_service_stable(
        self,
        service_name: str,
        service_type: str,
        timeout: int,
        cluster_name: Optional[str] = None,
        check_interval: int = 10
    ) -> bool:
        """
        Wait for ECS service to become stable.
        
        Args:
            service_name: ECS service name
            service_type: Type of service (for logging)
            timeout: Maximum time to wait in seconds
            cluster_name: ECS cluster name
            check_interval: Seconds between checks
            
        Returns:
            True if service becomes stable within timeout
        """
        cluster_name = cluster_name or config.DEFAULT_CLUSTER_NAME
        log_info(f"Waiting for {service_type} service ({service_name}) to become stable...")
        
        start_time = time.time()
        last_event_count = 0
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                log_error(f"{service_type} service did not stabilize within {timeout} seconds")
                return False
            
            # Get service status
            service_info = self.check_service_status(service_name, cluster_name)
            
            if not service_info:
                log_error(f"Failed to get status for {service_type}")
                return False
            
            running_count = service_info.get('runningCount', 0)
            desired_count = service_info.get('desiredCount', 0)
            pending_count = service_info.get('pendingCount', 0)
            deployments = len(service_info.get('deployments', []))
            
            log_info(f"[{service_type}] Running: {running_count}/{desired_count}, "
                    f"Pending: {pending_count}, Active deployments: {deployments}")
            
            # Log new events
            events = service_info.get('events', [])[:5]
            if len(events) > last_event_count:
                for event in events[last_event_count:]:
                    log_info(f"[{service_type} Event] {event['message']}")
                last_event_count = len(events)
            
            # Special case: if desired count is 0, skip stability check
            if desired_count == 0:
                log_info(f"{service_type} service has desired count of 0, skipping stability check")
                return True
            
            # Check if service is stable
            if (running_count == desired_count and 
                running_count > 0 and 
                deployments == 1 and 
                pending_count == 0):
                
                log_info(f"{service_type} service appears stable, checking task health...")
                
                # Additional health check
                if self.check_task_health(service_name, service_type, cluster_name):
                    log_info(f"✓ {service_type} service is healthy!")
                    return True
                else:
                    log_warn(f"{service_type} tasks are not all healthy yet")
            
            # Check for failed tasks
            stopped_tasks = self.get_recent_tasks(service_name, 'STOPPED', cluster_name)
            if stopped_tasks:
                log_warn(f"Found {len(stopped_tasks)} stopped tasks for {service_type}")
                
                # Get details of stopped tasks (first 2 only)
                try:
                    stopped_info = self.ecs_client.describe_tasks(
                        cluster=cluster_name,
                        tasks=stopped_tasks[:2]
                    )
                    
                    for task in stopped_info.get('tasks', []):
                        stopped_reason = task.get('stoppedReason', 'Unknown')
                        log_warn(f"Stopped task reason: {stopped_reason}")
                        
                        for container in task.get('containers', []):
                            name = container['name']
                            exit_code = container.get('exitCode', 'N/A')
                            log_warn(f"  Container {name}: exit_code={exit_code}")
                            
                except Exception as e:
                    log_warn(f"Error getting stopped task details: {e}")
            
            time.sleep(check_interval)
    
    def check_health_endpoint(
        self,
        alb_dns: str,
        health_check_timeout: int = 30
    ) -> bool:
        """
        Check ALB health endpoint.
        
        Args:
            alb_dns: ALB DNS name
            health_check_timeout: Timeout for health check request
            
        Returns:
            True if health check passes
        """
        url = f"http://{alb_dns}/health"
        log_info(f"Checking health endpoint: {url}")
        
        try:
            response = requests.get(url, timeout=health_check_timeout)
            
            if response.status_code == 200:
                log_info(f"✓ Health check passed: {response.text}")
                return True
            else:
                log_warn(f"Health check returned status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            log_warn(f"Health check timed out after {health_check_timeout} seconds")
            return False
        except Exception as e:
            log_warn(f"Health check failed: {e}")
            return False


# Create a singleton instance for convenience
ecs_utils = ECSUtils()