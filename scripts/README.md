# Repository Scripts

This directory contains repository-wide utilities to help maintain consistency and quality across all projects.

## Available Scripts

### `validate-repo.sh`
**Purpose**: Comprehensive validation of repository health and consistency

**Usage**: 
```bash
./scripts/validate-repo.sh
```

**What it checks**:
- Documentation consistency (project counts, naming)
- Project structure (required files present)
- Port conflicts between projects
- Environment configuration issues
- Infrastructure script presence

**Exit codes**:
- `0`: All checks passed
- `1`: Issues found (details provided in output)

### `check-ports.sh`
**Purpose**: Detect port conflicts across all projects

**Usage**:
```bash
./scripts/check-ports.sh
```

**Features**:
- Scans all docker-compose.yml files
- Identifies port conflicts between projects
- Suggests optimal port allocation scheme
- Colorized output for easy reading

## Usage Examples

### Daily Development Workflow
```bash
# Before starting work
./scripts/validate-repo.sh

# Check for port conflicts before running multiple projects
./scripts/check-ports.sh
```

### CI/CD Integration
```bash
# In your CI pipeline
./scripts/validate-repo.sh || exit 1
```

### Before Committing Changes
```bash
# Validate changes don't break consistency
./scripts/validate-repo.sh
```

## Adding New Scripts

When adding new repository-wide scripts:

1. **Make them executable**: `chmod +x scripts/new-script.sh`
2. **Add usage documentation** to this README
3. **Use consistent output formatting** (colors, icons)
4. **Follow naming convention**: `action-target.sh` (e.g., `validate-repo.sh`, `check-ports.sh`)
5. **Include help text** in the script itself

## Script Standards

- **Exit codes**: 0 for success, 1 for issues found
- **Output format**: Use emojis and colors for readability
- **Error handling**: Provide clear error messages
- **Documentation**: Include purpose and usage in script header