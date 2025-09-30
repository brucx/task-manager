"""Unit tests for storage utilities."""
import pytest
from pathlib import Path

from src.utils.storage import (
    get_task_dir,
    get_task_file_path,
    save_task_data,
    cleanup_task_dir,
)


@pytest.mark.unit
class TestGetTaskDir:
    """Test get_task_dir function."""

    def test_creates_directory_if_not_exists(self, temp_storage, task_id):
        """get_task_dir should create directory if not exists."""
        task_dir = get_task_dir(task_id)

        assert task_dir.exists()
        assert task_dir.is_dir()
        assert task_dir.name == task_id

    def test_returns_existing_directory(self, temp_storage, task_id):
        """get_task_dir should return existing directory."""
        # Create directory first
        first_call = get_task_dir(task_id)

        # Call again
        second_call = get_task_dir(task_id)

        assert first_call == second_call
        assert second_call.exists()

    def test_multiple_tasks_separate_directories(self, temp_storage):
        """Each task should have separate directory."""
        task1_dir = get_task_dir("task-1")
        task2_dir = get_task_dir("task-2")

        assert task1_dir != task2_dir
        assert task1_dir.exists()
        assert task2_dir.exists()


@pytest.mark.unit
class TestGetTaskFilePath:
    """Test get_task_file_path function."""

    def test_returns_correct_path(self, temp_storage, task_id):
        """get_task_file_path should return correct file path."""
        filename = "test.jpg"
        file_path = get_task_file_path(task_id, filename)

        assert file_path.parent.name == task_id
        assert file_path.name == filename
        assert isinstance(file_path, Path)

    def test_creates_parent_directory(self, temp_storage, task_id):
        """get_task_file_path should return correct nested path."""
        filename = "nested/file.txt"
        file_path = get_task_file_path(task_id, filename)

        # Path should be correct, but directory not created until save
        assert "nested" in str(file_path)
        assert file_path.name == "file.txt"

    def test_multiple_files_same_task(self, temp_storage, task_id):
        """Multiple files in same task should share parent directory."""
        file1 = get_task_file_path(task_id, "file1.txt")
        file2 = get_task_file_path(task_id, "file2.txt")

        assert file1.parent == file2.parent


@pytest.mark.unit
class TestSaveTaskData:
    """Test save_task_data function."""

    def test_saves_data_correctly(self, temp_storage, task_id):
        """save_task_data should save data to correct location."""
        filename = "test.json"
        data = b'{"key": "value"}'

        save_task_data(task_id, filename, data)

        file_path = get_task_file_path(task_id, filename)
        assert file_path.exists()
        assert file_path.read_bytes() == data

    def test_overwrites_existing_file(self, temp_storage, task_id):
        """save_task_data should overwrite existing file."""
        filename = "test.txt"

        # Write first data
        save_task_data(task_id, filename, b"original")

        # Overwrite
        save_task_data(task_id, filename, b"updated")

        file_path = get_task_file_path(task_id, filename)
        assert file_path.read_bytes() == b"updated"

    def test_saves_binary_data(self, temp_storage, task_id):
        """save_task_data should handle binary data correctly."""
        filename = "image.jpg"
        binary_data = bytes(range(256))

        save_task_data(task_id, filename, binary_data)

        file_path = get_task_file_path(task_id, filename)
        assert file_path.read_bytes() == binary_data

    def test_saves_empty_data(self, temp_storage, task_id):
        """save_task_data should handle empty data."""
        filename = "empty.txt"
        save_task_data(task_id, filename, b"")

        file_path = get_task_file_path(task_id, filename)
        assert file_path.exists()
        assert file_path.read_bytes() == b""

    def test_creates_nested_directories(self, temp_storage, task_id):
        """save_task_data should create nested directories."""
        filename = "subdir1/subdir2/file.txt"
        data = b"nested data"

        save_task_data(task_id, filename, data)

        file_path = get_task_file_path(task_id, filename)
        assert file_path.exists()
        assert file_path.read_bytes() == data


@pytest.mark.unit
class TestCleanupTaskDir:
    """Test cleanup_task_dir function."""

    def test_removes_directory_and_contents(self, temp_storage, task_id):
        """cleanup_task_dir should remove directory and all contents."""
        # Create files
        save_task_data(task_id, "file1.txt", b"data1")
        save_task_data(task_id, "file2.txt", b"data2")
        save_task_data(task_id, "subdir/file3.txt", b"data3")

        task_dir = get_task_dir(task_id)
        assert task_dir.exists()

        # Cleanup
        cleanup_task_dir(task_dir)

        assert not task_dir.exists()

    def test_handles_empty_directory(self, temp_storage, task_id):
        """cleanup_task_dir should handle empty directory."""
        task_dir = get_task_dir(task_id)

        cleanup_task_dir(task_dir)

        assert not task_dir.exists()

    def test_handles_nonexistent_directory(self, temp_storage):
        """cleanup_task_dir should handle nonexistent directory gracefully."""
        nonexistent_dir = temp_storage / "nonexistent-task"

        # Should not raise error
        cleanup_task_dir(nonexistent_dir)

        assert not nonexistent_dir.exists()

    def test_removes_nested_structure(self, temp_storage, task_id):
        """cleanup_task_dir should remove deeply nested structures."""
        # Create nested structure
        save_task_data(task_id, "a/b/c/d/file.txt", b"deep")

        task_dir = get_task_dir(task_id)
        cleanup_task_dir(task_dir)

        assert not task_dir.exists()


@pytest.mark.unit
class TestStorageIntegration:
    """Test storage functions working together."""

    def test_full_lifecycle(self, temp_storage, task_id):
        """Test complete storage lifecycle: create → save → retrieve → cleanup."""
        # 1. Create directory
        task_dir = get_task_dir(task_id)
        assert task_dir.exists()

        # 2. Save multiple files
        save_task_data(task_id, "input.jpg", b"image_data")
        save_task_data(task_id, "classification.json", b'{"category":"general"}')
        save_task_data(task_id, "output.jpg", b"result_data")

        # 3. Retrieve and verify
        input_path = get_task_file_path(task_id, "input.jpg")
        classification_path = get_task_file_path(task_id, "classification.json")
        output_path = get_task_file_path(task_id, "output.jpg")

        assert input_path.read_bytes() == b"image_data"
        assert classification_path.read_bytes() == b'{"category":"general"}'
        assert output_path.read_bytes() == b"result_data"

        # 4. Cleanup
        cleanup_task_dir(task_dir)
        assert not task_dir.exists()

    def test_concurrent_task_isolation(self, temp_storage):
        """Multiple tasks should not interfere with each other."""
        task1_id = "task-1"
        task2_id = "task-2"

        # Save data for both tasks
        save_task_data(task1_id, "data.txt", b"task1_data")
        save_task_data(task2_id, "data.txt", b"task2_data")

        # Verify isolation
        task1_file = get_task_file_path(task1_id, "data.txt")
        task2_file = get_task_file_path(task2_id, "data.txt")

        assert task1_file.read_bytes() == b"task1_data"
        assert task2_file.read_bytes() == b"task2_data"

        # Cleanup one task shouldn't affect the other
        task1_dir = get_task_dir(task1_id)
        task2_dir = get_task_dir(task2_id)

        cleanup_task_dir(task1_dir)

        assert not task1_dir.exists()
        assert task2_dir.exists()
        assert task2_file.read_bytes() == b"task2_data"