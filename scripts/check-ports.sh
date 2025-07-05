#!/bin/bash

# Port Conflict Detection Script
# This script checks for port conflicts across all projects in the repository

echo "🔍 Checking for port conflicts across all projects..."
echo "================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to extract ports from docker-compose files
extract_ports() {
    local file="$1"
    local project="$2"
    
    if [[ -f "$file" ]]; then
        echo -e "\n📁 ${project}:"
        grep -n "ports:" -A 1 "$file" | grep -E "[0-9]+:[0-9]+" | \
        sed 's/.*- "//' | sed 's/".*//' | sed 's/.*"//' | \
        while read port_mapping; do
            if [[ -n "$port_mapping" ]]; then
                host_port=$(echo "$port_mapping" | cut -d':' -f1)
                container_port=$(echo "$port_mapping" | cut -d':' -f2)
                echo "  🔌 Host port $host_port → Container port $container_port"
            fi
        done
    fi
}

# Check each project for docker-compose files
projects=(
    "agent-ecs-template"
    "agriculture-agent-ecs" 
    "strands-weather-agent"
    "spring-ai-agent-ecs"
)

declare -A used_ports

echo -e "\n🔍 Scanning projects for port usage..."

for project in "${projects[@]}"; do
    compose_file="$project/docker-compose.yml"
    extract_ports "$compose_file" "$project"
    
    # Collect port usage for conflict detection
    if [[ -f "$compose_file" ]]; then
        grep -E "[0-9]+:[0-9]+" "$compose_file" | \
        sed 's/.*- "//' | sed 's/".*//' | sed 's/.*"//' | \
        while read port_mapping; do
            if [[ -n "$port_mapping" ]]; then
                host_port=$(echo "$port_mapping" | cut -d':' -f1)
                if [[ -n "${used_ports[$host_port]}" ]]; then
                    echo -e "\n${RED}⚠️  CONFLICT DETECTED!${NC}"
                    echo -e "   Port $host_port is used by both:"
                    echo -e "   - ${used_ports[$host_port]}"
                    echo -e "   - $project"
                else
                    used_ports[$host_port]="$project"
                fi
            fi
        done
    fi
done

echo -e "\n📋 Summary of Port Allocations:"
echo "==============================="

# Sort and display port allocations
for port in $(printf '%s\n' "${!used_ports[@]}" | sort -n); do
    echo -e "  Port $port: ${used_ports[$port]}"
done

echo -e "\n✅ Port conflict check completed!"

# Suggest port allocation scheme
echo -e "\n💡 Recommended Port Allocation Scheme:"
echo "======================================"
echo "  agent-ecs-template:     8080-8081"
echo "  agriculture-agent-ecs:  8090-8093"  
echo "  strands-weather-agent:  8100-8103"
echo "  spring-ai-agent-ecs:    8110-8111"
echo ""
echo "This would eliminate all conflicts and allow running multiple projects simultaneously."