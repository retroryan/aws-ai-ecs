# Docker Security Proposal: .dockerignore Configuration

## Network Binding Analysis

All services in the Agriculture Agent project bind to `0.0.0.0`:
- **MCP Servers**: Listen on `0.0.0.0` (ports 7071-7073)
- **Main Agent**: Listens on `0.0.0.0:7075`

This is necessary for Docker container networking and AWS ECS deployment but requires careful security considerations.

## Security Rationale for .dockerignore

A properly configured `.dockerignore` file is critical for:

1. **Preventing Credential Leaks**
   - Environment files containing AWS credentials, API keys, and model configurations
   - AWS configuration files that might contain access keys
   - Private keys and certificates

2. **Reducing Attack Surface**
   - Excluding test files that might contain hardcoded credentials
   - Removing deployment scripts that could reveal infrastructure details
   - Eliminating local development configurations

3. **Minimizing Image Size**
   - Python cache files and virtual environments
   - Documentation and non-runtime files
   - IDE configurations and OS-specific files

## Proposed .dockerignore File

```dockerignore
# CRITICAL SECURITY: Environment and credentials
.env
.env.*
*.env
env/
.envrc
secrets/
private/

# CRITICAL SECURITY: AWS credentials and config
.aws/
credentials
config
*.pem
*.key
*.crt
*.p12
*_rsa
*_dsa
*_ed25519
*_ecdsa
*.pub

# CRITICAL SECURITY: API keys and tokens
*api_key*
*apikey*
*access_token*
*auth_token*
.netrc

# Git files (may contain sensitive history)
.git/
.gitignore
.gitattributes
.github/
.gitlab/

# Python cache and temporary files
__pycache__/
*.py[cod]
*$py.class
*.so
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
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
pip-log.txt
pip-delete-this-directory.txt

# Testing (may contain test credentials)
.pytest_cache/
.coverage
.coverage.*
.cache
*.cover
*.py,cover
.hypothesis/
.tox/
.nox/
htmlcov/
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.mypy_cache/
.dmypy.json
dmypy.json
.pyre/
.pytype/
cython_debug/

# IDE files (may contain project paths)
.vscode/
.idea/
*.swp
*.swo
*~
.project
.pydevproject
.settings/
*.sublime-*
.spyderproject
.spyproject
.ropeproject

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
.AppleDouble
.LSOverride
Icon
.DocumentRevisions-V100
.fseventsd
.TemporaryItems
.VolumeIcon.icns
.com.apple.timemachine.donotpresent

# Project specific security concerns
logs/
*.log
*.pid
.image-tags
infra/.image-tags
infra/logs/
infra/*.sh  # Deployment scripts may contain infrastructure details
scripts/*.sh  # Local scripts may have local paths/configs

# Test files (exclude to prevent test credential leaks)
tests/
test_*.py
*_test.py
fixtures/
mock_data/

# Documentation (not needed in production)
*.md
README*
CHANGELOG*
CONTRIBUTING*
LICENSE*
AUTHORS*
docs/
documentation/

# Docker files (prevent recursive inclusion)
Dockerfile*
docker-compose*.yml
.dockerignore

# Temporary and backup files
*.tmp
*.temp
*.bak
*.backup
*.old
*.orig
*.cache
*.swn
*.swo
*~

# Virtual environments
venv/
virtualenv/
.venv/
ENV/
env.bak/
venv.bak/
.virtualenv/

# Jupyter notebooks (may contain output with sensitive data)
.ipynb_checkpoints/
*.ipynb

# Database files
*.db
*.sqlite
*.sqlite3
*.sql
database/

# Archives (may contain bundled secrets)
*.tar
*.tar.gz
*.zip
*.gz
*.bz2
*.7z
*.rar
*.tgz

# Local development files
.local/
local_settings.py
local.py
settings_local.py
.env.local
.env.development
.env.test

# Node modules (if any frontend code)
node_modules/
npm-debug.log
yarn-error.log

# Infrastructure as Code state files
*.tfstate
*.tfstate.*
.terraform/
*.tfvars

# CloudFormation artifacts
packaged.yaml
samconfig.toml

# Monitoring and profiling
.profile
*.prof
*.pprof
```

## Implementation Recommendations

1. **Create Separate .dockerignore Files**: Consider having different .dockerignore files for different Docker images:
   - `.dockerignore.main` for the main agent
   - `.dockerignore.mcp` for MCP servers

2. **Regular Security Audits**: 
   - Review .dockerignore before each deployment
   - Use tools like `docker history` to inspect built images
   - Scan images for secrets using tools like TruffleHog or GitLeaks

3. **Build-Time Security**:
   - Use multi-stage builds to further minimize final image contents
   - Never use `COPY . .` without a comprehensive .dockerignore
   - Consider using `--secret` flag for build-time secrets

4. **Runtime Security**:
   - Since services bind to `0.0.0.0`, ensure:
     - Proper security groups in AWS
     - Network isolation between services
     - Use of service mesh or API gateway for external access

5. **Additional Measures**:
   - Use AWS Secrets Manager or Parameter Store for runtime secrets
   - Enable ECR image scanning
   - Implement least-privilege IAM roles

## Testing the .dockerignore

To verify the .dockerignore is working correctly:

```bash
# List files that would be included in the build context
docker build --no-cache --dry-run .

# Check image size before and after adding .dockerignore
docker images | grep agriculture-agent

# Inspect image layers for sensitive content
docker history <image-id> --no-trunc
```