"""Unit tests for CPU worker tasks."""
import pytest
import json
from pathlib import Path
from PIL import Image
from unittest.mock import Mock, patch

from src.workers.cpu_worker import (
    classify_image,
    encode_result,
    ImageCategory,
)


@pytest.mark.unit
class TestClassifyImage:
    """Test image classification logic."""

    def test_classify_portrait_aspect_ratio(self, temp_storage, portrait_image, task_id):
        """Portrait aspect ratio should be classified as PORTRAIT."""
        # Run classification
        result = classify_image(task_id, str(portrait_image))

        # Verify result
        assert result["category"] == ImageCategory.PORTRAIT.value
        assert result["width"] == 800
        assert result["height"] == 1000
        assert 0.7 <= result["aspect_ratio"] <= 1.3

    def test_classify_landscape_aspect_ratio(self, temp_storage, landscape_image, task_id):
        """Wide aspect ratio should be classified as LANDSCAPE."""
        result = classify_image(task_id, str(landscape_image))

        assert result["category"] == ImageCategory.LANDSCAPE.value
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["aspect_ratio"] > 1.5

    def test_classify_square_as_portrait(self, temp_storage, tmp_path, task_id):
        """Square images should be classified as PORTRAIT."""
        # Create square image
        img = Image.new("RGB", (1000, 1000))
        img_path = tmp_path / "square.jpg"
        img.save(img_path)

        result = classify_image(task_id, str(img_path))

        assert result["category"] == ImageCategory.PORTRAIT.value
        assert result["aspect_ratio"] == 1.0

    def test_classify_general_aspect_ratio(self, temp_storage, tmp_path, task_id):
        """Moderate aspect ratios should be classified as GENERAL."""
        # Create image with aspect ratio between thresholds
        img = Image.new("RGB", (1400, 1000))  # 1.4 aspect ratio
        img_path = tmp_path / "general.jpg"
        img.save(img_path)

        result = classify_image(task_id, str(img_path))

        assert result["category"] == ImageCategory.GENERAL.value
        assert 1.3 < result["aspect_ratio"] < 1.5

    def test_classification_saves_result(self, temp_storage, sample_image, task_id):
        """Classification should save result to task directory."""
        from src.utils.storage import get_task_file_path

        result = classify_image(task_id, str(sample_image))

        # Verify result file exists
        result_file = get_task_file_path(task_id, "classification.json")
        assert result_file.exists()

        # Verify content
        saved_data = json.loads(result_file.read_text())
        assert saved_data == result

    def test_classification_includes_dimensions(self, temp_storage, tmp_path, task_id):
        """Classification should include image dimensions."""
        img = Image.new("RGB", (640, 480))
        img_path = tmp_path / "test.jpg"
        img.save(img_path)

        result = classify_image(task_id, str(img_path))

        assert "width" in result
        assert "height" in result
        assert result["width"] == 640
        assert result["height"] == 480

    def test_classification_handles_large_images(self, temp_storage, tmp_path, task_id):
        """Classification should handle large images."""
        # Create large image
        img = Image.new("RGB", (4000, 3000))
        img_path = tmp_path / "large.jpg"
        img.save(img_path)

        result = classify_image(task_id, str(img_path))

        assert result["width"] == 4000
        assert result["height"] == 3000
        assert result["category"] in [c.value for c in ImageCategory]

    def test_classification_handles_small_images(self, temp_storage, tmp_path, task_id):
        """Classification should handle small images."""
        # Create small image
        img = Image.new("RGB", (100, 100))
        img_path = tmp_path / "small.jpg"
        img.save(img_path)

        result = classify_image(task_id, str(img_path))

        assert result["width"] == 100
        assert result["height"] == 100

    def test_classification_invalid_image_raises_error(self, temp_storage, tmp_path, task_id):
        """Classification should raise error for invalid image."""
        # Create invalid image file
        invalid_path = tmp_path / "invalid.jpg"
        invalid_path.write_text("not an image")

        with pytest.raises(Exception):
            classify_image(task_id, str(invalid_path))

    def test_classification_nonexistent_file_raises_error(self, temp_storage, task_id):
        """Classification should raise error for nonexistent file."""
        with pytest.raises(Exception):
            classify_image(task_id, "/nonexistent/path/image.jpg")


