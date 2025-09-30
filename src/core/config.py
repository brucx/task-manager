"""Configuration management."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Celery configuration
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    # Task timeout configuration
    task_default_timeout: int = 300  # 5 minutes
    task_queue_timeout: int = 30  # 30 seconds - drop if queued longer

    # Worker configuration
    io_worker_concurrency: int = 20
    cpu_worker_concurrency: int = 10
    gpu_worker_concurrency: int = 2  # 2 tasks per GPU

    # Queue names
    queue_main: str = "main"
    queue_io: str = "io"
    queue_cpu: str = "cpu"
    queue_gpu_general: str = "gpu-general"
    queue_gpu_portrait: str = "gpu-portrait"
    queue_gpu_landscape: str = "gpu-landscape"

    # Shared storage
    shared_tmp_path: str = "/tmp/shared/tasks"

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Admin notification
    admin_webhook_url: Optional[str] = None
    admin_email: Optional[str] = None

    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def broker_url(self) -> str:
        """Get Celery broker URL."""
        if self.celery_broker_url:
            return self.celery_broker_url

        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def result_backend_url(self) -> str:
        """Get Celery result backend URL."""
        if self.celery_result_backend:
            return self.celery_result_backend

        return self.broker_url


settings = Settings()