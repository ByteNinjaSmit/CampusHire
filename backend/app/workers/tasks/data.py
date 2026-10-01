"""``data.export`` / ``data.import``: thin wrappers around the admin exporter / importer (WP4c)."""

from app.core.celery_app import celery_app
from app.workers.runtime import call_job_function, run_async


@celery_app.task(name="data.export")
def export_data(job_id: str) -> None:
    from app.modules.admin.exporter import run_export_job

    run_async(call_job_function(run_export_job, job_id))


@celery_app.task(name="data.import")
def import_data(job_id: str) -> None:
    from app.modules.admin.importer import run_import_job

    run_async(call_job_function(run_import_job, job_id))
