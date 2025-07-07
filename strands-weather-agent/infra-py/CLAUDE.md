# Critical Rules for Working in infra-py Directory

## IMPORTANT: These rules must ALWAYS be followed when working in this directory

### Rule 1: Directory Restriction
- **ONLY work within the infra-py directory**
- **DO NOT navigate up to parent directories**
- All file operations must remain within `/Users/ryanknight/projects/aws/aws-ai-ecs/strands-weather-agent/infra-py/`

### Rule 2: Python Script Restrictions
- **DO NOT run any Python scripts**
- **DO NOT test any Python scripts**
- Code review and editing are allowed, but execution is prohibited
- This includes:
  - No `python` command execution
  - No pytest or unit test execution
  - No script validation through running

### Rule 3: Internet Access Restriction
- **DO NOT access the internet**
- **Use only local knowledge and available files**
- No web searches, API calls, or external resource fetching
- Work exclusively with the codebase and documentation already present

## Purpose
This directory contains Python-based infrastructure code for the strands-weather-agent project. All work should focus on code review, documentation, and static analysis without execution or external dependencies.

## Allowed Activities
- Reading and analyzing Python code
- Editing configuration files
- Reviewing infrastructure definitions
- Creating or updating documentation
- Static code analysis
- File organization and structure improvements

## Directory Context
This is the Python infrastructure directory for the AWS Strands Weather Agent project, which is part of the larger AWS AI ECS project demonstrating AI framework deployments to AWS ECS.