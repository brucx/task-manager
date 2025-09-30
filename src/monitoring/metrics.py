"""Prometheus metrics for task monitoring."""
import logging
import time
from typing import Dict
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from src.core.config import settings

logger = logging.getLogger(__name__)


class TaskMetrics:
    """Metrics collector for task execution."""

    def __init__(self):
        """Initialize metrics."""
        # Task counters
        self.tasks_submitted = Counter(
            "tasks_submitted_total",
            "Total number of tasks submitted",
            ["task_name"],
        )

        self.tasks_completed = Counter(
            "tasks_completed_total",
            "Total number of tasks completed",
            ["task_name", "status"],
        )

        # Task timing
        self.task_duration = Histogram(
            "task_duration_seconds",
            "Task execution duration in seconds",
            ["task_name", "worker_type"],
        )

        self.task_queue_time = Histogram(
            "task_queue_time_seconds",
            "Time spent in queue before execution",
            ["queue_name"],
        )

        # Worker metrics
        self.active_workers = Gauge(
            "active_workers",
            "Number of active workers",
            ["worker_type"],
        )

        self.queue_depth = Gauge(
            "queue_depth",
            "Number of tasks in queue",
            ["queue_name"],
        )

        # GPU metrics
        self.gpu_utilization = Gauge(
            "gpu_utilization_percent",
            "GPU utilization percentage",
            ["gpu_id"],
        )

        # Timeout tracking
        self.tasks_timeout = Counter(
            "tasks_timeout_total",
            "Total number of tasks that timed out",
            ["task_name"],
        )

        # Internal tracking
        self._task_start_times: Dict[str, float] = {}

    def task_submitted(self, task_name: str):
        """Record task submission."""
        self.tasks_submitted.labels(task_name=task_name).inc()

    def task_started(self, task_id: str, task_name: str):
        """Record task start."""
        self._task_start_times[task_id] = time.time()

    def task_completed(self, task_id: str, task_name: str, success: bool):
        """Record task completion."""
        status = "success" if success else "failure"
        self.tasks_completed.labels(task_name=task_name, status=status).inc()

        # Record duration
        if task_id in self._task_start_times:
            duration = time.time() - self._task_start_times[task_id]
            # Extract worker type from task name
            worker_type = self._extract_worker_type(task_name)
            self.task_duration.labels(
                task_name=task_name,
                worker_type=worker_type,
            ).observe(duration)

            del self._task_start_times[task_id]

    def task_timeout(self, task_name: str):
        """Record task timeout."""
        self.tasks_timeout.labels(task_name=task_name).inc()

    def update_queue_depth(self, queue_name: str, depth: int):
        """Update queue depth metric."""
        self.queue_depth.labels(queue_name=queue_name).set(depth)

    def update_gpu_utilization(self, gpu_id: str, utilization: float):
        """Update GPU utilization metric."""
        self.gpu_utilization.labels(gpu_id=gpu_id).set(utilization)

    @staticmethod
    def _extract_worker_type(task_name: str) -> str:
        """Extract worker type from task name."""
        if "gpu" in task_name.lower():
            return "gpu"
        elif "download" in task_name or "upload" in task_name:
            return "io"
        elif "classify" in task_name or "encode" in task_name:
            return "cpu"
        else:
            return "unknown"

    def export_metrics(self) -> bytes:
        """Export metrics in Prometheus format."""
        return generate_latest(REGISTRY)


# Global metrics instance
task_metrics = TaskMetrics()