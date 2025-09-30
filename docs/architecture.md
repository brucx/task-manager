# Architecture Overview

## System Design

The Task Manager framework is designed for high-throughput GPU-accelerated task processing with intelligent worker routing and comprehensive monitoring.

### Key Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI REST API                            │
│              (Sync & Async Task Submission)                     │
│                    Port 8000                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Redis Message Broker                         │
│         (Task Queues + Result Backend + Metrics)               │
│                    Port 6379                                    │
└─┬──────────┬──────────┬───────────┬───────────┬────────────────┘
  │          │          │           │           │
  ▼          ▼          ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌─────────┐
│   IO   │ │  CPU   │ │  CPU   │ │   GPU   │ │   GPU   │
│Workers │ │Classify│ │ Encode │ │ Workers │ │ Workers │
│  (20)  │ │  (10)  │ │  (10)  │ │ Server1 │ │ Server2 │
│        │ │        │ │        │ │ (16)    │ │ (16)    │
└────────┘ └────────┘ └────────┘ └─────────┘ └─────────┘
                                   8×GPU×2     8×GPU×2
```

## Hardware Configuration

### GPU Servers
- **2 Servers** with 8 NVIDIA RTX 4090 GPUs each
- **16 Total GPUs** × 2 concurrent tasks = **32 parallel GPU slots**
- **24GB VRAM** per GPU supporting 3 preloaded models (1GB each)

### Worker Distribution

| Worker Type | Count | Concurrency | Purpose |
|-------------|-------|-------------|---------|
| IO Workers | 20 | 20 | Download/Upload operations |
| CPU-Classify | 10 | 10 | Image classification |
| CPU-Encode | 10 | 10 | Result encoding |
| GPU Workers | 16 containers | 2 per GPU | Model inference |
| **Total** | **56** | **72** | **All operations** |

## Data Flow Architecture

### Task Pipeline (Image Super-Resolution Example)

```
1. Download Image (IO Worker)
   ↓
   /tmp/shared/tasks/{task_id}/input.jpg
   ↓
2. Classify Image (CPU Worker)
   ↓
   /tmp/shared/tasks/{task_id}/classification.json
   ↓
3. Route to Appropriate GPU Queue
   ↓ general/portrait/landscape
   ↓
4. GPU Inference (GPU Worker in Docker)
   ↓
   /tmp/shared/tasks/{task_id}/output.jpg
   ↓
5. Encode Result (CPU Worker)
   ↓
   /tmp/shared/tasks/{task_id}/result.jpg
   ↓
6. Upload to Object Storage (IO Worker)
   ↓
   S3/OSS URL
   ↓
7. Cleanup /tmp (Automatic)
```

### Shared Storage

- **Path**: `/tmp/shared/tasks/`
- **Structure**: One directory per task ID
- **Lifecycle**: Created on download, cleaned after upload
- **Sharing**: NFS volume mounted on all workers
- **Performance**: Zero-copy between worker stages

## Queue Architecture

### Queue Types

| Queue Name | Priority | Workers | Purpose |
|------------|----------|---------|---------|
| `main` | 5 | N/A | Task orchestration |
| `io` | 5 | 20 | Download/Upload |
| `cpu` | 5 | 20 | Classification/Encoding |
| `gpu-general` | 5 | 32 | General model inference |
| `gpu-portrait` | 5 | 32 | Portrait model inference |
| `gpu-landscape` | 5 | 32 | Landscape model inference |

### Task Routing Logic

1. **Main Task** submitted to `main` queue
2. **Download** routed to `io` queue (high concurrency)
3. **Classification** routed to `cpu` queue
4. **Dynamic GPU Routing** based on classification:
   - Portrait → `gpu-portrait`
   - Landscape → `gpu-landscape`
   - Default → `gpu-general`
5. **Encoding** routed to `cpu` queue
6. **Upload** routed to `io` queue

## Throughput Analysis

### Current Configuration

- **Input Load**: 30 tasks/sec
- **Task Duration**: 6 seconds (dominated by GPU inference)
- **Required Capacity**: 30 tasks/sec × 6 sec = 180 concurrent tasks
- **GPU Capacity**: 32 parallel slots
- **Bottleneck**: GPU inference (5.33 tasks/sec max)

### Queue Behavior

With 30 tasks/sec input and 5.33 tasks/sec processing:
- **Steady State**: ~30 second queue depth
- **Timeout**: 30 seconds → tasks dropped with admin notification
- **Strategy**: Accept and queue, timeout old tasks

### Scaling Options

To handle full 30 tasks/sec load:
1. **Add More GPUs**: 96 GPU slots needed (30 × 6 / 2 = 90 tasks)
2. **Faster Models**: Reduce inference time from 6s to 1.1s
3. **Batch Processing**: Process multiple images per GPU call
4. **Hybrid Approach**: Queue buffering + scale-out

## Model Management

### Preloading Strategy

All three models preloaded at worker startup:
```python
# On GPU worker initialization
ModelRegistry.load_model("general", "/models/general_model.pth")
ModelRegistry.load_model("portrait", "/models/portrait_model.pth")
ModelRegistry.load_model("landscape", "/models/landscape_model.pth")
```

### VRAM Usage

- **General Model**: 1GB
- **Portrait Model**: 1GB
- **Landscape Model**: 1GB
- **Total**: 3GB / 24GB VRAM (12.5% utilization)
- **Remaining**: 21GB for inference buffers

### Model Switching

No switching delay - all models resident in VRAM:
- Worker receives task with model name
- Retrieves from ModelRegistry (instant)
- Runs inference with appropriate model

## Timeout & Monitoring

### Timeout Management

```python
Task submitted → Queue → Wait...
                          ↓
                  if wait_time > 30s:
                    ↓
                  Revoke task
                  Notify admin (webhook/email)
                  Mark as TIMEOUT
