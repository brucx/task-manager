# Task Manager - Distributed GPU Task Framework

High-performance Celery-based framework for GPU-accelerated task processing with intelligent worker routing and comprehensive monitoring.

## Features

- 🎮 **GPU Optimization**: Multi-GPU support with dual-concurrency per GPU (32 parallel tasks on 16 GPUs)
- 🔄 **Task Hierarchy**: Parent-child task coordination with automatic routing
- ⏱️ **Timeout Management**: 30s queue timeout with admin notifications
- 📊 **Monitoring**: Real-time metrics, REST API, and web dashboard
- 🐳 **Docker Native**: Containerized workers with multi-server deployment
- 🔌 **Dual APIs**: Sync (poll-based) and async interfaces

## Quick Start

```bash
# Install dependencies with uv
uv venv --python 3.10
source .venv/bin/activate
uv pip install -e .

# Start services
docker-compose up -d

# Run example
python examples/image_super_resolution.py
```

## Architecture

- **2 Servers** × 8 GPUs × 2 concurrent tasks = 32 parallel GPU slots
- **Worker Types**: IO (20), CPU-Classify (10), CPU-Encode (10), GPU (32)
- **Queue Strategy**: Accept all, timeout after 30s with admin alert
- **Data Flow**: Shared /tmp volume for zero-copy performance

See [docs/architecture.md](docs/architecture.md) for details.