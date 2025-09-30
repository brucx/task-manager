"""Integration tests for TaskManager."""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.core.task_manager import TaskManager
from src.models import TaskState, TaskPriority, SubTaskConfig, WorkerType


@pytest.mark.integration
class TestSubmitTask:
    """Test task submission functionality."""

    def test_submit_task_returns_id(self, skip_if_no_redis):
        """submit_task should return valid task ID."""
        task_id = TaskManager.submit_task(
            task_name="classify_image",
            args=["test-id", "/path/to/image.jpg"],
            priority=5,
        )

        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0

    def test_submit_task_with_kwargs(self, skip_if_no_redis):
        """submit_task should accept kwargs."""
        task_id = TaskManager.submit_task(
            task_name="encode_result",
            kwargs={"task_id": "test", "output_path": "/path", "quality": 95},
        )

        assert task_id is not None

    def test_submit_task_with_priority(self, skip_if_no_redis):
        """submit_task should accept priority parameter."""
        high_priority_task = TaskManager.submit_task(
            task_name="classify_image",
            priority=TaskPriority.HIGH,
        )

        low_priority_task = TaskManager.submit_task(
            task_name="classify_image",
            priority=TaskPriority.LOW,
        )

        assert high_priority_task is not None
        assert low_priority_task is not None

    def test_submit_task_invalid_name_raises_error(self, skip_if_no_redis):
        """submit_task should raise error for invalid task name."""
        with pytest.raises(ValueError, match="not found"):
            TaskManager.submit_task(task_name="nonexistent_task")

    def test_submit_multiple_tasks(self, skip_if_no_redis):
        """Should be able to submit multiple tasks."""
        task_ids = []

        for i in range(5):
            task_id = TaskManager.submit_task(
                task_name="classify_image",
                args=[f"task-{i}", "/path/image.jpg"],
            )
            task_ids.append(task_id)

        assert len(task_ids) == 5
        assert len(set(task_ids)) == 5  # All unique


@pytest.mark.integration
class TestSubmitSubtasks:
    """Test subtask submission functionality."""

    def test_submit_parallel_subtasks(self, skip_if_no_redis):
        """Parallel subtasks should all receive IDs."""
        subtask_configs = [
            SubTaskConfig(
                name="classify_image",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
                args=["task1", "/path1"],
            ),
            SubTaskConfig(
                name="classify_image",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
                args=["task2", "/path2"],
            ),
        ]

        subtask_ids = TaskManager.submit_subtasks(
            parent_task_id="parent-123",
            subtask_configs=subtask_configs,
            parallel=True,
        )

        assert len(subtask_ids) == 2
        assert all(isinstance(sid, str) for sid in subtask_ids)

    def test_submit_sequential_subtasks(self, skip_if_no_redis):
        """Sequential subtasks should return chained task ID."""
        subtask_configs = [
            SubTaskConfig(
                name="classify_image",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
            ),
            SubTaskConfig(
                name="encode_result",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
            ),
        ]

        subtask_ids = TaskManager.submit_subtasks(
            parent_task_id="parent-456",
            subtask_configs=subtask_configs,
            parallel=False,
        )

        # Sequential mode returns single chain ID
        assert len(subtask_ids) == 1
        assert isinstance(subtask_ids[0], str)

    def test_submit_subtasks_with_priority(self, skip_if_no_redis):
        """Subtasks should respect priority settings."""
        subtask_configs = [
            SubTaskConfig(
                name="classify_image",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
                priority=TaskPriority.HIGH,
            ),
        ]

        subtask_ids = TaskManager.submit_subtasks(
            parent_task_id="parent-789",
            subtask_configs=subtask_configs,
            parallel=True,
        )

        assert len(subtask_ids) == 1

    def test_submit_subtasks_invalid_task_raises_error(self, skip_if_no_redis):
        """submit_subtasks should raise error for invalid task."""
        subtask_configs = [
            SubTaskConfig(
                name="nonexistent_task",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
            ),
        ]

        with pytest.raises(ValueError, match="not found"):
            TaskManager.submit_subtasks(
                parent_task_id="parent",
                subtask_configs=subtask_configs,
            )


@pytest.mark.integration
class TestGetTaskStatus:
    """Test task status retrieval."""

    def test_get_task_status_pending(self, skip_if_no_redis):
        """New task should have PENDING or RECEIVED state."""
        task_id = TaskManager.submit_task(
            task_name="classify_image",
            args=["test", "/path"],
        )

        status = TaskManager.get_task_status(task_id)

        assert status.task_id == task_id
        assert status.state in [TaskState.PENDING, TaskState.RECEIVED, TaskState.STARTED]

    def test_get_task_status_structure(self, skip_if_no_redis):
        """Task status should have correct structure."""
        task_id = TaskManager.submit_task(
            task_name="classify_image",
            args=["test", "/path"],
        )

        status = TaskManager.get_task_status(task_id)

        assert hasattr(status, "task_id")
        assert hasattr(status, "state")
        assert hasattr(status, "result")
        assert hasattr(status, "error")

    def test_get_task_status_nonexistent(self, skip_if_no_redis):
        """Getting status of nonexistent task should return PENDING."""
        status = TaskManager.get_task_status("nonexistent-task-id")

        # Celery returns PENDING for unknown tasks
        assert status.state == TaskState.PENDING


