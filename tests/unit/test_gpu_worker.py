"""Unit tests for GPU worker tasks."""
import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import Mock, patch, MagicMock

from src.workers.gpu_worker import (
    ModelRegistry,
    run_inference,
    gpu_inference_general,
    gpu_inference_portrait,
    gpu_inference_landscape,
)


@pytest.mark.unit
class TestModelRegistry:
    """Test ModelRegistry singleton pattern."""

    def setup_method(self):
        """Clear registry before each test."""
        ModelRegistry._models.clear()

    def test_load_model_once(self):
        """Model should be loaded only once."""
        model1 = ModelRegistry.load_model("test_model", "/path/to/model.pth")
        model2 = ModelRegistry.load_model("test_model", "/path/to/model.pth")

        assert model1 is model2
        assert len(ModelRegistry._models) == 1

    def test_load_multiple_models(self):
        """Multiple different models should be loaded separately."""
        model1 = ModelRegistry.load_model("model1", "/path/to/model1.pth")
        model2 = ModelRegistry.load_model("model2", "/path/to/model2.pth")
        model3 = ModelRegistry.load_model("model3", "/path/to/model3.pth")

        assert len(ModelRegistry._models) == 3
        assert model1 is not model2
        assert model2 is not model3

    def test_get_model_existing(self):
        """get_model should return loaded model."""
        loaded = ModelRegistry.load_model("test_model", "/path/to/model.pth")
        retrieved = ModelRegistry.get_model("test_model")

        assert retrieved is loaded
        assert retrieved is not None

    def test_get_model_nonexistent(self):
        """get_model should return None for nonexistent model."""
        result = ModelRegistry.get_model("nonexistent_model")
        assert result is None

    def test_model_metadata_stored(self):
        """Model registry should store metadata."""
        model = ModelRegistry.load_model("test_model", "/path/to/model.pth")

        assert model["name"] == "test_model"
        assert model["path"] == "/path/to/model.pth"
        assert model["loaded"] is True

    def test_load_model_idempotent(self):
        """Loading same model multiple times should be idempotent."""
        model1 = ModelRegistry.load_model("model", "/path")
        model2 = ModelRegistry.load_model("model", "/path")
        model3 = ModelRegistry.load_model("model", "/path")

        assert model1 is model2 is model3
        assert len(ModelRegistry._models) == 1


@pytest.mark.unit
class TestRunInference:
    """Test GPU inference execution."""

    def setup_method(self):
        """Clear registry and set up test models."""
        ModelRegistry._models.clear()
        ModelRegistry.load_model("general", "/models/general_model.pth")
        ModelRegistry.load_model("portrait", "/models/portrait_model.pth")
        ModelRegistry.load_model("landscape", "/models/landscape_model.pth")

    def test_inference_creates_output(self, tmp_path):
        """Inference should create output file."""
        # Create input image
        input_img = Image.new("RGB", (100, 100), color="blue")
        input_path = tmp_path / "input.jpg"
        input_img.save(input_path)

        output_path = tmp_path / "output.jpg"

        # Run inference
        run_inference("general", str(input_path), str(output_path))

        # Verify output exists
        assert output_path.exists()

    def test_inference_resizes_2x(self, tmp_path):
        """Placeholder inference should resize image 2x."""
        # Create input image
        input_img = Image.new("RGB", (100, 100))
        input_path = tmp_path / "input.jpg"
        input_img.save(input_path)

        output_path = tmp_path / "output.jpg"

        run_inference("general", str(input_path), str(output_path))

        # Verify output is 2x size
        output_img = Image.open(output_path)
        assert output_img.size == (200, 200)

    def test_inference_preserves_aspect_ratio(self, tmp_path):
        """Inference should preserve aspect ratio."""
        # Create non-square image
        input_img = Image.new("RGB", (200, 100))
        input_path = tmp_path / "input.jpg"
        input_img.save(input_path)

        output_path = tmp_path / "output.jpg"

        run_inference("general", str(input_path), str(output_path))

        # Verify aspect ratio preserved
        output_img = Image.open(output_path)
        assert output_img.size == (400, 200)

    def test_inference_with_different_models(self, tmp_path):
        """Inference should work with different model names."""
        input_img = Image.new("RGB", (100, 100))
        input_path = tmp_path / "input.jpg"
        input_img.save(input_path)

        models = ["general", "portrait", "landscape"]

        for model_name in models:
            output_path = tmp_path / f"output_{model_name}.jpg"
            run_inference(model_name, str(input_path), str(output_path))
            assert output_path.exists()

    def test_inference_invalid_model_raises_error(self, tmp_path):
        """Inference with invalid model should raise error."""
        input_img = Image.new("RGB", (100, 100))
        input_path = tmp_path / "input.jpg"
        input_img.save(input_path)

        output_path = tmp_path / "output.jpg"

        with pytest.raises(ValueError, match="not loaded"):
            run_inference("nonexistent_model", str(input_path), str(output_path))

    def test_inference_invalid_input_raises_error(self, tmp_path):
        """Inference with invalid input should raise error."""
        output_path = tmp_path / "output.jpg"

        with pytest.raises(Exception):
            run_inference("general", "/nonexistent/input.jpg", str(output_path))

    def test_inference_output_is_jpeg(self, tmp_path):
        """Inference output should be JPEG format."""
        input_img = Image.new("RGB", (100, 100))
        input_path = tmp_path / "input.jpg"
        input_img.save(input_path)

        output_path = tmp_path / "output.jpg"

        run_inference("general", str(input_path), str(output_path))

        output_img = Image.open(output_path)
        assert output_img.format == "JPEG"


