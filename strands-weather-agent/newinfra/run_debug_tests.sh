#!/bin/bash
# Run debug tests against different environments - Complete and Simple!

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Create timestamped output directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="$PROJECT_ROOT/debug_results/$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Weather Agent Debug Test Runner${NC}"
echo "=================================="
echo -e "📁 Results will be saved to: ${BLUE}$OUTPUT_DIR${NC}"

# Function to discover AWS ALB URL
discover_aws_url() {
    echo -e "\n${YELLOW}🔍 Discovering AWS ALB URL...${NC}"
    
    # Try to get from CloudFormation
    ALB_URL=$(aws cloudformation describe-stacks \
        --stack-name strands-weather-agent-base \
        --query 'Stacks[0].Outputs[?OutputKey==`ALBDNSName`].OutputValue' \
        --output text \
        --region ${AWS_REGION:-us-east-1} 2>/dev/null || echo "")
    
    if [ -n "$ALB_URL" ]; then
        ALB_URL="http://$ALB_URL"
        echo -e "${GREEN}✅ Found ALB URL: $ALB_URL${NC}"
    else
        echo -e "${RED}❌ Could not discover ALB URL from CloudFormation${NC}"
        # Try to use a default or ask user
        if [ -n "$1" ]; then
            ALB_URL="$1"
            echo -e "${YELLOW}Using provided URL: $ALB_URL${NC}"
        else
            echo -e "${RED}Please provide AWS URL as argument or ensure AWS CLI is configured${NC}"
            return 1
        fi
    fi
    
    # Test connectivity
    if curl -s "$ALB_URL/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ AWS deployment is accessible${NC}"
        echo "$ALB_URL"
    else
        echo -e "${RED}❌ AWS deployment not accessible at: $ALB_URL${NC}"
        return 1
    fi
}

# Function to run tests
run_test() {
    local env=$1
    local url=$2
    local output_subdir="$OUTPUT_DIR/$env"
    
    mkdir -p "$output_subdir"
    
    echo -e "\n${YELLOW}🧪 Running tests for $env environment...${NC}"
    echo -e "📝 Saving to: $output_subdir"
    
    # Run the test suite
    if python3 "$SCRIPT_DIR/debug_test_suite.py" "$env" --url "$url" --output-dir "$output_subdir" 2>&1 | tee "$output_subdir/test_output.log"; then
        echo -e "${GREEN}✅ $env tests completed${NC}"
        
        # Copy the most recent JSON result to a standard name
        LATEST_JSON=$(ls -t "$output_subdir"/debug_${env}_*.json 2>/dev/null | head -1)
        if [ -f "$LATEST_JSON" ]; then
            cp "$LATEST_JSON" "$output_subdir/results.json"
        fi
        
        return 0
    else
        echo -e "${RED}❌ $env tests failed${NC}"
        return 1
    fi
}

# Function to create comparison report
create_comparison_report() {
    local docker_json="$OUTPUT_DIR/docker/results.json"
    local aws_json="$OUTPUT_DIR/aws/results.json"
    local comparison_file="$OUTPUT_DIR/comparison_report.txt"
    
    echo -e "\n${YELLOW}📊 Creating comparison report...${NC}"
    
    if [ -f "$docker_json" ] && [ -f "$aws_json" ]; then
        python3 "$SCRIPT_DIR/compare_environments.py" "$docker_json" "$aws_json" > "$comparison_file" 2>&1
        
        # Also save structured comparison
        python3 "$SCRIPT_DIR/compare_environments.py" "$docker_json" "$aws_json" --save "$OUTPUT_DIR/comparison.json" > /dev/null 2>&1
        
        # Show summary
        echo -e "${GREEN}✅ Comparison report created${NC}"
        echo -e "\n${BLUE}=== COMPARISON SUMMARY ===${NC}"
        tail -20 "$comparison_file"
    else
        echo -e "${RED}❌ Could not create comparison - missing test results${NC}"
    fi
}

