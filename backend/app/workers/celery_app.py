from celery import Celery
from app.config import settings

celery_app = Celery(
    "british_auction_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Celery Beat schedule for periodic auction status reconciliation
    beat_schedule={
        "reconcile-auction-statuses-every-5-seconds": {
            "task": "app.workers.tasks.reconcile_auction_statuses",
            "schedule": 5.0,  # Run every 5 seconds
        },
    },
)
