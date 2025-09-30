# Deployment Guide

## Prerequisites

### System Requirements

**Base Services (Server 1):**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 100GB+
- OS: Ubuntu 22.04 or similar
- Docker 24.0+
- Docker Compose 2.0+

**GPU Servers (Server 2 & 3):**
- CPU: 16+ cores
- RAM: 64GB+
- Storage: 500GB+
- GPUs: 8× NVIDIA RTX 4090 (24GB each)
- OS: Ubuntu 22.04
- Docker 24.0+
- NVIDIA Driver 530+
- NVIDIA Container Toolkit

### Software Dependencies

```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose
sudo apt-get install docker-compose-plugin

# NVIDIA Container Toolkit (GPU servers only)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/brucx/task-manager.git
cd task-manager
```

### 2. Install Dependencies

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.10
source .venv/bin/activate

# Install dependencies
uv pip install -e .
```

### 3. Configuration

Create `.env` file:

```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Task Configuration
TASK_DEFAULT_TIMEOUT=300
TASK_QUEUE_TIMEOUT=30

# Shared Storage
SHARED_TMP_PATH=/tmp/shared/tasks

# Admin Notifications
ADMIN_WEBHOOK_URL=https://your-webhook-url.com/alert
ADMIN_EMAIL=admin@example.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

---

## Deployment: Single Server (Development)

For development and testing on a single machine:

### 1. Start Services

```bash
./scripts/deploy/start_services.sh
```

This starts:
- Redis (message broker)
- FastAPI API server
- IO workers (20)
- CPU workers (20)
- Flower monitoring UI

### 2. Verify Services

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test API
curl http://localhost:8000/health
```

### 3. Access Interfaces

- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/dashboard
- **Metrics**: http://localhost:8000/dashboard/metrics
- **Flower**: http://localhost:5555

### 4. Stop Services

```bash
./scripts/deploy/stop_services.sh
```

---

## Deployment: Multi-Server (Production)

### Architecture

```
Server 1: Redis + API + CPU/IO Workers
Server 2: GPU Workers (8 GPUs)
Server 3: GPU Workers (8 GPUs)
```

### Network Setup

All servers must be on same network:

**Server 1 (10.0.1.10):**
- Redis: Port 6379
- API: Port 8000
- Flower: Port 5555

**Server 2 & 3 (10.0.1.11, 10.0.1.12):**
- GPU workers connect to Server 1 Redis

### Shared Storage

Setup NFS for `/tmp/shared`:

**On Server 1 (NFS Server):**
```bash
sudo apt-get install nfs-kernel-server

# Create shared directory
sudo mkdir -p /shared/tasks
sudo chmod 777 /shared/tasks

# Configure exports
echo "/shared/tasks 10.0.1.0/24(rw,sync,no_subtree_check)" | \
  sudo tee -a /etc/exports

sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

**On Server 2 & 3 (NFS Clients):**
```bash
sudo apt-get install nfs-common

# Mount shared storage
sudo mkdir -p /tmp/shared
sudo mount 10.0.1.10:/shared/tasks /tmp/shared

# Add to /etc/fstab for persistence
echo "10.0.1.10:/shared/tasks /tmp/shared nfs defaults 0 0" | \
  sudo tee -a /etc/fstab
```

### Server 1 Deployment

```bash
# Update configuration
cat > .env << EOF
REDIS_HOST=10.0.1.10
REDIS_PORT=6379
SHARED_TMP_PATH=/tmp/shared/tasks
EOF

# Start services
./scripts/deploy/start_services.sh
```

### Server 2 & 3 Deployment

```bash
# Update GPU compose file
# Edit docker-compose.gpu.yml:
#   - REDIS_HOST=10.0.1.10

# Place models in ./models/
cp general_model.pth ./models/
cp portrait_model.pth ./models/
cp landscape_model.pth ./models/

# Start GPU workers
./scripts/deploy/start_gpu_workers.sh

# Verify GPU usage
watch -n 1 nvidia-smi
```

---

## Model Management

### Model Files

Place model files in `./models/`:
- `general_model.pth` (1GB)
- `portrait_model.pth` (1GB)
- `landscape_model.pth` (1GB)

