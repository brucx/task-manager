"""
Example: Image Super-Resolution Service

This example demonstrates how to use the task manager framework to implement
a complete image super-resolution pipeline with GPU inference.

Pipeline stages:
1. Download image from URL
2. Classify image type (general, portrait, landscape)
3. Run GPU inference with appropriate model
4. Encode and optimize result
5. Upload to object storage
"""
import asyncio
import logging
from src.core import celery_app, TaskManager
from src.models import SubTaskConfig, WorkerType
from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@celery_app.task(name="image_super_resolution_pipeline", bind=True)
def image_super_resolution_pipeline(
    self, image_url: str, upload_url: str
) -> dict:
    """
    Complete image super-resolution pipeline.

    This is the main task that orchestrates all subtasks.

    Args:
        image_url: URL of input image to download
        upload_url: URL to upload result (presigned S3 URL, etc.)

    Returns:
        Result dictionary with output URL
    """
    task_id = self.request.id
    logger.info(f"Starting super-resolution pipeline for task {task_id}")

    # Stage 1: Download image
    download_task = SubTaskConfig(
        name="download_image",
        worker_type=WorkerType.IO,
        queue=settings.queue_io,
        args=[task_id, image_url],
    )

    from src.workers.io_worker import download_image
    input_path = download_image.apply_async(
        args=[task_id, image_url],
        queue=settings.queue_io,
    ).get()

    logger.info(f"Downloaded image to {input_path}")

    # Stage 2: Classify image
    from src.workers.cpu_worker import classify_image
    classification = classify_image.apply_async(
        args=[task_id, input_path],
        queue=settings.queue_cpu,
    ).get()

    logger.info(f"Image classified as: {classification}")

    # Stage 3: Run GPU inference based on classification
    category = classification["category"]
    gpu_queue_map = {
        "general": settings.queue_gpu_general,
        "portrait": settings.queue_gpu_portrait,
        "landscape": settings.queue_gpu_landscape,
    }
    gpu_task_map = {
        "general": "gpu_inference_general",
        "portrait": "gpu_inference_portrait",
        "landscape": "gpu_inference_landscape",
    }

    gpu_queue = gpu_queue_map.get(category, settings.queue_gpu_general)
    gpu_task_name = gpu_task_map.get(category, "gpu_inference_general")

    from src.workers import gpu_worker
    gpu_task = getattr(gpu_worker, gpu_task_name)
    output_path = gpu_task.apply_async(
        args=[task_id, input_path],
        queue=gpu_queue,
    ).get()

    logger.info(f"GPU inference complete: {output_path}")

    # Stage 4: Encode result
    from src.workers.cpu_worker import encode_result
    encoded_path = encode_result.apply_async(
        args=[task_id, output_path],
        queue=settings.queue_cpu,
    ).get()

    logger.info(f"Result encoded: {encoded_path}")

    # Stage 5: Upload result
    from src.workers.io_worker import upload_result
    final_url = upload_result.apply_async(
        args=[task_id, "result.jpg", upload_url],
        queue=settings.queue_io,
    ).get()

    logger.info(f"Result uploaded to: {final_url}")

    # Cleanup task directory
    TaskManager.cleanup_task(task_id)

    return {
        "task_id": task_id,
        "input_url": image_url,
        "output_url": final_url,
        "classification": classification,
    }


async def submit_super_resolution_task(
    image_url: str, upload_url: str, sync: bool = False
) -> dict:
    """
    Submit image super-resolution task via API.

    Args:
        image_url: URL of input image
        upload_url: URL to upload result
        sync: If True, wait for completion

    Returns:
        Task result
    """
    import httpx

    async with httpx.AsyncClient() as client:
        # Submit task
        response = await client.post(
            "http://localhost:8000/api/v1/tasks",
            json={
                "task_name": "image_super_resolution_pipeline",
                "args": [image_url, upload_url],
                "sync": sync,
            },
        )
        response.raise_for_status()
        result = response.json()

        task_id = result["task_id"]
        logger.info(f"Submitted task: {task_id}")

        if not sync:
            # Poll for completion
            while True:
                status_response = await client.get(
                    f"http://localhost:8000/api/v1/tasks/{task_id}"
                )
                status = status_response.json()

                logger.info(f"Task {task_id} state: {status['state']}")

                if status["state"] in ["SUCCESS", "FAILURE", "TIMEOUT"]:
                    return status

                await asyncio.sleep(1)

        return result


# Example usage
async def main():
    """Example usage of the super-resolution service."""
    # Example image URL
    image_url = "https://example.com/input-image.jpg"
    upload_url = "https://s3.amazonaws.com/bucket/result.jpg"  # Presigned URL

    logger.info("Submitting super-resolution task...")

    # Submit task (async mode)
    result = await submit_super_resolution_task(
        image_url=image_url,
        upload_url=upload_url,
        sync=False,
    )

    logger.info(f"Task completed: {result}")


if __name__ == "__main__":
    asyncio.run(main())