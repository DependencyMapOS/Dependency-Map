"""Analysis jobs: GitHub fetch + graph + blast radius (Celery or inline)."""

from __future__ import annotations

import logging
import tempfile
import traceback
from pathlib import Path

from fastapi import BackgroundTasks
from supabase import create_client

from app.config import settings
from app.services.blast_radius import (
    compute_blast_radius,
    compute_cross_repo_blast_radius,
    stub_blast_summary,
)
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
from app.services.intelligent_scorer import run_intelligent_scoring
from app.worker.cross_repo_tasks import org_settings

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
        want_cross = bool(row.get("cross_repo"))

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

        oset = org_settings(sb, str(org_id))
        max_consumers = int(oset.get("max_consumer_repos") or settings.max_consumer_repos)

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
                    intel = run_intelligent_scoring(
                        str(org_id),
                        str(repo_id),
                        full_name,
                        g_head,
                        g_base,
                        changed,
                        head_repo_root=root_h,
                        head_sha=head_sha,
                    )
                    blast = intel.get("blast") or compute_blast_radius(g_head, changed, g_base)
                    co_text = fetch_codeowners_text(full_name, head_sha, token)
                    impacted = blast.get("impacted_modules", [])
                    reviewers = suggested_reviewers_from_codeowners(
                        co_text,
                        list(dict.fromkeys([*impacted, *changed])),
                    )
                    schema_version = int(intel.get("schema_version") or 2)
                    summary = {
                        "schema_version": schema_version,
                        "changed_files": changed,
                        "changed_dependency_edges": blast.get("changed_dependency_edges", []),
                        "impacted_modules": blast.get("impacted_modules", []),
                        "blast_radius_score": blast.get("blast_radius_score", 0),
                        "confidence": blast.get("confidence", "medium"),
                        "suggested_reviewers": reviewers,
                        "risks": blast.get("risks", []),
                    }
                    if intel.get("ml_metadata"):
                        summary["ml_metadata"] = intel["ml_metadata"]
                    if intel.get("changed_nodes") is not None:
                        summary["changed_nodes"] = intel["changed_nodes"]
                    if intel.get("risk_anomalies") is not None:
                        summary["risk_anomalies"] = intel["risk_anomalies"]

                    edges_res = (
                        sb.table("cross_repo_edges")
                        .select("*")
                        .eq("org_id", str(org_id))
                        .eq("target_repo_id", str(repo_id))
                        .execute()
                    )
                    cross_edges = edges_res.data or []
                    run_cross = want_cross or bool(cross_edges)
                    if run_cross and cross_edges:
                        consumers: dict[str, tuple[str, dict]] = {}
                        for e in cross_edges:
                            sid = str(e.get("source_repo_id") or "")
                            if sid == str(repo_id):
                                continue
                            if sid in consumers:
                                continue
                            cr = (
                                sb.table("repositories")
                                .select("full_name, default_branch")
                                .eq("id", sid)
                                .limit(1)
                                .execute()
                            )
                            if not cr.data:
                                continue
                            cfn = str(cr.data[0]["full_name"])
                            dbr = str(cr.data[0].get("default_branch") or "main")
                            snap = (
                                sb.table("dependency_snapshots")
                                .select("graph_json")
                                .eq("repo_id", sid)
                                .eq("branch", dbr)
                                .order("created_at", desc=True)
                                .limit(1)
                                .execute()
                            )
                            if snap.data:
                                consumers[sid] = (cfn, snap.data[0].get("graph_json") or {})
                        xb = compute_cross_repo_blast_radius(
                            full_name,
                            str(repo_id),
                            g_head,
                            changed,
                            cross_edges,
                            consumers,
                            max_consumer_repos=max_consumers,
                            max_super_nodes=settings.super_graph_max_nodes,
                        )
                        summary["cross_repo_impacts"] = xb.get("cross_repo_impacts", [])
                        summary["aggregate_cross_repo_score"] = xb.get(
                            "aggregate_cross_repo_score",
                            0,
                        )
                        summary["cross_repo_truncated"] = xb.get("cross_repo_truncated", False)
                        for imp in summary["cross_repo_impacts"]:
                            rid_imp = str(imp.get("repo_id") or "")
                            if not rid_imp:
                                continue
                            for fp in (imp.get("impacted_files") or [])[:25]:
                                if not isinstance(fp, str):
                                    continue
                                sb.table("risk_hotspots").insert(
                                    {
                                        "repo_id": rid_imp,
                                        "file_path": fp,
                                        "score": float(imp.get("blast_score", 0)) / 100.0,
                                        "reason": "cross_repo_blast",
                                    },
                                ).execute()
                    elif run_cross:
                        summary["cross_repo_impacts"] = []
                        summary["aggregate_cross_repo_score"] = 0
                        summary["cross_repo_truncated"] = False

                    # Persist head dependency edges for hotspot pipeline
                    edge_rows = [
                        {
                            "repo_id": str(repo_id),
                            "commit_sha": head_sha,
                            "branch": str(repo.get("default_branch") or "main"),
                            "source_path": str(e.get("source", "")),
                            "target_path": str(e.get("target", "")),
                            "edge_type": str(e.get("type", "import")),
                        }
                        for e in (g_head.get("edges") or [])
                        if isinstance(e, dict)
                    ]
                    if edge_rows:
                        sb.table("dependency_edges").delete().eq("repo_id", str(repo_id)).eq(
                            "commit_sha",
                            head_sha,
                        ).execute()
                        for i in range(0, len(edge_rows), 300):
                            sb.table("dependency_edges").insert(edge_rows[i : i + 300]).execute()

                    for path in impacted[:50]:
                        if isinstance(path, str) and path.endswith((".ts", ".tsx", ".js", ".jsx")):
                            sb.table("risk_hotspots").insert(
                                {
                                    "repo_id": str(repo_id),
                                    "file_path": path,
                                    "score": float(blast.get("blast_radius_score", 0)) / 100.0,
                                    "reason": "blast_radius",
                                },
                            ).execute()
            except Exception:
                log.exception("GitHub/graph pipeline failed for %s", analysis_id)
                summary = stub_blast_summary()
                summary["schema_version"] = 1
                summary["risks"] = [
                    *(summary.get("risks") or []),
                    f"pipeline_error: {traceback.format_exc(limit=1)}",
                ]
        else:
            summary = stub_blast_summary()
            summary["schema_version"] = 1
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
