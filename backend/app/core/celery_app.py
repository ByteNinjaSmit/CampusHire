"""Celery *producer* instance + config. Tasks live in app/workers (WP4); the API enqueues by string name."""

from celery import Celery

from app.core.config import settings

celery_app = Celery("campushire", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"socket_connect_timeout": 3, "socket_timeout": 3},
    result_expires=3600,
)
