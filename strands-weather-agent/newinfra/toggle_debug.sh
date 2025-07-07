#!/bin/bash
# Toggle debug mode for coordinate issue investigation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to enable debug mode
enable_debug() {
    echo -e "${YELLOW}Enabling debug mode for coordinate investigation...${NC}"
    
    # Add to .env
    if [ -f "$PROJECT_ROOT/.env" ]; then
        if ! grep -q "STRANDS_DEBUG_TOOL_CALLS" "$PROJECT_ROOT/.env"; then
            echo "" >> "$PROJECT_ROOT/.env"
            echo "# Debug mode for coordinate issue" >> "$PROJECT_ROOT/.env"
            echo "STRANDS_DEBUG_TOOL_CALLS=true" >> "$PROJECT_ROOT/.env"
            echo -e "${GREEN}✅ Added to .env${NC}"
        else
            sed -i.bak 's/STRANDS_DEBUG_TOOL_CALLS=.*/STRANDS_DEBUG_TOOL_CALLS=true/' "$PROJECT_ROOT/.env"
            echo -e "${GREEN}✅ Updated in .env${NC}"
        fi
    fi
    
    # Add to cloud.env
    if [ -f "$PROJECT_ROOT/cloud.env" ]; then
        if ! grep -q "STRANDS_DEBUG_TOOL_CALLS" "$PROJECT_ROOT/cloud.env"; then
            echo "" >> "$PROJECT_ROOT/cloud.env"
            echo "# Debug mode for coordinate issue" >> "$PROJECT_ROOT/cloud.env"
            echo "STRANDS_DEBUG_TOOL_CALLS=true" >> "$PROJECT_ROOT/cloud.env"
            echo -e "${GREEN}✅ Added to cloud.env${NC}"
        else
            sed -i.bak 's/STRANDS_DEBUG_TOOL_CALLS=.*/STRANDS_DEBUG_TOOL_CALLS=true/' "$PROJECT_ROOT/cloud.env"
            echo -e "${GREEN}✅ Updated in cloud.env${NC}"
        fi
    fi
    
    echo -e "\n${GREEN}Debug mode enabled!${NC}"
    echo "To see debug logs in CloudWatch:"
    echo "  aws logs filter-log-events \\"
    echo "    --log-group-name /ecs/strands-weather-agent-main \\"
    echo "    --filter-pattern '[COORDINATE_DEBUG]' \\"
    echo "    --region us-east-1"
}

# Function to disable debug mode
disable_debug() {
    echo -e "${YELLOW}Disabling debug mode...${NC}"
    
    # Remove from .env
    if [ -f "$PROJECT_ROOT/.env" ]; then
        sed -i.bak '/STRANDS_DEBUG_TOOL_CALLS/d' "$PROJECT_ROOT/.env"
        sed -i.bak '/# Debug mode for coordinate issue/d' "$PROJECT_ROOT/.env"
        echo -e "${GREEN}✅ Removed from .env${NC}"
    fi
    
    # Remove from cloud.env
    if [ -f "$PROJECT_ROOT/cloud.env" ]; then
        sed -i.bak '/STRANDS_DEBUG_TOOL_CALLS/d' "$PROJECT_ROOT/cloud.env"
        sed -i.bak '/# Debug mode for coordinate issue/d' "$PROJECT_ROOT/cloud.env"
        echo -e "${GREEN}✅ Removed from cloud.env${NC}"
    fi
    
    # Clean up backup files
    rm -f "$PROJECT_ROOT/.env.bak" "$PROJECT_ROOT/cloud.env.bak"
    
    echo -e "\n${GREEN}Debug mode disabled!${NC}"
}

# Main script
case ${1:-status} in
    enable|on)
        enable_debug
        echo -e "\n${YELLOW}Remember to redeploy for changes to take effect:${NC}"
        echo "  python3 infra/deploy.py update-services"
        ;;
    
    disable|off)
        disable_debug
        echo -e "\n${YELLOW}Remember to redeploy for changes to take effect:${NC}"
        echo "  python3 infra/deploy.py update-services"
        ;;
    
    status)
        echo -e "${YELLOW}Debug mode status:${NC}"
        
        if [ -f "$PROJECT_ROOT/.env" ] && grep -q "STRANDS_DEBUG_TOOL_CALLS=true" "$PROJECT_ROOT/.env"; then
            echo -e "  .env: ${GREEN}ENABLED${NC}"
        else
            echo -e "  .env: ${RED}DISABLED${NC}"
        fi
        
        if [ -f "$PROJECT_ROOT/cloud.env" ] && grep -q "STRANDS_DEBUG_TOOL_CALLS=true" "$PROJECT_ROOT/cloud.env"; then
            echo -e "  cloud.env: ${GREEN}ENABLED${NC}"
        else
            echo -e "  cloud.env: ${RED}DISABLED${NC}"
        fi
        
        # Check if deployed with debug
        echo -e "\n${YELLOW}Testing debug endpoint:${NC}"
        AWS_URL="http://strands-weather-agent-1803800064.us-east-1.elb.amazonaws.com"
        if curl -s "$AWS_URL/debug/tool-calls" | grep -q "debug_enabled"; then
            echo -e "  AWS Deployment: ${GREEN}DEBUG ENABLED${NC}"
        else
            echo -e "  AWS Deployment: ${RED}DEBUG DISABLED or not deployed${NC}"
        fi
        ;;
    
    *)
        echo "Usage: $0 [enable|disable|status]"
        echo ""
        echo "Commands:"
        echo "  enable  - Enable debug logging for coordinate issue"
        echo "  disable - Disable debug logging"
        echo "  status  - Check current debug status"
        exit 1
        ;;
esac