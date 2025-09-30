"""IO-bound workers for download and upload operations."""
import logging
import httpx
from pathlib import Path
from src.core.celery_app import celery_app
from src.core.config import settings
from src.utils.storage import get_task_file_path, save_task_data

logger = logging.getLogger(__name__)


@celery_app.task(
    name="download_image",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def download_image(self, task_id: str, image_url: str) -> str:
    """
    Download image from URL and save to shared storage.

    Args:
        task_id: Task ID
        image_url: URL of image to download

    Returns:
        Path to downloaded image
    """
    try:
        logger.info(f"Downloading image from {image_url} for task {task_id}")

        # Download image
        with httpx.Client(timeout=30.0) as client:
            response = client.get(image_url)
            response.raise_for_status()
            image_data = response.content

        # Save to shared storage
        save_task_data(task_id, "input.jpg", image_data)
        file_path = str(get_task_file_path(task_id, "input.jpg"))

        logger.info(f"Downloaded image to {file_path}")
        return file_path

    except Exception as exc:
        logger.error(f"Failed to download image: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="upload_result",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def upload_result(
    self, task_id: str, result_filename: str, upload_url: str
) -> str:
    """
    Upload result file to object storage.

    Args:
        task_id: Task ID
        result_filename: Name of result file in task directory
        upload_url: URL to upload to (presigned S3 URL, etc.)

    Returns:
        Upload confirmation or final URL
    """
    try:
        logger.info(f"Uploading {result_filename} for task {task_id}")

        # Load result file
        file_path = get_task_file_path(task_id, result_filename)
        if not file_path.exists():
            raise FileNotFoundError(f"Result file not found: {file_path}")

        result_data = file_path.read_bytes()

        # Upload to object storage
        with httpx.Client(timeout=60.0) as client:
            response = client.put(
                upload_url,
                content=result_data,
                headers={"Content-Type": "image/jpeg"},
            )
            response.raise_for_status()

        logger.info(f"Uploaded result to {upload_url}")
        return upload_url

    except Exception as exc:
        logger.error(f"Failed to upload result: {exc}")
        raise self.retry(exc=exc)