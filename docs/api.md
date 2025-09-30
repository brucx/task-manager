# API Reference

## REST API Endpoints

### Base URL
```
http://localhost:8000
```

### Authentication
Currently no authentication required. Add authentication middleware for production.

---

## Task Management

### Submit Task

Submit a new task for processing.

**Endpoint:** `POST /api/v1/tasks`

**Request Body:**
```json
{
  "task_name": "image_super_resolution_pipeline",
  "args": [
    "https://example.com/input-image.jpg",
    "https://s3.amazonaws.com/bucket/output.jpg"
  ],
  "kwargs": {},
  "priority": 5,
  "sync": false
}
```

**Parameters:**
- `task_name` (string, required): Name of the task to execute
- `args` (array, optional): Positional arguments for the task
- `kwargs` (object, optional): Keyword arguments for the task
- `priority` (integer, optional): Task priority 0-10 (default: 5)
- `sync` (boolean, optional): Wait for completion if true (default: false)

**Response (202 Accepted):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "PENDING",
  "submitted_at": "2025-01-15T10:30:00Z"
}
```

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "image_super_resolution_pipeline",
    "args": [
      "https://example.com/input.jpg",
      "https://s3.amazonaws.com/bucket/output.jpg"
    ]
  }'
```

**Example (Python):**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/tasks",
        json={
            "task_name": "image_super_resolution_pipeline",
            "args": [
                "https://example.com/input.jpg",
                "https://s3.amazonaws.com/bucket/output.jpg"
            ],
            "sync": False
        }
    )
    result = response.json()
    task_id = result["task_id"]
```

---

### Get Task Status

Retrieve the current status of a task.

**Endpoint:** `GET /api/v1/tasks/{task_id}`

**Path Parameters:**
- `task_id` (string, required): Task ID returned from submission

**Response (200 OK):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "state": "SUCCESS",
  "progress": 1.0,
  "result": {
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "input_url": "https://example.com/input.jpg",
    "output_url": "https://s3.amazonaws.com/bucket/output.jpg",
    "classification": {
      "category": "portrait",
      "width": 1920,
      "height": 1080,
      "aspect_ratio": 1.78
    }
  },
  "error": null,
  "submitted_at": "2025-01-15T10:30:00Z",
  "started_at": "2025-01-15T10:30:05Z",
  "completed_at": "2025-01-15T10:30:11Z",
  "subtasks": []
}
```

**Task States:**
- `PENDING`: Task queued, not yet started
- `RECEIVED`: Task received by worker
- `STARTED`: Task execution began
- `SUCCESS`: Task completed successfully
- `FAILURE`: Task failed with error
- `TIMEOUT`: Task exceeded queue timeout (30s)
- `REVOKED`: Task cancelled

**Example (cURL):**
```bash
curl http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000
```

**Example (Python - Polling):**
```python
import asyncio
import httpx

async def wait_for_task(task_id: str):
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"http://localhost:8000/api/v1/tasks/{task_id}"
            )
            status = response.json()

            print(f"State: {status['state']}")

            if status["state"] in ["SUCCESS", "FAILURE", "TIMEOUT"]:
                return status

            await asyncio.sleep(1)
```

---

### Cleanup Task

Remove task resources after completion.

**Endpoint:** `DELETE /api/v1/tasks/{task_id}`

**Path Parameters:**
- `task_id` (string, required): Task ID to cleanup

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Task 550e8400-e29b-41d4-a716-446655440000 cleaned up"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/v1/tasks/550e8400-e29b-41d4-a716-446655440000
```

---

## Monitoring

### Health Check

Check API health status.

**Endpoint:** `GET /health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "task-manager-api",
  "version": "0.1.0"
}
```

---

### Metrics Dashboard

View system metrics and status.

**Endpoint:** `GET /dashboard`

**Response:** HTML dashboard with:
- Worker pool status
- GPU configuration
- Queue information
- API endpoints

---

### Prometheus Metrics

Raw Prometheus metrics for monitoring integration.

**Endpoint:** `GET /dashboard/metrics`

**Response (text/plain):**
```
# HELP tasks_submitted_total Total number of tasks submitted
# TYPE tasks_submitted_total counter
tasks_submitted_total{task_name="image_super_resolution_pipeline"} 1234

# HELP tasks_completed_total Total number of tasks completed
# TYPE tasks_completed_total counter
tasks_completed_total{task_name="...",status="success"} 1200

# HELP task_duration_seconds Task execution duration in seconds
# TYPE task_duration_seconds histogram
task_duration_seconds_bucket{task_name="...",worker_type="gpu",le="5.0"} 100
```

---

## Usage Patterns

### Synchronous Processing

For simple use cases where client can wait:

```python
response = await client.post(
    "http://localhost:8000/api/v1/tasks",
    json={
        "task_name": "image_super_resolution_pipeline",
        "args": [...],
        "sync": True  # Block until complete
    }
)
result = response.json()["result"]
```

### Asynchronous Processing

For high-throughput scenarios:

```python
# Submit many tasks
task_ids = []
for image_url in image_urls:
    response = await client.post(
        "http://localhost:8000/api/v1/tasks",
        json={
            "task_name": "image_super_resolution_pipeline",
            "args": [image_url, upload_url],
            "sync": False
        }
    )
    task_ids.append(response.json()["task_id"])

# Poll for completion
results = []
for task_id in task_ids:
    status = await wait_for_task(task_id)
    results.append(status["result"])
```

### Batch Processing

Process multiple tasks concurrently:

```python
import asyncio

async def process_batch(image_urls: list):
    async with httpx.AsyncClient() as client:
        # Submit all tasks
        tasks = [
            client.post(
                "http://localhost:8000/api/v1/tasks",
                json={
                    "task_name": "image_super_resolution_pipeline",
                    "args": [url, get_upload_url(url)]
                }
            )
            for url in image_urls
        ]
        responses = await asyncio.gather(*tasks)

        # Get task IDs
        task_ids = [r.json()["task_id"] for r in responses]

        # Wait for all
        statuses = await asyncio.gather(*[
            wait_for_task(tid) for tid in task_ids
        ])

        return statuses
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Errors

**400 Bad Request**
- Invalid task name
- Missing required parameters

**404 Not Found**
- Task ID not found

**500 Internal Server Error**
- Worker failure
- System error

### Retry Strategy

For failed tasks:
1. Check task status for error details
2. Retry with exponential backoff
3. Maximum 3 retry attempts
4. Contact admin if persistent failures

---

## Rate Limiting

Currently no rate limiting implemented. Recommended for production:
- Per-client rate limits
- Queue depth monitoring
- Automatic backpressure

---

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

These interfaces allow:
- Testing endpoints directly
- Viewing request/response schemas
- Generating client code