@pytest.mark.integration
@pytest.mark.slow
class TestWaitForTask:
    """Test synchronous task waiting."""

    @patch("src.core.task_manager.TaskManager.get_task_status")
    def test_wait_for_task_success(self, mock_get_status):
        """wait_for_task should return when task succeeds."""
        # Mock progression: PENDING → STARTED → SUCCESS
        from src.models import TaskStatus

        mock_get_status.side_effect = [
            TaskStatus(task_id="test", state=TaskState.PENDING),
            TaskStatus(task_id="test", state=TaskState.STARTED),
            TaskStatus(task_id="test", state=TaskState.SUCCESS, result={"done": True}),
        ]

        status = TaskManager.wait_for_task("test", timeout=5.0, poll_interval=0.1)

        assert status.state == TaskState.SUCCESS
        assert status.result == {"done": True}

    @patch("src.core.task_manager.TaskManager.get_task_status")
    def test_wait_for_task_failure(self, mock_get_status):
        """wait_for_task should return when task fails."""
        from src.models import TaskStatus

        mock_get_status.return_value = TaskStatus(
            task_id="test",
            state=TaskState.FAILURE,
            error="Processing error",
        )

        status = TaskManager.wait_for_task("test", timeout=5.0)

        assert status.state == TaskState.FAILURE
        assert status.error == "Processing error"

    @patch("src.core.task_manager.TaskManager.get_task_status")
    def test_wait_for_task_timeout(self, mock_get_status):
        """wait_for_task should timeout if task doesn't complete."""
        from src.models import TaskStatus

        # Always return PENDING
        mock_get_status.return_value = TaskStatus(
            task_id="test",
            state=TaskState.PENDING,
        )

        status = TaskManager.wait_for_task("test", timeout=0.5, poll_interval=0.1)

        assert status.state == TaskState.TIMEOUT
        assert "timeout" in status.error.lower()

    @patch("src.core.task_manager.TaskManager.get_task_status")
    def test_wait_for_task_revoked(self, mock_get_status):
        """wait_for_task should return when task is revoked."""
        from src.models import TaskStatus

        mock_get_status.return_value = TaskStatus(
            task_id="test",
            state=TaskState.REVOKED,
        )

        status = TaskManager.wait_for_task("test", timeout=5.0)

        assert status.state == TaskState.REVOKED


@pytest.mark.integration
class TestCleanupTask:
    """Test task cleanup functionality."""

    def test_cleanup_task_removes_directory(self, temp_storage, task_id):
        """cleanup_task should remove task directory."""
        from src.utils.storage import get_task_dir, save_task_data

        # Create task files
        save_task_data(task_id, "test.txt", b"data")
        task_dir = get_task_dir(task_id)
        assert task_dir.exists()

        # Cleanup
        TaskManager.cleanup_task(task_id)

        # Verify removed
        assert not task_dir.exists()

    def test_cleanup_nonexistent_task(self, temp_storage):
        """cleanup_task should handle nonexistent task gracefully."""
        # Should not raise error
        TaskManager.cleanup_task("nonexistent-task")

    def test_cleanup_task_with_multiple_files(self, temp_storage, task_id):
        """cleanup_task should remove all task files."""
        from src.utils.storage import get_task_dir, save_task_data

        # Create multiple files
        save_task_data(task_id, "file1.txt", b"data1")
        save_task_data(task_id, "file2.txt", b"data2")
        save_task_data(task_id, "subdir/file3.txt", b"data3")

        task_dir = get_task_dir(task_id)
        assert task_dir.exists()

        # Cleanup
        TaskManager.cleanup_task(task_id)

        # All should be removed
        assert not task_dir.exists()


@pytest.mark.integration
class TestTaskManagerIntegration:
    """Test TaskManager methods working together."""

    def test_submit_get_status_cleanup_flow(self, skip_if_no_redis, temp_storage):
        """Test complete flow: submit → status → cleanup."""
        # 1. Submit task
        task_id = TaskManager.submit_task(
            task_name="classify_image",
            args=["integration-test", "/path/image.jpg"],
        )

        assert task_id is not None

        # 2. Get status
        status = TaskManager.get_task_status(task_id)
        assert status.task_id == task_id
        assert status.state in [
            TaskState.PENDING,
            TaskState.RECEIVED,
            TaskState.STARTED,
        ]

        # 3. Cleanup (even though task may still be running)
        TaskManager.cleanup_task(task_id)

    def test_parallel_subtask_submission_and_tracking(self, skip_if_no_redis):
        """Test submitting and tracking parallel subtasks."""
        # Submit parent task
        parent_id = TaskManager.submit_task(
            task_name="classify_image",
            args=["parent", "/path"],
        )

        # Submit subtasks
        subtask_configs = [
            SubTaskConfig(
                name="encode_result",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
            ),
            SubTaskConfig(
                name="encode_result",
                worker_type=WorkerType.CPU,
                queue="cpu_queue",
            ),
        ]

        subtask_ids = TaskManager.submit_subtasks(
            parent_task_id=parent_id,
            subtask_configs=subtask_configs,
            parallel=True,
        )

        # Track all tasks
        for subtask_id in subtask_ids:
            status = TaskManager.get_task_status(subtask_id)
            assert status.task_id == subtask_id