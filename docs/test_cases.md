# Test Case Design - Task Manager

## Test Architecture Overview

### Test Pyramid Strategy
```
                    /\
                   /  \
                  / E2E \          5% - End-to-End Tests
                 /------\
                /        \
               /Integration\       20% - Integration Tests
              /------------\
             /              \
            /   Unit Tests   \     75% - Unit Tests
           /------------------\
```

### Test Categories
- **Unit Tests**: Individual component logic validation
- **Integration Tests**: Component interaction and Celery task flow
- **E2E Tests**: Full workflow from API to worker completion
- **Performance Tests**: Load, latency, and resource utilization
- **Stress Tests**: System behavior under extreme conditions

---

## 1. Unit Tests

### 1.1 Task Model Tests (`tests/unit/test_models.py`)

#### Test Case: TaskState Enum Values
```python
def test_task_state_enum():
    """Validate TaskState enum contains all required states."""
    assert TaskState.PENDING == "PENDING"
    assert TaskState.SUCCESS == "SUCCESS"
    assert TaskState.FAILURE == "FAILURE"
    assert TaskState.TIMEOUT == "TIMEOUT"
```

**Priority**: 🟢 Medium
**Expected**: All enum values match specification
**Dependencies**: None

#### Test Case: SubTaskConfig Validation
```python
def test_subtask_config_valid():
    """Valid subtask configuration should be accepted."""
    config = SubTaskConfig(
        name="test_task",
        worker_type=WorkerType.CPU,
        queue="cpu_queue",
        priority=TaskPriority.HIGH
    )
    assert config.name == "test_task"
    assert config.priority == 10
```

**Priority**: 🟢 Medium
**Expected**: Valid config created without errors
**Dependencies**: Pydantic models

#### Test Case: TaskRequest Defaults
```python
def test_task_request_defaults():
    """TaskRequest should apply correct defaults."""
    request = TaskRequest(task_name="classify_image")
    assert request.args == []
    assert request.kwargs == {}
    assert request.priority == TaskPriority.NORMAL
    assert request.sync is False
```

**Priority**: 🟢 Medium
**Expected**: Default values correctly applied
**Dependencies**: Pydantic defaults

---

### 1.2 Storage Utils Tests (`tests/unit/test_storage.py`)

#### Test Case: Task Directory Creation
```python
def test_get_task_dir_creates_directory(tmp_path, monkeypatch):
    """get_task_dir should create directory if not exists."""
    monkeypatch.setattr('src.utils.storage.STORAGE_ROOT', tmp_path)
    task_id = "test-task-123"

    task_dir = get_task_dir(task_id)

    assert task_dir.exists()
    assert task_dir.is_dir()
    assert task_dir.name == task_id
```

**Priority**: 🔴 High
**Expected**: Directory created with correct structure
**Dependencies**: pathlib, pytest fixtures

#### Test Case: Save and Retrieve Task Data
```python
def test_save_and_retrieve_task_data(tmp_path, monkeypatch):
    """Data saved should be retrievable."""
    monkeypatch.setattr('src.utils.storage.STORAGE_ROOT', tmp_path)
    task_id = "test-task-456"
    filename = "test.json"
    data = b'{"key": "value"}'

    save_task_data(task_id, filename, data)
    file_path = get_task_file_path(task_id, filename)

    assert file_path.exists()
    assert file_path.read_bytes() == data
```

**Priority**: 🔴 High
**Expected**: Data integrity maintained
**Dependencies**: Storage utilities

#### Test Case: Cleanup Task Directory
```python
def test_cleanup_task_dir(tmp_path, monkeypatch):
    """cleanup_task_dir should remove all task files."""
    monkeypatch.setattr('src.utils.storage.STORAGE_ROOT', tmp_path)
    task_id = "cleanup-test"

    # Create files
    save_task_data(task_id, "file1.txt", b"data1")
    save_task_data(task_id, "file2.txt", b"data2")

    task_dir = get_task_dir(task_id)
    cleanup_task_dir(task_dir)

    assert not task_dir.exists()
```

**Priority**: 🔴 High
**Expected**: All files and directory removed
**Dependencies**: Storage utilities

---

### 1.3 CPU Worker Tests (`tests/unit/test_cpu_worker.py`)

