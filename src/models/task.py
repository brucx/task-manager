"""Task models and state definitions."""
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class WorkerType(str, Enum):
    """Worker type enumeration."""
    IO = "io"
    CPU = "cpu"
    GPU = "gpu"


class TaskState(str, Enum):
    """Task state enumeration."""
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"
    REVOKED = "REVOKED"


class TaskPriority(int, Enum):
    """Task priority levels."""
    LOW = 0
    NORMAL = 5
    HIGH = 10


class SubTaskConfig(BaseModel):
    """Configuration for a subtask."""
    name: str
    worker_type: WorkerType
    queue: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: Optional[int] = None


class TaskRequest(BaseModel):
    """Task submission request."""
    task_name: str
    args: List[Any] = Field(default_factory=list)
    kwargs: Dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    sync: bool = False  # If True, use poll-based sync API


class TaskResponse(BaseModel):
    """Task submission response."""
    task_id: str
    state: TaskState
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class TaskStatus(BaseModel):
    """Task status for polling."""
    task_id: str
    state: TaskState
    progress: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    submitted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    subtasks: List[str] = Field(default_factory=list)


class TaskMetrics(BaseModel):
    """Task execution metrics."""
    task_id: str
    task_name: str
    worker_type: WorkerType
    queue_time: float  # seconds in queue
    execution_time: float  # seconds executing
    total_time: float  # total end-to-end time
    success: bool
    timeout: bool = False