#!/bin/bash
# Test script for Ollama Docker integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 Testing Ollama Docker Integration"
echo "===================================="

# Check if services are running
echo -e "\n📊 Checking service status..."
docker-compose --profile ollama ps

# Check if Ollama is healthy
echo -e "\n🏥 Testing Ollama health..."
if docker exec ollama curl -f http://localhost:11434/ > /dev/null 2>&1; then
    echo "✅ Ollama is healthy"
else
    echo "❌ Ollama is not responding"
    exit 1
fi

# List available models
echo -e "\n📦 Available Ollama models:"
docker exec ollama ollama list

# Get the model from .env or use default
if [ -f .env ]; then
    export $(grep -E '^OLLAMA_MODEL=' .env | xargs)
fi
MODEL=${OLLAMA_MODEL:-llama3.2}

# Check if model is available
echo -e "\n🔍 Checking if model '$MODEL' is available..."
if docker exec ollama ollama list | grep -q "$MODEL"; then
    echo "✅ Model '$MODEL' is available"
else
    echo "⚠️  Model '$MODEL' not found. Pulling it now..."
    docker exec ollama ollama pull "$MODEL"
fi

# Test basic Ollama functionality
echo -e "\n🤖 Testing Ollama model response..."
TEST_RESPONSE=$(docker exec ollama ollama run "$MODEL" "Say 'Hello from Ollama' and nothing else" 2>/dev/null | head -n 1)
if [[ "$TEST_RESPONSE" == *"Hello from Ollama"* ]] || [[ "$TEST_RESPONSE" == *"Hello"* ]]; then
    echo "✅ Ollama model is responding correctly"
    echo "   Response: $TEST_RESPONSE"
else
    echo "⚠️  Unexpected response: $TEST_RESPONSE"
fi

# Test weather agent API
echo -e "\n🌤️  Testing Weather Agent API..."
API_URL="http://localhost:8090"

# Check health endpoint
echo "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s "${API_URL}/health" || echo "Failed")
if [[ "$HEALTH_RESPONSE" == *"healthy"* ]]; then
    echo "✅ Weather Agent API is healthy"
else
    echo "❌ Weather Agent API health check failed"
    echo "   Response: $HEALTH_RESPONSE"
fi

# Test with a simple query
echo -e "\n📍 Testing weather query..."
QUERY_PAYLOAD='{"message": "What is the weather in Chicago?", "session_id": "test-ollama-docker"}'
echo "Sending query: $QUERY_PAYLOAD"

QUERY_RESPONSE=$(curl -s -X POST "${API_URL}/query" \
    -H "Content-Type: application/json" \
    -d "$QUERY_PAYLOAD" || echo "Failed")

if [[ "$QUERY_RESPONSE" == *"error"* ]] || [[ "$QUERY_RESPONSE" == "Failed" ]]; then
    echo "❌ Query failed"
    echo "   Response: $QUERY_RESPONSE"
else
    echo "✅ Query successful"
    # Pretty print the response if jq is available
    if command -v jq &> /dev/null; then
        echo "$QUERY_RESPONSE" | jq -r '.response' | head -n 5
        echo "   ... (truncated)"
    else
        echo "$QUERY_RESPONSE" | head -n 100
    fi
fi

# Check logs for errors
echo -e "\n📋 Checking for errors in logs..."
ERROR_COUNT=$(docker-compose logs weather-agent 2>&1 | grep -c "ERROR" || true)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ No errors found in weather-agent logs"
else
    echo "⚠️  Found $ERROR_COUNT error(s) in logs"
    echo "   Run 'docker-compose logs weather-agent' to see details"
fi

# Summary
echo -e "\n======================================"
echo "📊 Test Summary"
echo "======================================"
echo "Provider: Ollama (Docker)"
echo "Model: $MODEL"
echo "API Endpoint: $API_URL"
echo ""
echo "✅ All basic tests completed"
echo ""
echo "📝 Next steps:"
echo "- View logs: docker-compose logs -f"
echo "- Try more queries: curl -X POST ${API_URL}/query -H 'Content-Type: application/json' -d '{\"message\": \"Your query here\"}'"
echo "- Stop services: ./scripts/stop_docker.sh"