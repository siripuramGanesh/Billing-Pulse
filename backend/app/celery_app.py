"""Celery application for background tasks."""

from celery import Celery

from .core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "billingpulse",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.call_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_retry_delay=60,  # 1 min
    task_max_retries=3,
    task_acks_late=True,  # Ack after task completes
    worker_prefetch_multiplier=1,  # One task at a time per worker
    beat_schedule={
        "process-scheduled-calls": {
            "task": "app.tasks.call_tasks.process_scheduled_calls",
            "schedule": 60.0,  # every 60 seconds
        },
    },
)
