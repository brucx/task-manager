"""GPU workers for model inference with model preloading."""
import logging
import os
from typing import Dict, Any, Optional
from PIL import Image
from src.core.celery_app import celery_app
from src.core.config import settings
from src.utils.storage import get_task_file_path

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Registry for preloaded models."""

    _models: Dict[str, Any] = {}

    @classmethod
    def load_model(cls, model_name: str, model_path: str) -> Any:
        """
        Load model into memory if not already loaded.

        Args:
            model_name: Name identifier for the model
            model_path: Path to model weights

        Returns:
            Loaded model object
        """
        if model_name not in cls._models:
            logger.info(f"Loading model {model_name} from {model_path}")

            # Placeholder for actual model loading
            # In production, replace with actual model loading code:
            # model = torch.load(model_path)
            # model = model.cuda()
            # model.eval()

            cls._models[model_name] = {
                "name": model_name,
                "path": model_path,
                "loaded": True,
                # "model": model,  # Actual model object
            }

            logger.info(f"Model {model_name} loaded successfully")

        return cls._models[model_name]

    @classmethod
    def get_model(cls, model_name: str) -> Optional[Any]:
        """Get preloaded model."""
        return cls._models.get(model_name)


# Preload models on worker startup
def preload_models():
    """Preload all models into GPU memory."""
    # Get GPU ID from environment
    gpu_id = os.environ.get("CUDA_VISIBLE_DEVICES", "0")
    logger.info(f"Preloading models on GPU {gpu_id}")

    # Load all three models (1GB each, fits in 24GB VRAM)
    ModelRegistry.load_model("general", "/models/general_model.pth")
    ModelRegistry.load_model("portrait", "/models/portrait_model.pth")
    ModelRegistry.load_model("landscape", "/models/landscape_model.pth")

    logger.info("All models preloaded successfully")


# Call preload on worker initialization
try:
    preload_models()
except Exception as e:
    logger.warning(f"Could not preload models (may be running without GPU): {e}")


def run_inference(model_name: str, input_image_path: str, output_image_path: str):
    """
    Run GPU inference with specified model.

    Args:
        model_name: Name of model to use
        input_image_path: Path to input image
        output_image_path: Path to save output

    This is a placeholder implementation. In production:
    1. Load image and preprocess
    2. Run model inference on GPU
    3. Post-process and save result
    """
    model = ModelRegistry.get_model(model_name)
    if not model:
        raise ValueError(f"Model {model_name} not loaded")

    logger.info(f"Running inference with {model_name}")

    # Placeholder implementation
    # In production, replace with:
    # image = preprocess(Image.open(input_image_path))
    # with torch.no_grad():
    #     output = model(image.cuda())
    # result = postprocess(output)
    # result.save(output_image_path)

    # For now, just copy and resize image as placeholder
    image = Image.open(input_image_path)
    # Simulate super-resolution: resize to 2x
    new_size = (image.width * 2, image.height * 2)
    result = image.resize(new_size, Image.LANCZOS)
    result.save(output_image_path, "JPEG", quality=95)

    logger.info(f"Inference complete, saved to {output_image_path}")


@celery_app.task(name="gpu_inference_general", bind=True)
def gpu_inference_general(self, task_id: str, input_path: str) -> str:
    """
    Run inference with general model.

    Args:
        task_id: Task ID
        input_path: Path to input image

    Returns:
        Path to output image
    """
    try:
        output_path = str(get_task_file_path(task_id, "output.jpg"))
        run_inference("general", input_path, output_path)
        return output_path
    except Exception as exc:
        logger.error(f"GPU inference failed: {exc}")
        raise


@celery_app.task(name="gpu_inference_portrait", bind=True)
def gpu_inference_portrait(self, task_id: str, input_path: str) -> str:
    """
    Run inference with portrait model.

    Args:
        task_id: Task ID
        input_path: Path to input image

    Returns:
        Path to output image
    """
    try:
        output_path = str(get_task_file_path(task_id, "output.jpg"))
        run_inference("portrait", input_path, output_path)
        return output_path
    except Exception as exc:
        logger.error(f"GPU inference failed: {exc}")
        raise


@celery_app.task(name="gpu_inference_landscape", bind=True)
def gpu_inference_landscape(self, task_id: str, input_path: str) -> str:
    """
    Run inference with landscape model.

    Args:
        task_id: Task ID
        input_path: Path to input image

    Returns:
        Path to output image
    """
    try:
        output_path = str(get_task_file_path(task_id, "output.jpg"))
        run_inference("landscape", input_path, output_path)
        return output_path
    except Exception as exc:
        logger.error(f"GPU inference failed: {exc}")
        raise