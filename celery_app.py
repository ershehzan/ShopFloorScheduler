# celery_app.py
"""
Celery application instance for ShopFloorScheduler.

This module creates the shared Celery app that both:
- The FastAPI layer uses to dispatch tasks (.delay())
- The Celery worker process uses to execute them

Configuration is read from environment variables with sensible defaults
so the app works out-of-the-box with a local Redis instance.

Usage:
    Start worker:  celery -A celery_app worker --loglevel=info --pool=solo
    Inspect tasks: celery -A celery_app inspect active
"""
import os
from celery import Celery

# Allow overriding via environment for Docker / production deployments
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "shopfloor",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["scheduler.tasks"],   # Auto-discover task module
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability
    task_acks_late=True,           # Re-queue on worker crash
    worker_prefetch_multiplier=1,  # One task at a time per worker
    task_reject_on_worker_lost=True,

    # Result TTL — keep results for 2 hours
    result_expires=7200,

    # Timezone
    timezone="UTC",
    enable_utc=True,
)
