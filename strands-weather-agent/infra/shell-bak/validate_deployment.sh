#!/bin/bash
# Simple validation script for Phase 3 testing
# Tests deployment with and without telemetry

set -e

echo "🚀 Strands Weather Agent - Deployment Validation"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    local status=$1
    local message=$2
    if [ "$status" = "success" ]; then
        echo -e "${GREEN}✅ ${message}${NC}"
    elif [ "$status" = "warning" ]; then
        echo -e "${YELLOW}⚠️  ${message}${NC}"
    else
        echo -e "${RED}❌ ${message}${NC}"
    fi
}

# Check if deployment script exists
if [ ! -f "infra/deploy.py" ]; then
    print_status "error" "deploy.py not found. Are you in the project root?"
    exit 1
fi

echo ""
echo "📋 Test 1: Check deployment status"
echo "=================================="
python3 infra/deploy.py status

echo ""
echo "📋 Test 2: Run service tests"
echo "============================"
python3 infra/test_services.py

echo ""
echo "📋 Test 3: Run integration tests"
echo "================================"
if [ -f "infra/integration_test.py" ]; then
    python3 infra/integration_test.py
else
    print_status "warning" "integration_test.py not found"
fi

echo ""
echo "📋 Test 4: Run telemetry demo"
echo "============================="
if [ -f "infra/demo_telemetry.py" ]; then
    python3 infra/demo_telemetry.py
else
    print_status "warning" "demo_telemetry.py not found"
fi

echo ""
echo "================================================"
echo "📊 Validation Summary"
echo "================================================"
echo ""
echo "If all tests passed:"
echo "  1. Check your Langfuse dashboard for traces"
echo "  2. Review CloudWatch logs for telemetry data"
echo "  3. Try the API docs at http://<alb-url>/docs"
echo ""
echo "To test telemetry toggle:"
echo "  - Enable:  python3 infra/deploy.py services"
echo "  - Disable: python3 infra/deploy.py services --disable-telemetry"
echo ""
print_status "success" "Validation complete!"