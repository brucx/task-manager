"""Shared storage utilities for task data."""
import os
import shutil
from pathlib import Path
from src.core.config import settings


def get_task_dir(task_id: str) -> Path:
    """
    Get task-specific directory path.

    Args:
        task_id: Task ID

    Returns:
        Path to task directory
    """
    task_dir = Path(settings.shared_tmp_path) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


def get_task_file_path(task_id: str, filename: str) -> Path:
    """
    Get path for a file within task directory.

    Args:
        task_id: Task ID
        filename: Name of the file

    Returns:
        Full path to file
    """
    return get_task_dir(task_id) / filename


def cleanup_task_dir(task_dir: Path):
    """
    Remove task directory and all contents.

    Args:
        task_dir: Path to task directory
    """
    if task_dir.exists():
        shutil.rmtree(task_dir)


def save_task_data(task_id: str, filename: str, data: bytes):
    """
    Save binary data to task directory.

    Args:
        task_id: Task ID
        filename: Name of file to save
        data: Binary data to write
    """
    file_path = get_task_file_path(task_id, filename)
    file_path.write_bytes(data)


def load_task_data(task_id: str, filename: str) -> bytes:
    """
    Load binary data from task directory.

    Args:
        task_id: Task ID
        filename: Name of file to load

    Returns:
        Binary file contents
    """
    file_path = get_task_file_path(task_id, filename)
    return file_path.read_bytes()