```

### Admin Notifications

Triggered on:
- Task queue timeout (>30s)
- Task failures
- Worker crashes

Notification channels:
- **Webhook**: HTTP POST to configured URL
- **Email**: SMTP notification (configurable)

### Metrics Collection

Prometheus metrics exported at `/dashboard/metrics`:

```
# Task metrics
tasks_submitted_total{task_name="..."}
tasks_completed_total{task_name="...", status="..."}
tasks_timeout_total{task_name="..."}

# Timing metrics
task_duration_seconds{task_name="...", worker_type="..."}
task_queue_time_seconds{queue_name="..."}

# Worker metrics
active_workers{worker_type="..."}
queue_depth{queue_name="..."}

# GPU metrics
gpu_utilization_percent{gpu_id="..."}
```

## API Design

### Endpoints

**Submit Task** (POST `/api/v1/tasks`)
```json
{
  "task_name": "image_super_resolution_pipeline",
  "args": ["https://example.com/input.jpg", "https://s3.../output.jpg"],
  "sync": false,
  "priority": 5
}
```

**Get Status** (GET `/api/v1/tasks/{task_id}`)
```json
{
  "task_id": "abc-123",
  "state": "SUCCESS",
  "result": {"output_url": "..."},
  "progress": 1.0
}
```

### Sync vs Async API

**Async Mode** (default):
1. Submit task → immediate return with task_id
2. Client polls `/api/v1/tasks/{task_id}` for status
3. Advantages: No long connections, client can cancel

**Sync Mode** (`sync: true`):
1. Submit task → blocks until completion
2. Returns final result directly
3. Advantages: Simpler client code
4. Timeout: Controlled by `task_default_timeout`

## Docker Deployment

### Multi-Server Setup

**Server 1** (API + Workers + Redis):
```bash
docker-compose up -d
```

**Server 2 & 3** (GPU Workers):
```bash
docker-compose -f docker-compose.gpu.yml up -d
```

### Network Configuration

All servers must be on shared network:
- Redis broker accessible from all workers
- NFS mount for `/tmp/shared` on all servers
- GPU servers connect to Redis on Server 1

### Container Types

| Dockerfile | Purpose | Base Image |
|------------|---------|------------|
| `Dockerfile.api` | FastAPI server | `python:3.10-slim` |
| `Dockerfile.worker` | CPU/IO workers | `python:3.10-slim` |
| `Dockerfile.gpu` | GPU workers | `nvidia/cuda:11.8.0-cudnn8` |

## Fault Tolerance

### Worker Failures

- **Task Acknowledgment**: Late acknowledgment after completion
- **Requeue**: Failed tasks automatically requeued
- **Max Retries**: 3 attempts with exponential backoff

### GPU Worker Failures

- **Container Restart**: Docker automatically restarts crashed containers
- **Task Recovery**: Celery requeues tasks from dead workers
- **Health Checks**: Periodic GPU health verification

### Data Loss Prevention

- **Shared Storage**: Persists across worker restarts
- **Result Backend**: Redis persistence with AOF
- **Cleanup**: Only after successful upload confirmation