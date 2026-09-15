import logging
import os
from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "researchops_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.pdf_tasks",
        "app.workers.export_tasks",
        "app.workers.summary_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
)


def dispatch_async_task(task_func, *args, **kwargs):
    """
    Dispatches task via Celery worker if available; otherwise falls back to running
    the function in an in-process thread pool so everything works locally without Redis.
    """
    try:
        if os.getenv("USE_CELERY", "false").lower() in ("true", "1", "yes"):
            return task_func.delay(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Celery dispatch failed: {e}. Running task synchronously.")

    # In-process execution fallback
    import threading
    thread = threading.Thread(target=task_func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return None
