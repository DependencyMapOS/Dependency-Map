"""BackgroundTasks handlers; replace with Redis/RQ/Celery for production."""

from supabase import create_client

from app.config import settings
from app.services.blast_radius import stub_blast_summary


def run_analysis_job(analysis_id: str) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    sb.table("pr_analyses").update({"status": "running"}).eq("id", analysis_id).execute()
    summary = stub_blast_summary()
    sb.table("pr_analyses").update(
        {
            "status": "completed",
            "summary_json": summary,
        },
    ).eq("id", analysis_id).execute()