#### Test Case: Image Classification Logic
```python
def test_classify_image_portrait(tmp_path):
    """Portrait aspect ratio should be classified as PORTRAIT."""
    # Create square test image
    from PIL import Image

    img = Image.new('RGB', (800, 1000))
    img_path = tmp_path / "portrait.jpg"
    img.save(img_path)

    result = classify_image("test-id", str(img_path))

    assert result["category"] == ImageCategory.PORTRAIT.value
    assert result["width"] == 800
    assert result["height"] == 1000
```

**Priority**: 🟡 Critical
**Expected**: Correct category classification
**Dependencies**: PIL, CPU worker logic

#### Test Case: Image Classification Landscape
```python
def test_classify_image_landscape(tmp_path):
    """Wide aspect ratio should be classified as LANDSCAPE."""
    img = Image.new('RGB', (1920, 1080))
    img_path = tmp_path / "landscape.jpg"
    img.save(img_path)

    result = classify_image("test-id", str(img_path))

    assert result["category"] == ImageCategory.LANDSCAPE.value
```

**Priority**: 🟡 Critical
**Expected**: Landscape detection works
**Dependencies**: PIL, CPU worker logic

---

### 1.4 GPU Worker Tests (`tests/unit/test_gpu_worker.py`)

#### Test Case: Model Registry Loading
```python
def test_model_registry_load():
    """Model should be loaded only once."""
    ModelRegistry._models.clear()

    model1 = ModelRegistry.load_model("test_model", "/path/to/model")
    model2 = ModelRegistry.load_model("test_model", "/path/to/model")

    assert model1 is model2
    assert len(ModelRegistry._models) == 1
```

**Priority**: 🟡 Critical
**Expected**: Singleton pattern for models
**Dependencies**: ModelRegistry

#### Test Case: GPU Inference Placeholder
```python
def test_gpu_inference_placeholder(tmp_path):
    """Inference should resize image as placeholder."""
    from PIL import Image

    # Create input image
    input_img = Image.new('RGB', (100, 100))
    input_path = tmp_path / "input.jpg"
    input_img.save(input_path)

    output_path = tmp_path / "output.jpg"

    run_inference("general", str(input_path), str(output_path))

    output_img = Image.open(output_path)
    assert output_img.size == (200, 200)  # 2x resize
```

**Priority**: 🟢 Medium
**Expected**: Placeholder resizes correctly
**Dependencies**: PIL, GPU worker

---

## 2. Integration Tests

### 2.1 Task Manager Tests (`tests/integration/test_task_manager.py`)

#### Test Case: Submit Task End-to-End
```python
@pytest.mark.asyncio
async def test_submit_task_returns_id(celery_app):
    """submit_task should return valid task ID."""
    task_id = TaskManager.submit_task(
        task_name="classify_image",
        args=["test-id", "/path/to/image.jpg"],
        priority=5
    )

    assert task_id is not None
    assert isinstance(task_id, str)
    assert len(task_id) > 0
```

**Priority**: 🟡 Critical
**Expected**: Valid task ID returned
**Dependencies**: Celery, Redis

#### Test Case: Submit Parallel Subtasks
```python
@pytest.mark.asyncio
async def test_submit_parallel_subtasks(celery_app):
    """Parallel subtasks should all receive IDs."""
    subtask_configs = [
        SubTaskConfig(
            name="classify_image",
            worker_type=WorkerType.CPU,
            queue="cpu_queue"
        ),
        SubTaskConfig(
            name="gpu_inference_general",
            worker_type=WorkerType.GPU,
            queue="gpu_queue"
        )
    ]

    subtask_ids = TaskManager.submit_subtasks(
        parent_task_id="parent-123",
        subtask_configs=subtask_configs,
        parallel=True
    )

    assert len(subtask_ids) == 2
    assert all(isinstance(sid, str) for sid in subtask_ids)
```

**Priority**: 🟡 Critical
**Expected**: All subtasks created
**Dependencies**: Celery group tasks

#### Test Case: Get Task Status Pending
```python
def test_get_task_status_pending():
    """New task should have PENDING state."""
    task_id = TaskManager.submit_task(
        task_name="classify_image",
        args=["test", "/path"]
    )

    status = TaskManager.get_task_status(task_id)

    assert status.task_id == task_id
    assert status.state in [TaskState.PENDING, TaskState.RECEIVED]
```

