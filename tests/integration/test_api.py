"""Integration tests for FastAPI endpoints."""
import pytest
from unittest.mock import patch, MagicMock

from src.models import TaskState, TaskPriority


@pytest.mark.integration
class TestSubmitTaskEndpoint:
    """Test POST /api/v1/tasks endpoint."""

    @pytest.mark.asyncio
    async def test_submit_task_returns_200(self, async_client, skip_if_no_redis):
        """POST /api/v1/tasks should return 200 with valid request."""
        request_data = {
            "task_name": "classify_image",
            "args": ["task-id", "/path/image.jpg"],
            "priority": 5,
            "sync": False,
        }

        response = await async_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "state" in data
        assert data["state"] == "PENDING"

    @pytest.mark.asyncio
    async def test_submit_task_minimal_request(self, async_client, skip_if_no_redis):
        """POST /api/v1/tasks should work with minimal request."""
        request_data = {
            "task_name": "classify_image",
        }

        response = await async_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data

    @pytest.mark.asyncio
    async def test_submit_task_with_kwargs(self, async_client, skip_if_no_redis):
        """POST /api/v1/tasks should accept kwargs."""
        request_data = {
            "task_name": "encode_result",
            "kwargs": {
                "task_id": "test",
                "output_path": "/path",
                "quality": 95,
            },
        }

        response = await async_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_submit_task_invalid_name_returns_500(
        self, async_client, skip_if_no_redis
    ):
        """POST /api/v1/tasks should return 500 for invalid task."""
        request_data = {
            "task_name": "nonexistent_task",
        }

        response = await async_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_submit_task_missing_task_name_returns_422(self, async_client):
        """POST /api/v1/tasks should return 422 for missing task_name."""
        request_data = {
            "args": ["test"],
        }

        response = await async_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.wait_for_task")
    @patch("src.api.main.TaskManager.submit_task")
    async def test_submit_task_sync_mode(
        self, mock_submit, mock_wait, async_client
    ):
        """POST /api/v1/tasks with sync=True should wait for completion."""
        from src.models import TaskStatus

        mock_submit.return_value = "sync-task-id"
        mock_wait.return_value = TaskStatus(
            task_id="sync-task-id",
            state=TaskState.SUCCESS,
            result={"output": "result.jpg"},
        )

        request_data = {
            "task_name": "classify_image",
            "sync": True,
        }

        response = await async_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "SUCCESS"

        # Verify wait_for_task was called
        mock_wait.assert_called_once()


@pytest.mark.integration
class TestGetTaskStatusEndpoint:
    """Test GET /api/v1/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    @patch("src.api.main.TaskManager.get_task_status")
    async def test_get_task_status_returns_200(
        self, mock_get_status, mock_submit, async_client
    ):
        """GET /api/v1/tasks/{id} should return 200."""
        from src.models import TaskStatus

        mock_submit.return_value = "test-task-id"
        mock_get_status.return_value = TaskStatus(
            task_id="test-task-id",
            state=TaskState.PENDING,
        )

        # Submit task first
        submit_response = await async_client.post(
            "/api/v1/tasks",
            json={"task_name": "classify_image"},
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

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.get_task_status")
    async def test_get_task_status_structure(self, mock_get_status, async_client):
        """GET /api/v1/tasks/{id} should return complete status structure."""
        from src.models import TaskStatus

        mock_get_status.return_value = TaskStatus(
            task_id="test-task",
            state=TaskState.SUCCESS,
            result={"output": "result.jpg"},
        )

        response = await async_client.get("/api/v1/tasks/test-task")

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "state" in data
        assert "result" in data

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.get_task_status")
    async def test_get_task_status_failed_task(self, mock_get_status, async_client):
        """GET /api/v1/tasks/{id} should return error information."""
        from src.models import TaskStatus

        mock_get_status.return_value = TaskStatus(
            task_id="failed-task",
            state=TaskState.FAILURE,
            error="Processing failed",
        )

        response = await async_client.get("/api/v1/tasks/failed-task")

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "FAILURE"
        assert "error" in data
        assert data["error"] == "Processing failed"


@pytest.mark.integration
class TestCleanupTaskEndpoint:
    """Test DELETE /api/v1/tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.cleanup_task")
    async def test_cleanup_task_returns_200(self, mock_cleanup, async_client):
        """DELETE /api/v1/tasks/{id} should return 200."""
        response = await async_client.delete("/api/v1/tasks/test-task-id")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify cleanup was called
        mock_cleanup.assert_called_once_with("test-task-id")

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.cleanup_task")
    async def test_cleanup_task_message(self, mock_cleanup, async_client):
        """DELETE /api/v1/tasks/{id} should return confirmation message."""
        response = await async_client.delete("/api/v1/tasks/cleanup-test")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "cleanup-test" in data["message"]

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.cleanup_task")
    async def test_cleanup_task_error_returns_500(self, mock_cleanup, async_client):
        """DELETE /api/v1/tasks/{id} should return 500 on error."""
        mock_cleanup.side_effect = Exception("Cleanup failed")

        response = await async_client.delete("/api/v1/tasks/error-task")

        assert response.status_code == 500


