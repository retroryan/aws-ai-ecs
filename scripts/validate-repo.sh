#!/bin/bash

# Repository Validation Script
# Validates the overall health and consistency of the aws-ai-ecs repository

echo "🔍 AWS AI ECS Repository Validation"
echo "===================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
issues_found=0
checks_passed=0

# Function to report check result
check_result() {
    local check_name="$1"
    local result="$2"
    local details="$3"
    
    if [[ "$result" == "PASS" ]]; then
        echo -e "✅ ${GREEN}$check_name${NC}"
        ((checks_passed++))
    else
        echo -e "❌ ${RED}$check_name${NC}"
        if [[ -n "$details" ]]; then
            echo -e "   ${YELLOW}$details${NC}"
        fi
        ((issues_found++))
    fi
}

echo -e "\n🔍 Running validation checks...\n"

# Check 1: Documentation consistency
echo -e "${BLUE}📚 Documentation Checks${NC}"
echo "========================"

# Check if project count matches reality
project_count_readme=$(grep -c "^### [0-9]" README.md)
actual_projects=$(find . -maxdepth 1 -type d -name "*-*" | wc -l)

if [[ "$project_count_readme" == "$actual_projects" ]]; then
    check_result "Project count in README matches reality" "PASS"
else
    check_result "Project count in README matches reality" "FAIL" "README shows $project_count_readme projects, but found $actual_projects directories"
fi

# Check for naming consistency
if grep -q "strands-ollama-weather-agent" CLAUDE.md; then
    check_result "CLAUDE.md uses correct project names" "FAIL" "Still references 'strands-ollama-weather-agent' instead of 'strands-weather-agent'"
else
    check_result "CLAUDE.md uses correct project names" "PASS"
fi

# Check 2: Project structure consistency
echo -e "\n${BLUE}🏗️  Project Structure Checks${NC}"
echo "============================="

required_files=("README.md" "CLAUDE.md" "docker-compose.yml")
python_projects=("agent-ecs-template" "agriculture-agent-ecs" "strands-weather-agent")

for project in "${python_projects[@]}"; do
    missing_files=()
    for file in "${required_files[@]}"; do
        if [[ ! -f "$project/$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        check_result "$project has required files" "PASS"
    else
        check_result "$project has required files" "FAIL" "Missing: ${missing_files[*]}"
    fi
done

# Check 3: Port conflicts
echo -e "\n${BLUE}🔌 Port Conflict Checks${NC}"
echo "======================="

# Use our port check script
if ./scripts/check-ports.sh | grep -q "CONFLICT DETECTED"; then
    check_result "No port conflicts between projects" "FAIL" "Port conflicts detected - run ./scripts/check-ports.sh for details"
else
    check_result "No port conflicts between projects" "PASS"
fi

# Check 4: Environment configuration
echo -e "\n${BLUE}⚙️  Environment Configuration Checks${NC}"
echo "===================================="

# Check for multiple .env files in same project
env_conflicts=()
for project in "${python_projects[@]}"; do
    env_files=$(find "$project" -name ".env*" -type f | wc -l)
    if [[ $env_files -gt 1 ]]; then
        env_conflicts+=("$project ($env_files .env files)")
    fi
done

if [[ ${#env_conflicts[@]} -eq 0 ]]; then
    check_result "No multiple .env files per project" "PASS"
else
    check_result "No multiple .env files per project" "FAIL" "Multiple .env files in: ${env_conflicts[*]}"
fi

# Check 5: Infrastructure consistency
echo -e "\n${BLUE}🏗️  Infrastructure Checks${NC}"
echo "========================="

deploy_scripts=()
for project in "${python_projects[@]}" "spring-ai-agent-ecs"; do
    if [[ -f "$project/infra/deploy.sh" ]]; then
        deploy_scripts+=("$project")
    fi
done

if [[ ${#deploy_scripts[@]} -eq 4 ]]; then
    check_result "All projects have deploy scripts" "PASS"
else
    check_result "All projects have deploy scripts" "FAIL" "Missing deploy scripts in some projects"
fi

# Summary
echo -e "\n${BLUE}📊 Validation Summary${NC}"
echo "===================="
echo -e "✅ Checks passed: ${GREEN}$checks_passed${NC}"
echo -e "❌ Issues found: ${RED}$issues_found${NC}"

if [[ $issues_found -eq 0 ]]; then
    echo -e "\n🎉 ${GREEN}All validation checks passed! Repository is in good shape.${NC}"
    exit 0
else
    echo -e "\n⚠️  ${YELLOW}$issues_found issue(s) found. See details above.${NC}"
    echo -e "\n💡 To fix issues:"
    echo "- Review REPOSITORY_REVIEW_RECOMMENDATIONS.md for detailed guidance"
    echo "- Run ./scripts/check-ports.sh for port conflict details"
    echo "- Check individual project documentation for consistency"
    exit 1
fi