@pytest.mark.unit
class TestGPUInferenceGeneral:
    """Test gpu_inference_general task."""

    def setup_method(self):
        """Set up test models."""
        ModelRegistry._models.clear()
        ModelRegistry.load_model("general", "/models/general_model.pth")

    def test_inference_general_returns_output_path(self, temp_storage, sample_image, task_id):
        """gpu_inference_general should return output path."""
        output_path = gpu_inference_general(task_id, str(sample_image))

        assert output_path is not None
        assert isinstance(output_path, str)
        assert Path(output_path).exists()

    def test_inference_general_creates_output_in_task_dir(
        self, temp_storage, sample_image, task_id
    ):
        """Output should be created in task directory."""
        from src.utils.storage import get_task_dir

        output_path = gpu_inference_general(task_id, str(sample_image))

        task_dir = get_task_dir(task_id)
        output_file = Path(output_path)

        assert output_file.parent == task_dir

    def test_inference_general_output_filename(self, temp_storage, sample_image, task_id):
        """Output should be named output.jpg."""
        output_path = gpu_inference_general(task_id, str(sample_image))

        assert Path(output_path).name == "output.jpg"


@pytest.mark.unit
class TestGPUInferencePortrait:
    """Test gpu_inference_portrait task."""

    def setup_method(self):
        """Set up test models."""
        ModelRegistry._models.clear()
        ModelRegistry.load_model("portrait", "/models/portrait_model.pth")

    def test_inference_portrait_returns_output_path(
        self, temp_storage, portrait_image, task_id
    ):
        """gpu_inference_portrait should return output path."""
        output_path = gpu_inference_portrait(task_id, str(portrait_image))

        assert output_path is not None
        assert Path(output_path).exists()

    def test_inference_portrait_uses_portrait_model(
        self, temp_storage, portrait_image, task_id
    ):
        """Portrait inference should use portrait model."""
        # This is implicitly tested by not raising "model not loaded" error
        output_path = gpu_inference_portrait(task_id, str(portrait_image))
        assert Path(output_path).exists()


@pytest.mark.unit
class TestGPUInferenceLandscape:
    """Test gpu_inference_landscape task."""

    def setup_method(self):
        """Set up test models."""
        ModelRegistry._models.clear()
        ModelRegistry.load_model("landscape", "/models/landscape_model.pth")

    def test_inference_landscape_returns_output_path(
        self, temp_storage, landscape_image, task_id
    ):
        """gpu_inference_landscape should return output path."""
        output_path = gpu_inference_landscape(task_id, str(landscape_image))

        assert output_path is not None
        assert Path(output_path).exists()

    def test_inference_landscape_uses_landscape_model(
        self, temp_storage, landscape_image, task_id
    ):
        """Landscape inference should use landscape model."""
        output_path = gpu_inference_landscape(task_id, str(landscape_image))
        assert Path(output_path).exists()


@pytest.mark.unit
class TestGPUWorkerIntegration:
    """Test GPU worker functions integration."""

    def setup_method(self):
        """Set up all models."""
        ModelRegistry._models.clear()
        ModelRegistry.load_model("general", "/models/general_model.pth")
        ModelRegistry.load_model("portrait", "/models/portrait_model.pth")
        ModelRegistry.load_model("landscape", "/models/landscape_model.pth")

    def test_all_inference_tasks_work(self, temp_storage, sample_image, task_id):
        """All three inference tasks should work correctly."""
        # Test general
        output_general = gpu_inference_general(
            task_id + "-general", str(sample_image)
        )
        assert Path(output_general).exists()

        # Test portrait
        output_portrait = gpu_inference_portrait(
            task_id + "-portrait", str(sample_image)
        )
        assert Path(output_portrait).exists()

        # Test landscape
        output_landscape = gpu_inference_landscape(
            task_id + "-landscape", str(sample_image)
        )
        assert Path(output_landscape).exists()

    def test_models_persist_across_tasks(self, temp_storage, sample_image):
        """Models should stay loaded across multiple task executions."""
        initial_model_count = len(ModelRegistry._models)

        # Run multiple tasks
        for i in range(5):
            task_id = f"task-{i}"
            gpu_inference_general(task_id, str(sample_image))

        # Model count should remain the same
        assert len(ModelRegistry._models) == initial_model_count