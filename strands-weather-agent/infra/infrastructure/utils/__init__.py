"""
General utility functions.
"""

from .logging import (
    logger,
    setup_logging,
    log_info,
    log_warn,
    log_error,
    log_step,
    print_section,
    get_timestamp
)

from .console import (
    console,
    spinner,
    with_progress,
    create_table,
    print_success,
    print_error,
    print_warning,
    confirm
)

from .validation import (
    check_aws_cli,
    check_aws_credentials,
    check_docker,
    check_python,
    check_jq,
    check_bedrock_access,
    ensure_project_root,
    validate_deployment_prerequisites
)

__all__ = [
    # Logging
    'logger',
    'setup_logging',
    'log_info',
    'log_warn',
    'log_error',
    'log_step',
    'print_section',
    'get_timestamp',
    
    # Console
    'console',
    'spinner',
    'with_progress',
    'create_table',
    'print_success',
    'print_error',
    'print_warning',
    'confirm',
    
    # Validation
    'check_aws_cli',
    'check_aws_credentials',
    'check_docker',
    'check_python',
    'check_jq',
    'check_bedrock_access',
    'ensure_project_root',
    'validate_deployment_prerequisites'
]