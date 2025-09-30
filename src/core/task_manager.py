"""Task manager for coordinating parent-child tasks."""
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from celery import group, chain
from celery.result import AsyncResult, GroupResult
from .celery_app import celery_app
from .config import settings
from src.models import TaskState, TaskStatus, SubTaskConfig
from src.utils.storage import get_task_dir, cleanup_task_dir
from src.monitoring.notification import notify_admin_timeout

logger = logging.getLogger(__name__)


class TaskManager:
    """Manages parent-child task relationships and coordination."""

    @staticmethod
    def submit_task(
        task_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: int = 5,
    ) -> str:
        """
        Submit a main task.

        Args:
            task_name: Name of the task to execute
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Task priority (0-10)

        Returns:
            Task ID
        """
        args = args or []
        kwargs = kwargs or {}

        # Get task function
        task_func = celery_app.tasks.get(task_name)
        if not task_func:
            raise ValueError(f"Task {task_name} not found")

        # Submit task
        result = task_func.apply_async(
            args=args,
            kwargs=kwargs,
            priority=priority,
        )

        logger.info(f"Submitted task {task_name} with ID {result.id}")
        return result.id

    @staticmethod
    def submit_subtasks(
        parent_task_id: str,
        subtask_configs: List[SubTaskConfig],
        parallel: bool = True,
    ) -> List[str]:
        """
        Submit subtasks for a parent task.

        Args:
            parent_task_id: ID of the parent task
            subtask_configs: List of subtask configurations
            parallel: If True, run subtasks in parallel; otherwise sequential

        Returns:
            List of subtask IDs
        """
        tasks = []

        for config in subtask_configs:
            task_func = celery_app.tasks.get(config.name)
            if not task_func:
                raise ValueError(f"Task {config.name} not found")

            signature = task_func.signature(
                args=config.args,
                kwargs=config.kwargs,
                priority=config.priority,
                queue=config.queue,
                time_limit=config.timeout,
            )
            tasks.append(signature)

        # Execute tasks
        if parallel:
            job = group(tasks)
            result = job.apply_async()
            subtask_ids = [r.id for r in result.results]
        else:
            job = chain(tasks)
            result = job.apply_async()
            subtask_ids = [result.id]

        logger.info(
            f"Submitted {len(subtask_configs)} subtasks for parent {parent_task_id}: {subtask_ids}"
        )
        return subtask_ids

    @staticmethod
    def get_task_status(task_id: str) -> TaskStatus:
        """
        Get status of a task.

        Args:
            task_id: Task ID

        Returns:
            TaskStatus object
        """
        result = AsyncResult(task_id, app=celery_app)

        status = TaskStatus(
            task_id=task_id,
            state=TaskState(result.state),
            result=result.result if result.successful() else None,
            error=str(result.info) if result.failed() else None,
        )

        # Check for timeout
        if result.state == "PENDING":
            # Check if task has been waiting too long
            task_info = result.info
            if isinstance(task_info, dict) and "submitted_at" in task_info:
                submitted_at = datetime.fromisoformat(task_info["submitted_at"])
                wait_time = (datetime.utcnow() - submitted_at).total_seconds()

                if wait_time > settings.task_queue_timeout:
                    status.state = TaskState.TIMEOUT
                    status.error = f"Task timeout after {wait_time:.1f}s in queue"

                    # Revoke the task
                    result.revoke(terminate=True)

                    # Notify admin
                    notify_admin_timeout(task_id, wait_time)
                    logger.warning(f"Task {task_id} timeout after {wait_time:.1f}s")

        return status

    @staticmethod
    def wait_for_task(
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 0.5,
    ) -> TaskStatus:
        """
        Wait for a task to complete (for sync API).

        Args:
            task_id: Task ID
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks

        Returns:
            Final TaskStatus
        """
        import time

        start_time = time.time()

        while True:
            status = TaskManager.get_task_status(task_id)

            # Check if task is done
            if status.state in [
                TaskState.SUCCESS,
                TaskState.FAILURE,
                TaskState.TIMEOUT,
                TaskState.REVOKED,
            ]:
                return status

            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                status.state = TaskState.TIMEOUT
                status.error = "Client timeout"
                return status

            time.sleep(poll_interval)

    @staticmethod
    def cleanup_task(task_id: str):
        """
        Cleanup task resources (files, etc.).

        Args:
            task_id: Task ID
        """
        try:
            task_dir = get_task_dir(task_id)
            cleanup_task_dir(task_dir)
            logger.info(f"Cleaned up resources for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to cleanup task {task_id}: {e}")