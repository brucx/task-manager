"""CPU-bound workers for classification and encoding."""
import logging
import json
from enum import Enum
from PIL import Image
from src.core.celery_app import celery_app
from src.utils.storage import get_task_file_path, save_task_data

logger = logging.getLogger(__name__)


class ImageCategory(str, Enum):
    """Image category classification."""
    GENERAL = "general"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


@celery_app.task(name="classify_image", bind=True)
def classify_image(self, task_id: str, image_path: str) -> dict:
    """
    Classify image to determine which model to use.

    Args:
        task_id: Task ID
        image_path: Path to image file

    Returns:
        Classification result with category
    """
    try:
        logger.info(f"Classifying image for task {task_id}")

        # Load image
        image = Image.open(image_path)
        width, height = image.size
        aspect_ratio = width / height

        # Simple classification logic (placeholder - replace with actual model)
        # In production, use a lightweight classification model
        if 0.7 <= aspect_ratio <= 1.3:
            # Nearly square - likely portrait
            category = ImageCategory.PORTRAIT
        elif aspect_ratio > 1.5:
            # Wide aspect ratio - likely landscape
            category = ImageCategory.LANDSCAPE
        else:
            # Default to general model
            category = ImageCategory.GENERAL

        result = {
            "category": category.value,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
        }

        # Save classification result
        result_json = json.dumps(result)
        save_task_data(task_id, "classification.json", result_json.encode())

        logger.info(f"Classified as {category.value}: {result}")
        return result

    except Exception as exc:
        logger.error(f"Failed to classify image: {exc}")
        raise


@celery_app.task(name="encode_result", bind=True)
def encode_result(self, task_id: str, output_path: str, quality: int = 95) -> str:
    """
    Encode and optimize result image.

    Args:
        task_id: Task ID
        output_path: Path to output image from GPU inference
        quality: JPEG quality (0-100)

    Returns:
        Path to encoded image
    """
    try:
        logger.info(f"Encoding result for task {task_id}")

        # Load and optimize image
        image = Image.open(output_path)

        # Save optimized version
        encoded_path = get_task_file_path(task_id, "result.jpg")
        image.save(
            encoded_path,
            "JPEG",
            quality=quality,
            optimize=True,
        )

        logger.info(f"Encoded result to {encoded_path}")
        return str(encoded_path)

    except Exception as exc:
        logger.error(f"Failed to encode result: {exc}")
        raise