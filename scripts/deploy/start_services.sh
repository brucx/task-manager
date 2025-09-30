#!/bin/bash
# Start all services (base + workers)

set -e

# Start base services first
./scripts/deploy/start_base.sh

# Start workers
./scripts/deploy/start_workers.sh

echo ""
echo "✅ All services started successfully!"
echo ""