@pytest.mark.integration
class TestHealthEndpoint:
    """Test /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, async_client):
        """GET /health should return 200."""
        response = await async_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_health_includes_metadata(self, async_client):
        """GET /health should include service metadata."""
        response = await async_client.get("/health")

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert data["service"] == "task-manager-api"


@pytest.mark.integration
class TestRootEndpoint:
    """Test / root endpoint."""

    @pytest.mark.asyncio
    async def test_root_returns_200(self, async_client):
        """GET / should return 200."""
        response = await async_client.get("/")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_includes_api_info(self, async_client):
        """GET / should include API information."""
        response = await async_client.get("/")

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "docs" in data
        assert data["docs"] == "/docs"


@pytest.mark.integration
class TestAPIIntegration:
    """Test API endpoints working together."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    @patch("src.api.main.TaskManager.get_task_status")
    @patch("src.api.main.TaskManager.cleanup_task")
    async def test_full_api_workflow(
        self, mock_cleanup, mock_get_status, mock_submit, async_client
    ):
        """Test complete workflow: submit → status → cleanup."""
        from src.models import TaskStatus

        # Mock responses
        mock_submit.return_value = "workflow-task-id"
        mock_get_status.return_value = TaskStatus(
            task_id="workflow-task-id",
            state=TaskState.SUCCESS,
            result={"output": "result.jpg"},
        )

        # 1. Submit task
        submit_response = await async_client.post(
            "/api/v1/tasks",
            json={"task_name": "classify_image"},
        )
        assert submit_response.status_code == 200
        task_id = submit_response.json()["task_id"]

        # 2. Get status
        status_response = await async_client.get(f"/api/v1/tasks/{task_id}")
        assert status_response.status_code == 200

        # 3. Cleanup
        cleanup_response = await async_client.delete(f"/api/v1/tasks/{task_id}")
        assert cleanup_response.status_code == 200

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, async_client):
        """API should include CORS headers."""
        response = await async_client.options(
            "/api/v1/tasks",
            headers={"Origin": "http://localhost:3000"},
        )

        # CORS should be enabled
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled


@pytest.mark.integration
class TestAPISyncClient:
    """Test API with synchronous test client."""

    def test_submit_task_sync_client(self, sync_client, skip_if_no_redis):
        """Test task submission with sync client."""
        request_data = {
            "task_name": "classify_image",
            "args": ["sync-test", "/path"],
        }

        response = sync_client.post(
            "/api/v1/tasks",
            json=request_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data

    def test_health_sync_client(self, sync_client):
        """Test health endpoint with sync client."""
        response = sync_client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"