**Priority**: 🔴 High
**Expected**: Status reflects actual state
**Dependencies**: Celery, task execution

---

### 2.2 API Integration Tests (`tests/integration/test_api.py`)

#### Test Case: Submit Task via API
```python
@pytest.mark.asyncio
async def test_api_submit_task(async_client):
    """POST /api/v1/tasks should accept valid request."""
    request_data = {
        "task_name": "classify_image",
        "args": ["task-id", "/path/image.jpg"],
        "priority": 5,
        "sync": False
    }

    response = await async_client.post(
        "/api/v1/tasks",
        json=request_data
    )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["state"] == "PENDING"
```

**Priority**: 🟡 Critical
**Expected**: 200 OK with task_id
**Dependencies**: FastAPI test client

#### Test Case: Get Task Status via API
```python
@pytest.mark.asyncio
async def test_api_get_task_status(async_client):
    """GET /api/v1/tasks/{id} should return status."""
    # Submit task first
    submit_response = await async_client.post(
        "/api/v1/tasks",
        json={"task_name": "classify_image"}
    )
    task_id = submit_response.json()["task_id"]

    # Get status
    status_response = await async_client.get(
        f"/api/v1/tasks/{task_id}"
    )

    assert status_response.status_code == 200
    data = status_response.json()
    assert data["task_id"] == task_id
    assert "state" in data
```

**Priority**: 🔴 High
**Expected**: Status endpoint functional
**Dependencies**: FastAPI, running workers

#### Test Case: Sync API Wait for Completion
```python
@pytest.mark.asyncio
async def test_api_sync_mode(async_client):
    """Sync mode should wait for task completion."""
    request_data = {
        "task_name": "classify_image",
        "sync": True
    }

    response = await async_client.post(
        "/api/v1/tasks",
        json=request_data
    )

    assert response.status_code == 200
    data = response.json()
    assert data["state"] in [
        TaskState.SUCCESS,
        TaskState.FAILURE,
        TaskState.TIMEOUT
    ]
```

**Priority**: 🟡 Critical
**Expected**: Blocks until completion
**Dependencies**: Running workers, task execution

---

### 2.3 Worker Communication Tests (`tests/integration/test_worker_communication.py`)

#### Test Case: IO → CPU → GPU Pipeline
```python
@pytest.mark.asyncio
async def test_full_pipeline_flow():
    """Test complete IO → CPU → GPU → CPU → IO flow."""
    # 1. Download image
    download_result = download_image.delay(
        "test-pipeline",
        "https://example.com/test.jpg"
    )
    input_path = download_result.get(timeout=30)

    # 2. Classify image
    classify_result = classify_image.delay(
        "test-pipeline",
        input_path
    )
    classification = classify_result.get(timeout=10)

    # 3. Run GPU inference
    model_task = f"gpu_inference_{classification['category']}"
    gpu_result = celery_app.tasks[model_task].delay(
        "test-pipeline",
        input_path
    )
    output_path = gpu_result.get(timeout=60)

    # 4. Encode result
    encode_result = encode_result.delay(
        "test-pipeline",
        output_path
    )
    final_path = encode_result.get(timeout=10)

    assert Path(final_path).exists()
```

**Priority**: 🟡 Critical
**Expected**: Complete pipeline executes
**Dependencies**: All workers, Redis, shared storage

---

## 3. End-to-End Tests

### 3.1 Complete Workflow Tests (`tests/e2e/test_workflow.py`)

