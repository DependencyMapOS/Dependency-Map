"""Analysis jobs: GitHub fetch + graph + blast radius (Celery or inline)."""

from __future__ import annotations

import logging
import tempfile
import traceback
from pathlib import Path

from fastapi import BackgroundTasks
from supabase import create_client

from app.config import settings
from app.services.blast_radius import compute_blast_radius, stub_blast_summary
from app.services.codeowners import suggested_reviewers_from_codeowners
from app.services.github_client import (
    changed_files_from_compare,
    compare_commits,
    fetch_codeowners_text,
    fetch_tarball_to_dir,
    get_installation_token,
    github_configured,
)
from app.services.graph_builder import build_dependency_graph

log = logging.getLogger(__name__)


def schedule_analysis_job(
    analysis_id: str,
    background: BackgroundTasks | None = None,
) -> None:
    """Run via Celery when configured; otherwise FastAPI BackgroundTasks or inline."""
    if settings.use_celery:
        try:
            from app.celery_app import run_analysis_task

            run_analysis_task.delay(analysis_id)
        except Exception:
            log.exception("Celery enqueue failed; running inline")
            run_analysis_job(analysis_id)
        return
    if background is not None:
        background.add_task(run_analysis_job, analysis_id)
    else:
        run_analysis_job(analysis_id)


def run_analysis_job(analysis_id: str) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        log.warning("Supabase not configured; skip analysis %s", analysis_id)
        return

    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)

    try:
        res = (
            sb.table("pr_analyses")
            .select("*")
            .eq("id", analysis_id)
            .limit(1)
            .execute()
        )
        if not res.data:
            log.error("Analysis %s not found", analysis_id)
            return
        row = res.data[0]
        repo_id = row["repo_id"]
        base_sha = row.get("base_sha") or ""
        head_sha = row.get("head_sha") or ""

        sb.table("pr_analyses").update({"status": "running"}).eq("id", analysis_id).execute()

        rres = (
            sb.table("repositories")
            .select("*")
            .eq("id", repo_id)
            .limit(1)
            .execute()
        )
        if not rres.data:
            raise RuntimeError("Repository not found for analysis")

        repo = rres.data[0]
        full_name = repo["full_name"]
        org_id = repo["org_id"]

        iresv = (
            sb.table("github_installations")
            .select("installation_id")
            .eq("org_id", org_id)
            .limit(1)
            .execute()
        )
        installation_id = iresv.data[0]["installation_id"] if iresv.data else None

        summary: dict = {}

        if (
            github_configured()
            and installation_id is not None
            and base_sha
            and head_sha
        ):
            try:
                token = get_installation_token(int(installation_id))
                with tempfile.TemporaryDirectory() as tmp:
                    base_root = Path(tmp) / "b"
                    head_root = Path(tmp) / "h"
                    root_b = fetch_tarball_to_dir(full_name, base_sha, token, base_root)
                    root_h = fetch_tarball_to_dir(full_name, head_sha, token, head_root)
                    g_base = build_dependency_graph(root_b)
                    g_head = build_dependency_graph(root_h)
                    compare_js = compare_commits(full_name, base_sha, head_sha, token)
                    changed = changed_files_from_compare(compare_js)
                    blast = compute_blast_radius(g_head, changed, g_base)
                    co_text = fetch_codeowners_text(full_name, head_sha, token)
                    impacted = blast.get("impacted_modules", [])
                    reviewers = suggested_reviewers_from_codeowners(
                        co_text,
                        list(dict.fromkeys([*impacted, *changed])),
                    )
                    summary = {
                        "schema_version": 1,
                        "changed_files": changed,
                        "changed_dependency_edges": blast.get("changed_dependency_edges", []),
                        "impacted_modules": blast.get("impacted_modules", []),
                        "blast_radius_score": blast.get("blast_radius_score", 0),
                        "confidence": blast.get("confidence", "medium"),
                        "suggested_reviewers": reviewers,
                        "risks": blast.get("risks", []),
                    }
            except Exception:
                log.exception("GitHub/graph pipeline failed for %s", analysis_id)
                summary = stub_blast_summary()
                summary["risks"] = [
                    *(summary.get("risks") or []),
                    f"pipeline_error: {traceback.format_exc(limit=1)}",
                ]
        else:
            summary = stub_blast_summary()
            summary["risks"] = [
                *(summary.get("risks") or []),
                "GitHub App or installation not configured, or SHAs missing — stub summary.",
            ]

        sb.table("pr_analyses").update(
            {"status": "completed", "summary_json": summary, "error": None},
        ).eq("id", analysis_id).execute()
    except Exception:
        log.exception("Analysis job failed %s", analysis_id)
        sb.table("pr_analyses").update(
            {
                "status": "failed",
                "error": traceback.format_exc()[:8000],
            },
        ).eq("id", analysis_id).execute()
