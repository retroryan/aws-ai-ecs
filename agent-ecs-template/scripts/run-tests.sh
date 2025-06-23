#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Agent ECS Integration Tests ==="
echo

cd "$PROJECT_DIR"

echo "1. Installing test dependencies..."
pip install -q -r tests/requirements.txt

echo "2. Starting services..."
"$SCRIPT_DIR/start.sh"

echo "3. Waiting for services to be ready..."
sleep 5

echo "4. Running integration tests..."
echo
set +e
pytest tests/ -v --tb=short --timeout=60
TEST_EXIT_CODE=$?
set -e

echo
echo "5. Stopping services..."
"$SCRIPT_DIR/stop.sh"

echo
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed. Exit code: $TEST_EXIT_CODE"
fi

exit $TEST_EXIT_CODE