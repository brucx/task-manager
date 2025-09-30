"""Unit tests for task models."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models import (
    WorkerType,
    TaskState,
    TaskPriority,
    SubTaskConfig,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TaskMetrics,
)


class TestWorkerType:
    """Test WorkerType enum."""

    def test_worker_type_values(self):
        """Validate WorkerType enum contains all required types."""
        assert WorkerType.IO == "io"
        assert WorkerType.CPU == "cpu"
        assert WorkerType.GPU == "gpu"

    def test_worker_type_from_string(self):
        """WorkerType should be constructable from string."""
        assert WorkerType("io") == WorkerType.IO
        assert WorkerType("cpu") == WorkerType.CPU
        assert WorkerType("gpu") == WorkerType.GPU


class TestTaskState:
    """Test TaskState enum."""

    def test_task_state_values(self):
        """Validate TaskState enum contains all required states."""
        assert TaskState.PENDING == "PENDING"
        assert TaskState.RECEIVED == "RECEIVED"
        assert TaskState.STARTED == "STARTED"
        assert TaskState.SUCCESS == "SUCCESS"
        assert TaskState.FAILURE == "FAILURE"
        assert TaskState.TIMEOUT == "TIMEOUT"
        assert TaskState.REVOKED == "REVOKED"

    def test_task_state_from_string(self):
        """TaskState should be constructable from string."""
        assert TaskState("PENDING") == TaskState.PENDING
        assert TaskState("SUCCESS") == TaskState.SUCCESS
        assert TaskState("FAILURE") == TaskState.FAILURE


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_task_priority_values(self):
        """Validate TaskPriority enum values."""
        assert TaskPriority.LOW == 0
        assert TaskPriority.NORMAL == 5
        assert TaskPriority.HIGH == 10

    def test_priority_ordering(self):
        """Priority should be orderable."""
        assert TaskPriority.LOW < TaskPriority.NORMAL
        assert TaskPriority.NORMAL < TaskPriority.HIGH


class TestSubTaskConfig:
    """Test SubTaskConfig model."""

    def test_valid_subtask_config(self):
        """Valid subtask configuration should be accepted."""
        config = SubTaskConfig(
            name="test_task",
            worker_type=WorkerType.CPU,
            queue="cpu_queue",
            priority=TaskPriority.HIGH,
        )

        assert config.name == "test_task"
        assert config.worker_type == WorkerType.CPU
        assert config.queue == "cpu_queue"
        assert config.priority == TaskPriority.HIGH
        assert config.args == []
        assert config.kwargs == {}
        assert config.timeout is None

    def test_subtask_config_with_args(self):
        """SubTaskConfig should accept args and kwargs."""
        config = SubTaskConfig(
            name="test_task",
            worker_type=WorkerType.GPU,
            queue="gpu_queue",
            args=["arg1", "arg2"],
            kwargs={"key": "value"},
            timeout=300,
        )

        assert config.args == ["arg1", "arg2"]
        assert config.kwargs == {"key": "value"}
        assert config.timeout == 300

    def test_subtask_config_defaults(self):
        """SubTaskConfig should apply correct defaults."""
        config = SubTaskConfig(
            name="test_task",
            worker_type=WorkerType.IO,
            queue="io_queue",
        )

        assert config.priority == TaskPriority.NORMAL
        assert config.args == []
        assert config.kwargs == {}
        assert config.timeout is None

    def test_subtask_config_validation_error(self):
        """SubTaskConfig should reject invalid data."""
        with pytest.raises(ValidationError):
            SubTaskConfig(
                name="test_task",
                worker_type="invalid_type",  # Invalid type
                queue="queue",
            )


class TestTaskRequest:
    """Test TaskRequest model."""

    def test_minimal_task_request(self):
        """Minimal TaskRequest should work with defaults."""
        request = TaskRequest(task_name="classify_image")

        assert request.task_name == "classify_image"
        assert request.args == []
        assert request.kwargs == {}
        assert request.priority == TaskPriority.NORMAL
        assert request.sync is False

    def test_task_request_with_args(self):
        """TaskRequest should accept args and kwargs."""
        request = TaskRequest(
            task_name="process_image",
            args=["task-id", "/path/to/image"],
            kwargs={"quality": 95},
            priority=TaskPriority.HIGH,
            sync=True,
        )

        assert request.task_name == "process_image"
        assert request.args == ["task-id", "/path/to/image"]
        assert request.kwargs == {"quality": 95}
        assert request.priority == TaskPriority.HIGH
        assert request.sync is True

    def test_task_request_defaults(self):
        """TaskRequest should apply correct defaults."""
        request = TaskRequest(task_name="test_task")

        assert request.args == []
        assert request.kwargs == {}
        assert request.priority == TaskPriority.NORMAL
        assert request.sync is False

    def test_task_request_validation(self):
        """TaskRequest should validate required fields."""
        with pytest.raises(ValidationError):
            TaskRequest()  # Missing task_name


class TestTaskResponse:
    """Test TaskResponse model."""

    def test_task_response_creation(self):
        """TaskResponse should be created with required fields."""
        response = TaskResponse(
            task_id="test-task-123",
            state=TaskState.PENDING,
        )

        assert response.task_id == "test-task-123"
        assert response.state == TaskState.PENDING
        assert isinstance(response.submitted_at, datetime)

    def test_task_response_submitted_at_default(self):
        """TaskResponse should auto-generate submitted_at."""
        response1 = TaskResponse(
            task_id="task1",
            state=TaskState.PENDING,
        )

        response2 = TaskResponse(
            task_id="task2",
            state=TaskState.PENDING,
        )

        assert response1.submitted_at is not None
        assert response2.submitted_at is not None
        # Should be very close in time
        time_diff = abs((response2.submitted_at - response1.submitted_at).total_seconds())
        assert time_diff < 1.0


class TestTaskStatus:
    """Test TaskStatus model."""

    def test_task_status_minimal(self):
        """TaskStatus should work with minimal fields."""
        status = TaskStatus(
            task_id="test-task",
            state=TaskState.PENDING,
        )

        assert status.task_id == "test-task"
        assert status.state == TaskState.PENDING
        assert status.progress is None
        assert status.result is None
        assert status.error is None
        assert status.subtasks == []

    def test_task_status_complete(self):
        """TaskStatus should accept all fields."""
        submitted_at = datetime.utcnow()
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow()

        status = TaskStatus(
            task_id="test-task",
            state=TaskState.SUCCESS,
            progress=100.0,
            result={"output": "result.jpg"},
            submitted_at=submitted_at,
            started_at=started_at,
            completed_at=completed_at,
            subtasks=["sub1", "sub2"],
        )

        assert status.state == TaskState.SUCCESS
        assert status.progress == 100.0
        assert status.result == {"output": "result.jpg"}
        assert status.submitted_at == submitted_at
        assert status.started_at == started_at
        assert status.completed_at == completed_at
        assert status.subtasks == ["sub1", "sub2"]

    def test_task_status_with_error(self):
        """TaskStatus should store error information."""
        status = TaskStatus(
            task_id="failed-task",
            state=TaskState.FAILURE,
            error="Processing failed: Invalid input",
        )

        assert status.state == TaskState.FAILURE
        assert status.error == "Processing failed: Invalid input"


class TestTaskMetrics:
    """Test TaskMetrics model."""

    def test_task_metrics_creation(self):
        """TaskMetrics should be created with all required fields."""
        metrics = TaskMetrics(
            task_id="metrics-task",
            task_name="classify_image",
            worker_type=WorkerType.CPU,
            queue_time=1.5,
            execution_time=3.2,
            total_time=4.7,
            success=True,
        )

        assert metrics.task_id == "metrics-task"
        assert metrics.task_name == "classify_image"
        assert metrics.worker_type == WorkerType.CPU
        assert metrics.queue_time == 1.5
        assert metrics.execution_time == 3.2
        assert metrics.total_time == 4.7
        assert metrics.success is True
        assert metrics.timeout is False

    def test_task_metrics_with_timeout(self):
        """TaskMetrics should track timeout status."""
        metrics = TaskMetrics(
            task_id="timeout-task",
            task_name="gpu_inference",
            worker_type=WorkerType.GPU,
            queue_time=120.0,
            execution_time=0.0,
            total_time=120.0,
            success=False,
            timeout=True,
        )

        assert metrics.success is False
        assert metrics.timeout is True

    def test_task_metrics_validation(self):
        """TaskMetrics should validate required fields."""
        with pytest.raises(ValidationError):
            TaskMetrics(
                task_id="test",
                # Missing required fields
            )