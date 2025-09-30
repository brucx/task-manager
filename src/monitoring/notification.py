"""Admin notification system for timeouts and failures."""
import logging
import httpx
from typing import Optional
from src.core.config import settings

logger = logging.getLogger(__name__)


def notify_admin_timeout(task_id: str, wait_time: float):
    """
    Notify admin about task timeout.

    Args:
        task_id: ID of timed out task
        wait_time: Time spent in queue before timeout
    """
    message = f"Task {task_id} timed out after {wait_time:.1f}s in queue"
    logger.warning(message)

    # Send webhook notification if configured
    if settings.admin_webhook_url:
        try:
            _send_webhook(
                url=settings.admin_webhook_url,
                payload={
                    "event": "task_timeout",
                    "task_id": task_id,
                    "wait_time": wait_time,
                    "message": message,
                },
            )
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

    # Send email notification if configured
    if settings.admin_email:
        try:
            _send_email(
                to=settings.admin_email,
                subject=f"Task Timeout Alert: {task_id}",
                body=message,
            )
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")


def notify_admin_failure(task_id: str, error: str):
    """
    Notify admin about task failure.

    Args:
        task_id: ID of failed task
        error: Error message
    """
    message = f"Task {task_id} failed: {error}"
    logger.error(message)

    if settings.admin_webhook_url:
        try:
            _send_webhook(
                url=settings.admin_webhook_url,
                payload={
                    "event": "task_failure",
                    "task_id": task_id,
                    "error": error,
                    "message": message,
                },
            )
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")


def _send_webhook(url: str, payload: dict):
    """Send webhook notification."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"Webhook notification sent to {url}")


def _send_email(to: str, subject: str, body: str):
    """
    Send email notification.

    Placeholder implementation - integrate with actual email service.
    """
    # In production, integrate with SendGrid, SES, etc.
    logger.info(f"Would send email to {to}: {subject}")
    pass