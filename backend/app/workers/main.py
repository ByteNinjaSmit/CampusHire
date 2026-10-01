"""Celery worker entrypoint: ``celery -A app.workers.main worker -B``.

Imports the shared producer instance from ``app.core.celery_app`` (no tasks there), registers every task
module and defines the beat schedule (plan WP4). Times are UTC (``celery_app.conf.timezone``).
"""

from celery.schedules import crontab

from app.core.celery_app import celery_app

celery_app.conf.update(
    worker_hijack_root_logger=False,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "compliance-scan-daily": {
            "task": "maintenance.compliance_scan",
            "schedule": crontab(hour=2, minute=0),
        },
        "close-expired-internships-hourly": {
            "task": "maintenance.close_expired_internships",
            "schedule": crontab(minute=0),
        },
        "cleanup-tokens-daily": {
            "task": "maintenance.cleanup_tokens",
            "schedule": crontab(hour=3, minute=30),
        },
        "purge-pending-uploads-hourly": {
            "task": "maintenance.purge_pending_uploads",
            "schedule": crontab(minute=15),
        },
        "interview-reminders-every-15-min": {
            "task": "interviews.send_reminders",
            "schedule": crontab(minute="*/15"),
        },
    },
)

# Importing the task modules registers the tasks on ``celery_app``.
from app.workers.tasks import data, emails, interviews, maintenance, reports  # noqa: E402, F401

# Celery looks for ``app`` / ``celery`` in the module given to ``-A``.
app = celery = celery_app