#### Test Case: Image Super Resolution Workflow
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_super_resolution_workflow(async_client):
    """Complete super resolution from API to result."""
    # Submit via API
    response = await async_client.post(
        "/api/v1/tasks",
        json={
            "task_name": "process_image",
            "kwargs": {
                "image_url": "https://example.com/test.jpg"
            },
            "sync": True
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == TaskState.SUCCESS

    # Verify result exists
    task_id = data["task_id"]
    result_path = get_task_file_path(task_id, "result.jpg")
    assert result_path.exists()
```

**Priority**: 🟡 Critical
**Expected**: Full workflow completes
**Dependencies**: All components running

---

## 4. Performance Tests

### 4.1 Load Tests (`tests/performance/test_load.py`)

#### Test Case: Concurrent Task Submission
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_concurrent_task_submission():
    """System should handle 100 concurrent submissions."""
    import asyncio

    async def submit_task():
        return TaskManager.submit_task(
            task_name="classify_image",
            args=["load-test", "/test/image.jpg"]
        )

    start_time = time.time()
    tasks = [submit_task() for _ in range(100)]
    task_ids = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    assert len(task_ids) == 100
    assert duration < 5.0  # Should complete in <5s
```

**Priority**: 🟢 Medium
**Expected**: <5s for 100 tasks
**Dependencies**: Performance baseline

#### Test Case: GPU Worker Throughput
```python
@pytest.mark.performance
def test_gpu_worker_throughput():
    """GPU worker should process 10 tasks/sec."""
    task_ids = []

    start_time = time.time()
    for i in range(50):
        task_id = TaskManager.submit_task(
            task_name="gpu_inference_general",
            args=[f"perf-{i}", "/test/input.jpg"]
        )
        task_ids.append(task_id)

    # Wait for completion
    for task_id in task_ids:
        TaskManager.wait_for_task(task_id, timeout=60)

    duration = time.time() - start_time
    throughput = 50 / duration

    assert throughput >= 10  # At least 10 tasks/sec
```

**Priority**: 🟢 Medium
**Expected**: ≥10 tasks/sec
**Dependencies**: GPU availability

---

## 5. Stress Tests

### 5.1 System Limits (`tests/stress/test_limits.py`)

#### Test Case: Queue Backlog Handling
```python
@pytest.mark.stress
def test_queue_backlog_handling():
    """System should handle queue backlog gracefully."""
    # Submit 1000 tasks rapidly
    task_ids = []
    for i in range(1000):
        task_id = TaskManager.submit_task(
            task_name="classify_image",
            args=[f"stress-{i}", "/test/image.jpg"]
        )
        task_ids.append(task_id)

    # Check all tasks eventually process
    completed = 0
    for task_id in task_ids:
        status = TaskManager.get_task_status(task_id)
        if status.state in [TaskState.SUCCESS, TaskState.FAILURE]:
            completed += 1

    assert completed > 900  # 90% success rate
```

**Priority**: 🟢 Medium
**Expected**: >90% completion
**Dependencies**: Worker capacity

---

## Test Infrastructure Requirements

### Fixtures (`tests/conftest.py`)

```python
@pytest.fixture(scope="session")
def celery_config():
    """Celery configuration for tests."""
    return {
        'broker_url': 'redis://localhost:6379/1',
        'result_backend': 'redis://localhost:6379/1',
        'task_always_eager': False,  # Use real workers
    }

@pytest.fixture
async def async_client():
    """FastAPI test client."""
    from httpx import AsyncClient
    from src.api.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def mock_celery_app(monkeypatch):
    """Mock Celery app for isolated tests."""
    # Mock implementation
    pass
```

### Test Execution Commands

```bash
# Run all tests
pytest tests/

# Unit tests only
pytest tests/unit/ -v

# Integration tests (requires Redis)
pytest tests/integration/ -v

# E2E tests (requires all services)
pytest tests/e2e/ -v --e2e

# Performance tests
pytest tests/performance/ -v --performance

# Coverage report
pytest --cov=src --cov-report=html tests/
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest tests/unit/ -v

  integration-tests:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v3
      - name: Run integration tests
        run: pytest tests/integration/ -v
```

---

## Test Coverage Goals

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| Core Logic | 95%+ | 🟡 Critical |
| Workers | 90%+ | 🟡 Critical |
| API Endpoints | 90%+ | 🔴 High |
| Utils | 85%+ | 🔴 High |
| Models | 80%+ | 🟢 Medium |

---

## Test Execution Priority

1. **🟡 Critical Tests**: Must pass before deployment
   - API integration tests
   - Worker communication tests
   - Core task manager logic

2. **🔴 High Priority**: Should pass before merge
   - Storage utilities
   - Task status tracking
   - Error handling

3. **🟢 Medium Priority**: Monitor and improve
   - Performance benchmarks
   - Stress tests
   - Edge cases

---

## Next Steps

1. Create `tests/` directory structure
2. Implement `conftest.py` with fixtures
3. Write unit tests for models and utils (fastest to implement)
4. Set up integration test environment (Redis, workers)
5. Implement API integration tests
6. Add E2E tests for complete workflows
7. Configure CI/CD pipeline with test automation