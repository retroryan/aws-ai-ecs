# Shell to Python Migration Plan

## Overview
This document tracks the migration of all shell scripts in the infra-py directory to Python. The goal is to create a modern, maintainable Python-based infrastructure management system with no backwards compatibility to shell scripts.

## Migration Principles
1. **Pure Python**: No shell command wrappers, use Python libraries (boto3, docker-py, etc.)
2. **Type Safety**: Use type hints throughout
3. **Error Handling**: Comprehensive exception handling with clear error messages
4. **Modularity**: Shared utilities in dedicated modules
5. **Configuration**: Use dataclasses/pydantic for configuration management
6. **Logging**: Structured logging with Python's logging module
7. **Testing**: Each module should be testable without AWS dependencies

## Directory Structure
```
infra-py/
├── utils/
│   ├── __init__.py
│   ├── common.py          # Core utilities (logging, config)
│   ├── ecs_utils.py       # ECS/ECR operations
│   ├── aws_utils.py       # AWS general utilities
│   └── docker_utils.py    # Docker operations
├── scripts/
│   ├── __init__.py
│   ├── aws_setup.py
│   ├── build_push.py
│   ├── deploy.py
│   ├── status.py
│   ├── test_services.py
│   └── ...
├── shell-bak/             # Migrated shell scripts
├── requirements.txt       # Python dependencies
└── config.py             # Configuration management

```

## Migration Order and Dependencies

### Phase 1: Core Utilities (Foundation)
- [x] Create utils directory structure
- [x] Migrate common.sh → utils/common.py
- [x] Migrate enhanced_logging.sh → Integrate into utils/common.py
- [x] Create utils/config.py for configuration management

### Phase 2: AWS Utilities
- [x] Migrate ecs-utils.sh → utils/ecs_utils.py
- [x] Create utils/aws_utils.py for general AWS operations
- [x] Create utils/docker_utils.py for Docker operations

### Phase 3: Setup and Configuration Scripts
- [x] Migrate aws-checks.sh → scripts/aws_checks.py
- [x] Migrate aws-setup.sh → scripts/aws_setup.py
- [x] Migrate setup-ecr.sh → scripts/setup_ecr.py

### Phase 4: Build and Deployment Scripts
- [x] Migrate build-push.sh → scripts/build_push.py
- [x] Update deploy.py to use Python scripts and config module
- [x] Migrate stack_operations.sh → Integrated into deploy.py

### Phase 5: Monitoring and Testing Scripts
- [ ] Migrate status.sh → scripts/status.py
- [ ] Migrate wait-for-service.sh → scripts/wait_for_service.py
- [ ] Migrate test_services.sh → scripts/test_services.py
- [ ] Migrate multi-turn-test.sh → scripts/multi_turn_test.py
- [ ] Migrate validate_deployment.sh → scripts/validate_deployment.py

### Phase 6: Cleanup Scripts
- [ ] Migrate cleanup.sh → scripts/cleanup.py
- [ ] Migrate undeploy.sh → scripts/undeploy.py

## Dependencies to Add
- boto3 (AWS SDK)
- docker (Docker SDK)
- click (CLI framework)
- pydantic (Configuration validation)
- rich (Enhanced terminal output)
- python-dotenv (Environment file handling)

## Status Updates

### 2025-07-07 - Initial Planning
- Created migration plan
- Identified all shell scripts to migrate
- Established directory structure
- Defined migration phases

### 2025-07-07 - Phase 1 Progress
- Created utils directory structure with __init__.py
- Migrated common.sh → utils/common.py
  - Converted all bash functions to Python
  - Implemented using boto3 for AWS operations
  - Added rich console for colored output
  - Integrated logging functionality from enhanced_logging.sh
- Created config.py with Pydantic models for configuration management
- Created requirements.txt with all necessary dependencies
- Moved common.sh to shell-bak/

### 2025-07-07 - Phase 2 Complete
- Migrated ecs-utils.sh → utils/ecs_utils.py
  - Converted all ECS/ECR operations to boto3
  - Implemented service health monitoring
  - Added CloudWatch logs integration
  - Converted to class-based design for better organization
- Created utils/aws_utils.py
  - General AWS utilities (identity, credentials, tagging)
  - SSM parameter store operations
  - Generic wait conditions
- Created utils/docker_utils.py
  - Docker image build/push operations
  - ECR authentication
  - Image management utilities
  - Integration with docker-py SDK
- Updated utils/__init__.py with all exports
- Moved ecs-utils.sh to shell-bak/

### 2025-07-07 - Phase 3 Progress
- Created scripts directory structure with __init__.py
- Migrated aws-checks.sh → scripts/aws_checks.py
  - Converted to click CLI framework
  - Added rich console output for better formatting
  - Improved model availability checking
  - Added ECR repository status checking
- Migrated aws-setup.sh → scripts/aws_setup.py  
  - Automated Bedrock model discovery and selection
  - Generates bedrock.env configuration file
  - Added model access testing capability
  - Supports inference profiles (us. prefix models)
- Migrated setup-ecr.sh → scripts/setup_ecr.py
  - Create/delete ECR repositories
  - Docker authentication with ECR
  - Rich table output for repository information
  - Confirmation prompts for destructive operations
- Moved aws-checks.sh, aws-setup.sh, and setup-ecr.sh to shell-bak/
- Phase 3 complete!

### 2025-07-07 - Critical Issues Resolved
- **Eliminated shell script dependency**: 
  - Created scripts/build_push.py with full Docker functionality
  - Updated deploy.py to use Python scripts exclusively
  - No more subprocess calls to shell scripts
- **Added version tagging**:
  - Git commit + timestamp format (e.g., abc1234-20240107-143022)
  - Saves tags to .image-tags file for deployment consistency
  - Graceful fallback if git not available
- **Standardized configuration**:
  - deploy.py now uses centralized config module throughout
  - Removed direct .env loading in favor of config module
  - Consistent configuration access pattern
- **Added progress indicators**:
  - Created spinner context manager in utils/common.py
  - Rich Progress integration in build_push.py
  - Visual feedback for all long-running operations
- Moved build-push.sh to shell-bak/
- **Migration now self-contained** - no shell dependencies!

### Progress Tracking
Total Scripts: 13
- [x] Migrated: 7 (common.sh, ecs-utils.sh, aws-checks.sh, aws-setup.sh, setup-ecr.sh, build-push.sh, deploy.py updated)
- [ ] In Progress: 0
- [ ] Remaining: 6

## Next Steps
1. Start Phase 4: Build and Deployment Scripts
   - build-push.sh → scripts/build_push.py
   - deploy.sh → scripts/deploy.py (if exists)
   - stack_operations.sh → Integrate into deploy.py
2. Continue with Phase 5: Monitoring and Testing Scripts
3. Complete Phase 6: Cleanup Scripts

## Summary of Today's Progress
- Completed Phase 1: Core Utilities (common.sh, enhanced_logging.sh)
- Completed Phase 2: AWS Utilities (ecs-utils.sh, aws_utils.py, docker_utils.py)
- Completed Phase 3: Setup and Configuration Scripts (aws-checks.sh, aws-setup.sh, setup-ecr.sh)
- Created comprehensive Python utility modules with modern patterns
- Established project structure with utils/ and scripts/ directories
- 5 out of 13 shell scripts successfully migrated to Python

## Notes
- Each migrated script should maintain the same functionality as the shell version
- All scripts should use argparse or click for CLI interfaces
- Configuration should be centralized in config.py
- Logging should use Python's logging module with consistent formatting
- Error messages should be clear and actionable