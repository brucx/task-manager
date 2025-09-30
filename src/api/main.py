"""FastAPI application for task submission and monitoring."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from src.core import TaskManager, settings
from src.models import TaskRequest, TaskResponse, TaskStatus, TaskState
from src.monitoring.dashboard import dashboard_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Task Manager API")
    yield
    logger.info("Shutting down Task Manager API")


# Create FastAPI app
app = FastAPI(
    title="Task Manager API",
    description="Distributed GPU task processing framework",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount dashboard app
app.mount("/dashboard", dashboard_app)


@app.post("/api/v1/tasks", response_model=TaskResponse)
async def submit_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
):
    """
    Submit a new task for processing.

    Args:
        request: Task submission request
        background_tasks: FastAPI background tasks

    Returns:
        Task response with task ID
    """
    try:
        # Submit task
        task_id = TaskManager.submit_task(
            task_name=request.task_name,
            args=request.args,
            kwargs=request.kwargs,
            priority=request.priority,
        )

        # If sync mode, wait for completion
        if request.sync:
            status = TaskManager.wait_for_task(
                task_id=task_id,
                timeout=settings.task_default_timeout,
            )

            # Schedule cleanup
            background_tasks.add_task(TaskManager.cleanup_task, task_id)

            return TaskResponse(
                task_id=task_id,
                state=status.state,
            )

        # Async mode - return immediately
        return TaskResponse(
            task_id=task_id,
            state=TaskState.PENDING,
        )

    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """
    Get status of a task.

    Args:
        task_id: Task ID

    Returns:
        Task status
    """
    try:
        status = TaskManager.get_task_status(task_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/tasks/{task_id}")
async def cleanup_task(task_id: str):
    """
    Cleanup task resources.

    Args:
        task_id: Task ID

    Returns:
        Cleanup confirmation
    """
    try:
        TaskManager.cleanup_task(task_id)
        return {"status": "success", "message": f"Task {task_id} cleaned up"}
    except Exception as e:
        logger.error(f"Failed to cleanup task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "task-manager-api",
        "version": "0.1.0",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Task Manager API",
        "version": "0.1.0",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "metrics": "/dashboard/metrics",
    }