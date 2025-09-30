#!/bin/bash
# Start CPU/IO workers

set -e

echo "🚀 Starting CPU/IO workers..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if base services are running
if ! docker network ls | grep -q task_network; then
    echo "❌ task_network not found. Please start base services first:"
    echo "   ./scripts/deploy/start_base.sh"
    exit 1
fi

# Start workers
echo "📦 Starting IO and CPU workers..."
docker-compose -f docker-compose.workers.yml up -d

# Wait for startup
echo "⏳ Waiting for workers to start..."
sleep 5

# Check status
echo "🏥 Worker status:"
docker-compose -f docker-compose.workers.yml ps

# Show logs
echo ""
echo "📋 Recent logs:"
docker-compose -f docker-compose.workers.yml logs --tail=20

echo ""
echo "✅ Workers started successfully!"
echo ""
echo "📊 Monitor workers:"
echo "  - Flower UI: http://localhost:5555"
echo "  - View logs: docker-compose -f docker-compose.workers.yml logs -f"
echo ""