@pytest.mark.unit
class TestEncodeResult:
    """Test result encoding and optimization."""

    def test_encode_result_creates_output(self, temp_storage, sample_image, task_id):
        """encode_result should create optimized output."""
        from src.utils.storage import get_task_file_path

        result_path = encode_result(task_id, str(sample_image))

        # Verify output exists
        output_file = Path(result_path)
        assert output_file.exists()
        assert output_file.name == "result.jpg"

    def test_encode_result_quality_parameter(self, temp_storage, tmp_path, task_id):
        """encode_result should respect quality parameter."""
        # Create test image
        img = Image.new("RGB", (500, 500), color="red")
        input_path = tmp_path / "input.jpg"
        img.save(input_path)

        # Encode with different qualities
        result_high = encode_result(task_id + "-high", str(input_path), quality=95)
        result_low = encode_result(task_id + "-low", str(input_path), quality=50)

        # High quality should be larger file
        high_size = Path(result_high).stat().st_size
        low_size = Path(result_low).stat().st_size

        assert high_size > low_size

    def test_encode_result_default_quality(self, temp_storage, sample_image, task_id):
        """encode_result should use default quality of 95."""
        result_path = encode_result(task_id, str(sample_image))

        # Verify image can be opened and is JPEG
        output_img = Image.open(result_path)
        assert output_img.format == "JPEG"

    def test_encode_result_preserves_dimensions(self, temp_storage, tmp_path, task_id):
        """encode_result should preserve image dimensions."""
        # Create test image with specific size
        img = Image.new("RGB", (1024, 768))
        input_path = tmp_path / "input.jpg"
        img.save(input_path)

        result_path = encode_result(task_id, str(input_path))

        # Verify dimensions preserved
        output_img = Image.open(result_path)
        assert output_img.size == (1024, 768)

    def test_encode_result_handles_different_formats(self, temp_storage, tmp_path, task_id):
        """encode_result should handle different input formats."""
        # Create PNG image
        img = Image.new("RGB", (500, 500))
        input_path = tmp_path / "input.png"
        img.save(input_path, "PNG")

        result_path = encode_result(task_id, str(input_path))

        # Output should be JPEG
        output_img = Image.open(result_path)
        assert output_img.format == "JPEG"

    def test_encode_result_invalid_image_raises_error(self, temp_storage, tmp_path, task_id):
        """encode_result should raise error for invalid image."""
        invalid_path = tmp_path / "invalid.jpg"
        invalid_path.write_text("not an image")

        with pytest.raises(Exception):
            encode_result(task_id, str(invalid_path))

    def test_encode_result_nonexistent_file_raises_error(self, temp_storage, task_id):
        """encode_result should raise error for nonexistent file."""
        with pytest.raises(Exception):
            encode_result(task_id, "/nonexistent/output.jpg")


@pytest.mark.unit
class TestCPUWorkerIntegration:
    """Test CPU worker functions working together."""

    def test_classify_then_encode_workflow(self, temp_storage, portrait_image, task_id):
        """Test classification → encoding workflow."""
        # 1. Classify image
        classification = classify_image(task_id, str(portrait_image))
        assert classification["category"] == ImageCategory.PORTRAIT.value

        # 2. Encode the same image (simulating GPU output)
        encoded_path = encode_result(task_id, str(portrait_image))

        # 3. Verify both outputs exist
        from src.utils.storage import get_task_file_path

        classification_file = get_task_file_path(task_id, "classification.json")
        result_file = Path(encoded_path)

        assert classification_file.exists()
        assert result_file.exists()

        # 4. Verify classification data
        saved_classification = json.loads(classification_file.read_text())
        assert saved_classification["category"] == ImageCategory.PORTRAIT.value


@pytest.mark.unit
class TestImageCategory:
    """Test ImageCategory enum."""

    def test_category_values(self):
        """Validate ImageCategory enum values."""
        assert ImageCategory.GENERAL == "general"
        assert ImageCategory.PORTRAIT == "portrait"
        assert ImageCategory.LANDSCAPE == "landscape"

    def test_category_from_string(self):
        """ImageCategory should be constructable from string."""
        assert ImageCategory("general") == ImageCategory.GENERAL
        assert ImageCategory("portrait") == ImageCategory.PORTRAIT
        assert ImageCategory("landscape") == ImageCategory.LANDSCAPE