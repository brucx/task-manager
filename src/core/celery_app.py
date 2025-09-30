"""Celery application configuration."""
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from .config import settings
from src.monitoring.metrics import task_metrics

# Create Celery app
celery_app = Celery(
    "task_manager",
    broker=settings.broker_url,
    backend=settings.result_backend_url,
    include=[
        "src.workers.io_worker",
        "src.workers.cpu_worker",
        "src.workers.gpu_worker",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.task_default_timeout,
    task_soft_time_limit=settings.task_default_timeout - 10,
    worker_prefetch_multiplier=1,  # Important for fair task distribution
    worker_max_tasks_per_child=1000,  # Restart workers periodically
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Requeue tasks if worker dies
    task_default_priority=5,
    broker_connection_retry_on_startup=True,
)

# Define task routes
celery_app.conf.task_routes = {
    "src.workers.io_worker.*": {"queue": settings.queue_io},
    "src.workers.cpu_worker.*": {"queue": settings.queue_cpu},
    "src.workers.gpu_worker.gpu_inference_general": {"queue": settings.queue_gpu_general},
    "src.workers.gpu_worker.gpu_inference_portrait": {"queue": settings.queue_gpu_portrait},
    "src.workers.gpu_worker.gpu_inference_landscape": {"queue": settings.queue_gpu_landscape},
}


# Task monitoring hooks
@task_prerun.connect
def task_prerun_handler(task_id=None, task=None, **kwargs):
    """Record task start time."""
    if settings.enable_metrics:
        task_metrics.task_started(task_id, task.name)


@task_postrun.connect
def task_postrun_handler(task_id=None, task=None, retval=None, **kwargs):
    """Record task completion."""
    if settings.enable_metrics:
        task_metrics.task_completed(task_id, task.name, success=True)


@task_failure.connect
def task_failure_handler(task_id=None, exception=None, **kwargs):
    """Record task failure."""
    if settings.enable_metrics:
        task_metrics.task_completed(task_id, "unknown", success=False)