#!/bin/bash
# Stop all services

set -e

echo "🛑 Stopping Task Manager services..."

# Stop workers
if [ -f docker-compose.workers.yml ]; then
    echo "👷 Stopping CPU/IO workers..."
    docker-compose -f docker-compose.workers.yml down
fi

# Stop GPU workers if present
if [ -f docker-compose.gpu.yml ]; then
    echo "🎮 Stopping GPU workers..."
    docker-compose -f docker-compose.gpu.yml down
fi

# Stop base services
if [ -f docker-compose.base.yml ]; then
    echo "📦 Stopping base services..."
    docker-compose -f docker-compose.base.yml down
fi

# Stop old docker-compose.yml if present
if [ -f docker-compose.yml ]; then
    echo "📦 Stopping legacy services..."
    docker-compose down 2>/dev/null || true
fi

echo "✅ All services stopped"