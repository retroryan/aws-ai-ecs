#!/bin/bash
# Start Docker containers with Ollama service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🚀 Starting Weather Agent with Ollama..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and set OLLAMA_MODEL to your preferred model"
    echo "   Default is llama3.2"
fi

# Set environment variables for Ollama
export MODEL_PROVIDER=ollama
export OLLAMA_HOST=http://ollama:11434

# Build images
echo "🔨 Building Docker images..."
docker-compose build

# Start services with ollama profile
echo "🚀 Starting services with Ollama..."
docker-compose --profile ollama up -d

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama to start..."
sleep 10

# Check if model needs to be pulled
MODEL=${OLLAMA_MODEL:-llama3.2}
echo "🔍 Checking if model '$MODEL' is available in Ollama..."

# Try to list models and check if our model exists
if ! docker exec ollama ollama list | grep -q "$MODEL"; then
    echo "📥 Pulling model '$MODEL'..."
    docker exec ollama ollama pull "$MODEL"
else
    echo "✅ Model '$MODEL' is already available"
fi

# Wait for all services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "🏥 Checking service health..."
docker-compose ps

echo ""
echo "✅ Services started successfully!"
echo ""
echo "🌐 Access the Weather Agent API at: http://localhost:8090"
echo "🦙 Ollama is running at: http://localhost:11434"
echo ""
echo "📝 To test the service, run: ./scripts/test_docker.sh"
echo "📊 To view logs: docker-compose logs -f"
echo "🛑 To stop: ./scripts/stop_docker.sh"