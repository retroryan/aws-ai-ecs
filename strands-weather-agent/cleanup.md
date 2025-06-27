# Project Cleanup Proposal

## Overview
This document outlines cleanup opportunities for the Strands Weather Agent project to improve maintainability, reduce repository size, and enhance security.

## 🧹 Files to Remove

### 1. Test Classes and Debug Code

#### Leftover Test Files (Can be consolidated or removed)
- `tests/test_simple_coordinate.py` - Basic coordinate test, functionality covered by other tests
- `tests/test_diverse_cities.py` - Geographic knowledge test, redundant with main test suite
- `tests/test_coordinate_handling.py` - Coordinate handling, covered by comprehensive tests
- `tests/test_coordinate_usage.py` - Usage patterns, redundant
- `tests/docker_test.py` - Docker integration test, can be moved to scripts/
- `weather_agent/test_setup.py` - Setup validation, should be in tests/ or removed

#### Debug and Development Files
- `weather_agent/test_demo.sh` - Demo script, functionality in main scripts
- `tests/run_all_tests.py` - Redundant with pytest and scripts/run-tests.sh

### 2. Cache and Build Artifacts

#### Python Cache Files
```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
```

#### Pytest Cache
```
.pytest_cache/
```

#### System Files
```
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
```

### 3. Log Files and Temporary Data
- `logs/*.log` - Runtime logs (should be in .gitignore)
- `infra/logs/` - Infrastructure logs
- `infra/.image-tags` - Build artifacts

### 4. History and Backup Files
- `.history/` directory - Contains 10+ old README versions
- `.history/mcp_servers/` - Old server versions

### 5. Redundant Documentation
- `CLAUDE.md` - Development notes, not needed for users
- `context.md` - Internal context, not user-facing
- `smart-agent-lifecycle-deep-dive.md` - Detailed analysis, could be moved to docs/
- `realistic-caching-improvements.md` - Implementation notes
- `ARCHITECTURE_ANALYSIS.md` - Internal analysis
- `infra/alignment.md` - Development notes

### 6. Model Testing Artifacts
- `models_testing/test_results/` - Contains 13 old test result files
- Some files in `models_testing/` may be development-only

### 7. Environment Files with Sensitive Data
⚠️ **SECURITY CONCERN**: Review these files for sensitive data:
- `.env` - Contains AWS account info and credentials
- `bedrock.env` - Configuration file
- `weather_agent/.env` - Local environment

## 🐳 Proposed .dockerignore

```dockerignore
# Version Control
.git
.gitignore
.history/

# Documentation (not needed in containers)
*.md
!README.md
docs/
GUIDE_*.md
ARCHITECTURE_*.md
CLAUDE.md
context.md
smart-agent-*.md
realistic-caching-*.md

# Development and Testing
tests/
models_testing/
.pytest_cache/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# IDE and Editor Files
.vscode/
.idea/
*.swp
*.swo
*~
.claude/

# System Files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs and Temporary Files
logs/
*.log
*.tmp
*.temp
.cache/

# Environment Files (use build args instead)
.env*
!.env.example
bedrock.env

# Build Artifacts
build/
dist/
*.egg-info/
.eggs/
infra/logs/
infra/.image-tags

# Virtual Environments
.venv/
venv/
env/
ENV/

# Coverage Reports
htmlcov/
.coverage
.coverage.*
coverage.xml
*.cover

# Jupyter Notebooks (if any)
.ipynb_checkpoints

# Local Development
scripts/local_*
*_local.*

# AWS and Cloud Files
.aws/
credentials
config

# Node.js (if any frontend)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Backup Files
*.bak
*.backup
*.old
*~

# Large Files
*.zip
*.tar.gz
*.rar
```

## 🔧 Cleanup Actions

### Immediate Actions (Safe to do now)

1. **Remove Cache Files**
   ```bash
   find . -name "__pycache__" -type d -exec rm -rf {} +
   find . -name "*.pyc" -delete
   find . -name ".DS_Store" -delete
   rm -rf .pytest_cache/
   ```

2. **Clean Log Files**
   ```bash
   rm -f logs/*.log
   rm -rf infra/logs/
   ```

3. **Remove Build Artifacts**
   ```bash
   rm -f infra/.image-tags
   ```

### Review Required Actions

4. **History Cleanup** (Review first)
   ```bash
   # Review .history/ contents before removing
   ls -la .history/
   # If confirmed not needed:
   # rm -rf .history/
   ```

