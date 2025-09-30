"""End-to-end workflow tests."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.models import TaskState


@pytest.mark.e2e
@pytest.mark.slow
class TestSuperResolutionWorkflow:
    """Test complete super-resolution workflow."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.wait_for_task")
    @patch("src.api.main.TaskManager.submit_task")
    async def test_complete_workflow_via_api(
        self, mock_submit, mock_wait, async_client, temp_storage
    ):
        """Complete super resolution from API to result."""
        from src.models import TaskStatus

        # Mock task completion
        mock_submit.return_value = "e2e-test-task"
        mock_wait.return_value = TaskStatus(
            task_id="e2e-test-task",
            state=TaskState.SUCCESS,
            result={"output": "result.jpg"},
        )

        # Submit via API
        response = await async_client.post(
            "/api/v1/tasks",
            json={
                "task_name": "classify_image",
                "kwargs": {
                    "task_id": "e2e-test",
                    "image_path": "/test/image.jpg",
                },
                "sync": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == TaskState.SUCCESS

    @pytest.mark.asyncio
    @patch("src.workers.io_worker.download_image.delay")
    @patch("src.workers.cpu_worker.classify_image.delay")
    @patch("src.workers.gpu_worker.gpu_inference_general.delay")
    @patch("src.workers.cpu_worker.encode_result.delay")
    async def test_full_pipeline_with_workers(
        self,
        mock_encode,
        mock_gpu,
        mock_classify,
        mock_download,
        temp_storage,
        sample_image,
    ):
        """Test complete pipeline: download → classify → GPU → encode."""
        from celery.result import AsyncResult

        # Mock each step returning the next input
        mock_download_result = MagicMock(spec=AsyncResult)
        mock_download_result.get.return_value = str(sample_image)
        mock_download.return_value = mock_download_result

        mock_classify_result = MagicMock(spec=AsyncResult)
        mock_classify_result.get.return_value = {
            "category": "general",
            "width": 800,
            "height": 600,
        }
        mock_classify.return_value = mock_classify_result

        mock_gpu_result = MagicMock(spec=AsyncResult)
        mock_gpu_result.get.return_value = str(sample_image)
        mock_gpu.return_value = mock_gpu_result

        mock_encode_result = MagicMock(spec=AsyncResult)
        mock_encode_result.get.return_value = str(sample_image)
        mock_encode.return_value = mock_encode_result

        # Execute pipeline
        # 1. Download
        download_result = mock_download("test-workflow", "https://example.com/test.jpg")
        input_path = download_result.get(timeout=30)
        assert input_path is not None

        # 2. Classify
        classify_result = mock_classify("test-workflow", input_path)
        classification = classify_result.get(timeout=10)
        assert classification["category"] == "general"

        # 3. GPU inference
        gpu_result = mock_gpu("test-workflow", input_path)
        output_path = gpu_result.get(timeout=60)
        assert output_path is not None

        # 4. Encode
        encode_final = mock_encode("test-workflow", output_path)
        final_path = encode_final.get(timeout=10)
        assert final_path is not None


@pytest.mark.e2e
class TestAsyncWorkflow:
    """Test async workflow without waiting for completion."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    async def test_async_submission_returns_immediately(
        self, mock_submit, async_client
    ):
        """Async mode should return immediately without waiting."""
        import time

        mock_submit.return_value = "async-task-id"

        start_time = time.time()

        response = await async_client.post(
            "/api/v1/tasks",
            json={
                "task_name": "classify_image",
                "sync": False,  # Async mode
            },
        )

        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 1.0  # Should return quickly
        data = response.json()
        assert data["state"] == "PENDING"

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    @patch("src.api.main.TaskManager.get_task_status")
    async def test_async_workflow_poll_for_status(
        self, mock_get_status, mock_submit, async_client
    ):
        """Async workflow: submit → poll status until complete."""
        from src.models import TaskStatus

        mock_submit.return_value = "poll-task-id"

        # Simulate progression
        status_sequence = [
            TaskStatus(task_id="poll-task-id", state=TaskState.PENDING),
            TaskStatus(task_id="poll-task-id", state=TaskState.STARTED),
            TaskStatus(
                task_id="poll-task-id",
                state=TaskState.SUCCESS,
                result={"output": "done"},
            ),
        ]

        mock_get_status.side_effect = status_sequence

        # 1. Submit
        submit_response = await async_client.post(
            "/api/v1/tasks",
            json={"task_name": "classify_image", "sync": False},
        )
        task_id = submit_response.json()["task_id"]

        # 2. Poll status
        for _ in range(3):
            status_response = await async_client.get(f"/api/v1/tasks/{task_id}")
            status = status_response.json()

            if status["state"] == "SUCCESS":
                assert status["result"]["output"] == "done"
                break


@pytest.mark.e2e
class TestErrorHandling:
    """Test error handling in E2E workflows."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.wait_for_task")
    @patch("src.api.main.TaskManager.submit_task")
    async def test_task_failure_handling(
        self, mock_submit, mock_wait, async_client
    ):
        """System should handle task failures gracefully."""
        from src.models import TaskStatus

        mock_submit.return_value = "failed-task"
        mock_wait.return_value = TaskStatus(
            task_id="failed-task",
            state=TaskState.FAILURE,
            error="Processing failed: Invalid input",
        )

        response = await async_client.post(
            "/api/v1/tasks",
            json={
                "task_name": "classify_image",
                "sync": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "FAILURE"

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.wait_for_task")
    @patch("src.api.main.TaskManager.submit_task")
    async def test_timeout_handling(self, mock_submit, mock_wait, async_client):
        """System should handle timeouts gracefully."""
        from src.models import TaskStatus

        mock_submit.return_value = "timeout-task"
        mock_wait.return_value = TaskStatus(
            task_id="timeout-task",
            state=TaskState.TIMEOUT,
            error="Task timeout after 120s in queue",
        )

        response = await async_client.post(
            "/api/v1/tasks",
            json={
                "task_name": "classify_image",
                "sync": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "TIMEOUT"


@pytest.mark.e2e
class TestCleanupWorkflow:
    """Test cleanup in E2E workflows."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    @patch("src.api.main.TaskManager.get_task_status")
    @patch("src.api.main.TaskManager.cleanup_task")
    async def test_complete_lifecycle_with_cleanup(
        self, mock_cleanup, mock_get_status, mock_submit, async_client, temp_storage
    ):
        """Test complete lifecycle: submit → complete → cleanup."""
        from src.models import TaskStatus

        mock_submit.return_value = "lifecycle-task"
        mock_get_status.return_value = TaskStatus(
            task_id="lifecycle-task",
            state=TaskState.SUCCESS,
            result={"output": "result.jpg"},
        )

        # 1. Submit
        submit_response = await async_client.post(
            "/api/v1/tasks",
            json={"task_name": "classify_image"},
        )
        task_id = submit_response.json()["task_id"]

        # 2. Wait for completion (by checking status)
        status_response = await async_client.get(f"/api/v1/tasks/{task_id}")
        assert status_response.json()["state"] == "SUCCESS"

        # 3. Cleanup
        cleanup_response = await async_client.delete(f"/api/v1/tasks/{task_id}")
        assert cleanup_response.status_code == 200

        mock_cleanup.assert_called_once_with(task_id)


@pytest.mark.e2e
@pytest.mark.slow
class TestMultipleWorkflows:
    """Test multiple workflows running concurrently."""

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    async def test_concurrent_task_submissions(self, mock_submit, async_client):
        """System should handle multiple concurrent submissions."""
        import asyncio

        # Generate unique task IDs
        mock_submit.side_effect = [f"concurrent-task-{i}" for i in range(10)]

        # Submit multiple tasks concurrently
        tasks = []
        for i in range(10):
            task = async_client.post(
                "/api/v1/tasks",
                json={"task_name": "classify_image"},
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.status_code == 200 for r in responses)

        # All should have unique task IDs
        task_ids = [r.json()["task_id"] for r in responses]
        assert len(set(task_ids)) == 10

    @pytest.mark.asyncio
    @patch("src.api.main.TaskManager.submit_task")
    @patch("src.api.main.TaskManager.get_task_status")
    async def test_interleaved_submit_and_status_checks(
        self, mock_get_status, mock_submit, async_client
    ):
        """System should handle interleaved submissions and status checks."""
        from src.models import TaskStatus

        mock_submit.side_effect = ["task-1", "task-2", "task-3"]
        mock_get_status.side_effect = [
            TaskStatus(task_id="task-1", state=TaskState.PENDING),
            TaskStatus(task_id="task-2", state=TaskState.STARTED),
            TaskStatus(task_id="task-3", state=TaskState.SUCCESS),
        ]

        # Submit task 1
        r1 = await async_client.post(
            "/api/v1/tasks", json={"task_name": "classify_image"}
        )
        task1_id = r1.json()["task_id"]

        # Check task 1 status
        s1 = await async_client.get(f"/api/v1/tasks/{task1_id}")

        # Submit task 2
        r2 = await async_client.post(
            "/api/v1/tasks", json={"task_name": "classify_image"}
        )
        task2_id = r2.json()["task_id"]

        # Check task 2 status
        s2 = await async_client.get(f"/api/v1/tasks/{task2_id}")

        # Submit task 3
        r3 = await async_client.post(
            "/api/v1/tasks", json={"task_name": "classify_image"}
        )
        task3_id = r3.json()["task_id"]

        # Check task 3 status
        s3 = await async_client.get(f"/api/v1/tasks/{task3_id}")

        # All operations should succeed
        assert all(r.status_code == 200 for r in [r1, r2, r3, s1, s2, s3])