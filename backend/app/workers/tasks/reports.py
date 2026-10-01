"""``reports.export(job_id)``: thin wrapper; the work lives in ``app.modules.reports.service.run_export_job`` (WP4b)."""

from app.core.celery_app import celery_app
from app.workers.runtime import call_job_function, run_async


@celery_app.task(name="reports.export")
def export_report(job_id: str) -> None:
    from app.modules.reports.service import run_export_job  # lazy: avoid import cycles at worker boot

    run_async(call_job_function(run_export_job, job_id))