5. **Test Consolidation** (Requires code review)
   - Merge redundant test files into comprehensive test suites
   - Keep `test_mcp_agent_strands.py` and `test_structured_output.py` as main tests
   - Move `docker_test.py` to `scripts/test_docker_integration.py`

6. **Documentation Cleanup** (Review with team)
   - Move development docs to `docs/development/`
   - Keep user-facing documentation in root
   - Archive or remove internal analysis documents

### Security Actions (High Priority)

7. **Environment File Security**
   ```bash
   # Review .env files for sensitive data
   grep -r "aws_access_key\|aws_secret\|password\|token" .env*
   
   # Remove sensitive data and use .env.example templates
   # Ensure .env files are in .gitignore
   ```

8. **Credential Scanning**
   ```bash
   # Scan for accidentally committed credentials
   git log --all --full-history -- .env
   git log --all --full-history -- bedrock.env
   ```

## 📁 Proposed Directory Structure (After Cleanup)

```
strands-weather-agent/
├── README.md                          # Main documentation
├── GUIDE_STRUCTURED_OUTPUT_STRANDS.md # Keep - important guide
├── docker-compose.yml
├── .env.example                       # Template only
├── .gitignore
├── .dockerignore                      # New file
├── requirements.txt                   # Root requirements
├── docker/                           # Docker configurations
├── infra/                           # Infrastructure code
├── scripts/                         # Utility scripts
├── mcp_servers/                     # MCP server implementations
├── weather_agent/                   # Main application
├── tests/                           # Consolidated test suite
│   ├── test_mcp_agent_strands.py   # Main agent tests
│   ├── test_structured_output.py   # Structured output tests
│   └── integration/                # Integration tests
│       └── test_docker.py          # Moved from root tests/
├── examples/                        # Usage examples
└── docs/                           # Documentation (new)
    ├── development/                # Development docs
    │   ├── architecture.md        # Moved from root
    │   └── testing.md             # Testing guidelines
    └── deployment/                 # Deployment guides
```

## 🎯 Benefits of Cleanup

### Repository Size Reduction
- Remove ~50MB of cache files and logs
- Remove ~20 redundant test and documentation files
- Cleaner git history

### Security Improvements
- Remove sensitive environment files from tracking
- Implement proper .dockerignore to prevent credential leaks
- Clean credential scanning

### Maintainability
- Consolidated test suite (easier to run and maintain)
- Clear separation of user vs. development documentation
- Reduced cognitive load for new contributors

### Docker Build Performance
- Smaller build context (faster builds)
- Fewer files to copy and process
- Better layer caching

## 🚀 Implementation Plan

### Phase 1: Safe Cleanup (No code changes)
1. Remove cache files and build artifacts
2. Clean log files
3. Add .dockerignore file
4. Update .gitignore if needed

### Phase 2: Test Consolidation (Requires testing)
1. Review and merge redundant test files
2. Move integration tests to appropriate locations
3. Update test scripts and documentation

### Phase 3: Documentation Restructure (Team review)
1. Move development docs to docs/ folder
2. Keep essential user documentation in root
3. Update README references

### Phase 4: Security Hardening (Critical)
1. Audit all environment files
2. Remove sensitive data from repository
3. Implement credential scanning in CI/CD

## 📋 Checklist

- [ ] Review all files marked for deletion
- [ ] Backup important development notes
- [ ] Test that cleanup doesn't break builds
- [ ] Update CI/CD scripts if needed
- [ ] Verify Docker builds work with new .dockerignore
- [ ] Update documentation references
- [ ] Run security scan after cleanup
- [ ] Update team on changes

## ⚠️ Warnings

1. **Don't delete** without reviewing:
   - Any file with unique functionality
   - Environment files (may contain important config)
   - Test files (ensure coverage isn't lost)

2. **Security Priority**: Handle environment files first
   - They may contain AWS credentials
   - Should not be in version control

3. **Test Before Merge**: Ensure all functionality works after cleanup
   - Run full test suite
   - Test Docker builds
   - Verify deployment scripts

## 🔍 Files Requiring Manual Review

These files need individual review before cleanup decisions:

### Test Files
- `tests/test_mcp_agent.py` - Large test file, check for unique tests
- `models_testing/` directory - Determine if needed for production

### Documentation
- `STRANDS_DEFINITIVE_GUIDE.md` - Comprehensive guide, keep or move to docs/
- Various analysis documents - Archive vs. delete decision needed

### Configuration
- Multiple .env files - Consolidate and secure
- `bedrock.env` - Review for sensitive data

This cleanup will significantly improve the project's maintainability and security posture while reducing repository bloat.
