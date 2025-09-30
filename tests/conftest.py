"""Pytest configuration and shared fixtures."""
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, MagicMock

# Set up event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Celery configuration fixtures
@pytest.fixture(scope="session")
def celery_config():
    """Celery configuration for tests."""
    return {
        "broker_url": "redis://localhost:6379/1",
        "result_backend": "redis://localhost:6379/1",
        "task_always_eager": False,  # Use real workers in integration tests
        "task_eager_propagates": True,
        "task_ignore_result": False,
    }


@pytest.fixture(scope="session")
def celery_config_eager():
    """Celery configuration for unit tests (eager mode)."""
    return {
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_always_eager": True,
        "task_eager_propagates": True,
        "task_ignore_result": False,
    }


@pytest.fixture
def celery_app_eager(celery_config_eager):
    """Celery app with eager mode for unit tests."""
    from src.core.celery_app import celery_app

    celery_app.conf.update(celery_config_eager)
    yield celery_app
    celery_app.conf.update(celery_config_eager)


# FastAPI test client fixtures
@pytest.fixture
async def async_client() -> AsyncGenerator:
    """FastAPI async test client."""
    from httpx import AsyncClient, ASGITransport
    from src.api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def sync_client():
    """FastAPI sync test client."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)


# Storage fixtures
@pytest.fixture
def temp_storage(tmp_path, monkeypatch) -> Generator[Path, None, None]:
    """Temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir(exist_ok=True)

    # Monkey patch settings.shared_tmp_path
    from src.core.config import settings
    monkeypatch.setattr(settings, "shared_tmp_path", str(storage_dir))

    yield storage_dir

    # Cleanup
    if storage_dir.exists():
        shutil.rmtree(storage_dir)


@pytest.fixture
def task_id() -> str:
    """Generate test task ID."""
    import uuid
    return f"test-task-{uuid.uuid4().hex[:8]}"


# Mock fixtures
@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    return mock


@pytest.fixture
def mock_celery_result():
    """Mock Celery AsyncResult."""
    mock = MagicMock()
    mock.id = "mock-task-id"
    mock.state = "SUCCESS"
    mock.result = {"status": "completed"}
    mock.successful.return_value = True
    mock.failed.return_value = False
    return mock


# Image fixtures
@pytest.fixture
def sample_image(tmp_path) -> Path:
    """Create sample test image."""
    from PIL import Image

    img = Image.new("RGB", (800, 600), color="blue")
    img_path = tmp_path / "sample.jpg"
    img.save(img_path, "JPEG")

    return img_path


@pytest.fixture
def portrait_image(tmp_path) -> Path:
    """Create portrait aspect ratio image."""
    from PIL import Image

    img = Image.new("RGB", (800, 1000), color="red")
    img_path = tmp_path / "portrait.jpg"
    img.save(img_path, "JPEG")

    return img_path


@pytest.fixture
def landscape_image(tmp_path) -> Path:
    """Create landscape aspect ratio image."""
    from PIL import Image

    img = Image.new("RGB", (1920, 1080), color="green")
    img_path = tmp_path / "landscape.jpg"
    img.save(img_path, "JPEG")

    return img_path


# HTTP mock fixtures
@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for IO worker tests."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake_image_data"
    mock_response.raise_for_status = MagicMock()

    mock_client.get.return_value = mock_response
    mock_client.put.return_value = mock_response

    return mock_client


# Pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (requires Redis, workers)"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end tests (requires full system)"
    )
    config.addinivalue_line(
        "markers", "performance: Performance benchmarking tests"
    )
    config.addinivalue_line(
        "markers", "stress: Stress and load tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )


# Skip conditions
@pytest.fixture
def skip_if_no_redis():
    """Skip test if Redis is not available."""
    import redis

    try:
        r = redis.Redis(host="localhost", port=6379, db=1)
        r.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip("Redis not available")


@pytest.fixture
def skip_if_no_gpu():
    """Skip test if GPU is not available."""
    import os

    if not os.environ.get("CUDA_VISIBLE_DEVICES"):
        pytest.skip("GPU not available")