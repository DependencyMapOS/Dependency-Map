"""Celery app for analysis workers."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "dependency_map",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="dm.run_analysis")
def run_analysis_task(analysis_id: str) -> None:
    from app.worker.tasks import run_analysis_job

    run_analysis_job(analysis_id)
