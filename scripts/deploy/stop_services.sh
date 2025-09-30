#!/bin/bash
# Stop all services

set -e

echo "🛑 Stopping Task Manager services..."

# Stop base services
echo "📦 Stopping base services..."
docker-compose down

# Stop GPU workers if present
if [ -f docker-compose.gpu.yml ]; then
    echo "🎮 Stopping GPU workers..."
    docker-compose -f docker-compose.gpu.yml down
fi

echo "✅ All services stopped"