### Model Format

Models should be PyTorch `.pth` files. Update `src/workers/gpu_worker.py` to load your specific model format:

```python
# Example: Load PyTorch model
import torch

def load_model(model_path):
    model = YourModelClass()
    model.load_state_dict(torch.load(model_path))
    model = model.cuda()
    model.eval()
    return model
```

### Model Updates

To update models:

```bash
# Stop GPU workers
docker-compose -f docker-compose.gpu.yml down

# Replace model files
cp new_model.pth ./models/general_model.pth

# Restart GPU workers
docker-compose -f docker-compose.gpu.yml up -d
```

---

## Monitoring

### Prometheus Integration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'task-manager'
    static_configs:
      - targets: ['10.0.1.10:8000']
    metrics_path: '/dashboard/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

Import metrics:
- `tasks_submitted_total`
- `tasks_completed_total`
- `task_duration_seconds`
- `queue_depth`
- `gpu_utilization_percent`

### Log Aggregation

Collect logs from all services:

```bash
# Export logs
docker-compose logs > /var/log/task-manager/api.log
docker-compose -f docker-compose.gpu.yml logs > /var/log/task-manager/gpu.log
```

---

## Scaling

### Horizontal Scaling

Add more GPU servers:

```bash
# On new server
docker-compose -f docker-compose.gpu.yml up -d
```

### Vertical Scaling

Adjust worker concurrency:

```yaml
# docker-compose.yml
io-worker:
  command: celery -A src.core.celery_app worker -Q io -c 40  # Increase from 20
```

### Auto-Scaling

Use Docker Swarm or Kubernetes for dynamic scaling:

```yaml
# docker-compose.yml
deploy:
  replicas: 3
  update_config:
    parallelism: 1
  resources:
    limits:
      cpus: '4'
      memory: 8G
```

---

## Backup & Recovery

### Redis Backup

```bash
# Enable AOF persistence
docker-compose exec redis redis-cli CONFIG SET appendonly yes

# Backup data
docker-compose exec redis redis-cli BGSAVE
docker cp task-manager_redis_1:/data/dump.rdb ./backup/
```

### Shared Storage Backup

```bash
# Backup task data
rsync -avz /tmp/shared/ backup@server:/backups/shared/
```

---

## Troubleshooting

### Common Issues

**Issue: GPU workers not starting**
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check GPU availability
nvidia-smi
```

**Issue: Tasks timing out**
```bash
# Check queue depth
redis-cli -h 10.0.1.10 LLEN gpu-general

# Check worker status
docker-compose -f docker-compose.gpu.yml ps

# View worker logs
docker-compose -f docker-compose.gpu.yml logs gpu-worker-0
```

**Issue: NFS mount failing**
```bash
# Check NFS exports
showmount -e 10.0.1.10

# Test mount
sudo mount -t nfs 10.0.1.10:/shared/tasks /tmp/test
```

### Performance Tuning

**Redis Optimization:**
```bash
# Increase max connections
redis-cli CONFIG SET maxclients 10000

# Increase memory
redis-cli CONFIG SET maxmemory 4gb
```

**Worker Optimization:**
```bash
# Increase prefetch
celery -A src.core.celery_app worker -Q io --prefetch-multiplier 4

# Adjust concurrency
celery -A src.core.celery_app worker -Q cpu -c 20
```

---

## Security

### Production Checklist

- [ ] Enable Redis authentication
- [ ] Add API rate limiting
- [ ] Implement API key authentication
- [ ] Enable HTTPS with SSL certificates
- [ ] Restrict Docker network access
- [ ] Enable firewall rules
- [ ] Secure NFS with Kerberos
- [ ] Implement task validation
- [ ] Add input sanitization
- [ ] Enable audit logging

### Redis Authentication

```bash
# Set password
redis-cli CONFIG SET requirepass your-strong-password

# Update .env
REDIS_PASSWORD=your-strong-password
```

### API Authentication

Add to `src/api/main.py`:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.api_key:
        raise HTTPException(status_code=403)
    return api_key
```