# Function to create summary
create_summary() {
    local summary_file="$OUTPUT_DIR/summary.md"
    
    cat > "$summary_file" << EOF
# Debug Test Results - $TIMESTAMP

## Test Environments

### Docker
- URL: http://localhost:7777
- Status: $([ -f "$OUTPUT_DIR/docker/results.json" ] && echo "✅ Tested" || echo "❌ Not tested")

### AWS
- URL: $([ -f "$OUTPUT_DIR/aws/.url" ] && cat "$OUTPUT_DIR/aws/.url" || echo "Not discovered")
- Status: $([ -f "$OUTPUT_DIR/aws/results.json" ] && echo "✅ Tested" || echo "❌ Not tested")

## Key Findings

$(if [ -f "$OUTPUT_DIR/comparison_report.txt" ]; then
    echo "### Differences Found:"
    grep -E "formatting_error|timeout|retry" "$OUTPUT_DIR/comparison_report.txt" | head -10
else
    echo "No comparison available"
fi)

## Files Generated

- \`docker/results.json\` - Docker test results
- \`docker/test_output.log\` - Docker test console output
- \`aws/results.json\` - AWS test results
- \`aws/test_output.log\` - AWS test console output
- \`comparison_report.txt\` - Detailed comparison
- \`comparison.json\` - Structured comparison data

## Next Steps

1. Review the comparison report for differences
2. Check test output logs for error details
3. Look for formatting errors unique to AWS
4. Check CloudWatch logs with:
   \`\`\`
   aws logs filter-log-events \\
     --log-group-name /ecs/strands-weather-agent-main \\
     --filter-pattern '[COORDINATE_DEBUG]' \\
     --region us-east-1
   \`\`\`
EOF

    echo -e "\n${GREEN}📄 Summary created: $summary_file${NC}"
}

# Main execution
main() {
    local env_to_test="${1:-both}"
    local custom_aws_url="$2"
    
    echo -e "\n${BLUE}Test mode: $env_to_test${NC}"
    
    case $env_to_test in
        docker)
            # Test Docker only
            if curl -s http://localhost:7777/health > /dev/null 2>&1; then
                run_test "docker" "http://localhost:7777"
            else
                echo -e "${RED}❌ Docker services not running${NC}"
                echo -e "${YELLOW}Start with: ./scripts/start_docker.sh${NC}"
                exit 1
            fi
            ;;
        
        aws)
            # Test AWS only
            AWS_URL=$(discover_aws_url "$custom_aws_url") || exit 1
            mkdir -p "$OUTPUT_DIR/aws"
            echo "$AWS_URL" > "$OUTPUT_DIR/aws/.url"
            run_test "aws" "$AWS_URL"
            ;;
        
        both|"")
            # Test both environments (default)
            DOCKER_TESTED=false
            AWS_TESTED=false
            
            # Test Docker
            echo -e "\n${BLUE}=== DOCKER TESTING ===${NC}"
            if curl -s http://localhost:7777/health > /dev/null 2>&1; then
                if run_test "docker" "http://localhost:7777"; then
                    DOCKER_TESTED=true
                fi
            else
                echo -e "${YELLOW}⚠️  Docker services not running, skipping Docker tests${NC}"
                echo -e "   Start with: ./scripts/start_docker.sh"
            fi
            
            # Test AWS
            echo -e "\n${BLUE}=== AWS TESTING ===${NC}"
            AWS_URL=$(discover_aws_url "$custom_aws_url")
            if [ $? -eq 0 ]; then
                mkdir -p "$OUTPUT_DIR/aws"
                echo "$AWS_URL" > "$OUTPUT_DIR/aws/.url"
                if run_test "aws" "$AWS_URL"; then
                    AWS_TESTED=true
                fi
            else
                echo -e "${YELLOW}⚠️  AWS deployment not accessible, skipping AWS tests${NC}"
            fi
            
            # Compare if both tested
            if [ "$DOCKER_TESTED" = true ] && [ "$AWS_TESTED" = true ]; then
                create_comparison_report
            else
                echo -e "\n${YELLOW}⚠️  Could not test both environments - comparison skipped${NC}"
            fi
            ;;
        
        *)
            echo -e "${RED}Invalid environment: $env_to_test${NC}"
            echo "Usage: $0 [docker|aws|both] [custom_aws_url]"
            exit 1
            ;;
    esac
    
    # Create summary
    create_summary
    
    # Final output
    echo -e "\n${GREEN}✨ Debug testing complete!${NC}"
    echo -e "\n📁 All results saved to: ${BLUE}$OUTPUT_DIR${NC}"
    echo -e "\nKey files:"
    echo -e "  📄 Summary: ${BLUE}$OUTPUT_DIR/summary.md${NC}"
    [ -f "$OUTPUT_DIR/comparison_report.txt" ] && echo -e "  📊 Comparison: ${BLUE}$OUTPUT_DIR/comparison_report.txt${NC}"
    echo -e "\n💡 To view results:"
    echo -e "  cat $OUTPUT_DIR/summary.md"
    
    # Open summary if on macOS
    if [ "$(uname)" = "Darwin" ] && [ -f "$OUTPUT_DIR/summary.md" ]; then
        echo -e "\n${YELLOW}Opening summary in default editor...${NC}"
        open "$OUTPUT_DIR/summary.md" 2>/dev/null || true
    fi
}

# Run main function
main "$@"