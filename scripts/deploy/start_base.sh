#!/bin/bash
# Start base services (Redis, API, Flower)

set -e

echo "🚀 Starting base services..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create shared volume directory
mkdir -p /tmp/shared/tasks
chmod 777 /tmp/shared/tasks

# Start base services
echo "📦 Starting Redis, API, and Flower..."
docker-compose -f docker-compose.base.yml up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose -f docker-compose.base.yml ps

# Show logs
echo ""
echo "📋 Recent logs:"
docker-compose -f docker-compose.base.yml logs --tail=20

echo ""
echo "✅ Base services started successfully!"
echo ""
echo "📊 Access points:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Dashboard: http://localhost:8000/dashboard"
echo "  - Metrics: http://localhost:8000/dashboard/metrics"
echo "  - Flower (Celery UI): http://localhost:5555"
echo ""
echo "💡 Next steps:"
echo "  - Start workers: ./scripts/deploy/start_workers.sh"
echo "  - Start GPU workers: ./scripts/deploy/start_gpu_workers.sh"
echo ""