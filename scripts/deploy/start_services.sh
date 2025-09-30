#!/bin/bash
# Start all services with Docker Compose

set -e

echo "🚀 Starting Task Manager services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create shared volume directory
mkdir -p /tmp/shared/tasks
chmod 777 /tmp/shared/tasks

# Start base services (Redis, API, CPU/IO workers)
echo "📦 Starting base services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

# Show logs
echo ""
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📊 Access points:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Dashboard: http://localhost:8000/dashboard"
echo "  - Metrics: http://localhost:8000/dashboard/metrics"
echo "  - Flower (Celery UI): http://localhost:5555"
echo ""
echo "🎮 GPU workers must be started separately on GPU servers:"
echo "  docker-compose -f docker-compose.gpu.yml up -d"
echo ""