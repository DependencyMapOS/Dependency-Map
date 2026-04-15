"""Celery tasks for ML training / refresh."""

from __future__ import annotations

import base64
import logging
from typing import Any

from app.config import settings
from app.services.feedback_engine import maybe_update_org_weights
from app.services.gnn_engine import train_link_prediction

log = logging.getLogger(__name__)


def _load_org_ast_graphs(org_id: str) -> list[dict[str, Any]]:
    """Fetch the latest AST graph snapshot per repo for the org."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []
    from supabase import create_client

    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)

    repos_res = sb.table("repositories").select("id").eq("org_id", org_id).execute()
    repo_ids = [str(r["id"]) for r in (repos_res.data or [])]
    if not repo_ids:
        return []

    graphs: list[dict[str, Any]] = []
    for rid in repo_ids:
        snap_res = (
            sb.table("ast_graph_snapshots")
            .select("ast_graph_json")
            .eq("repo_id", rid)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if snap_res.data and snap_res.data[0].get("ast_graph_json"):
            g = snap_res.data[0]["ast_graph_json"]
            if isinstance(g, dict) and (g.get("nodes") or g.get("edges")):
                graphs.append(g)

    return graphs


def _persist_model_artifact(org_id: str, result: dict[str, Any]) -> None:
    """Save trained model state_dict + metrics to model_artifacts."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    state_bytes = result.get("state_dict")
    if not state_bytes:
        return
    from supabase import create_client

    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    encoded = base64.b64encode(state_bytes).decode("ascii")
    sb.table("model_artifacts").upsert(
        {
            "org_id": org_id,
            "model_name": "gat-sage",
            "version": "1",
            "state_dict": encoded,
            "metrics": {
                "final_loss": result.get("final_loss"),
                "graphs_trained": result.get("graphs"),
                "params": result.get("params"),
            },
        },
        on_conflict="org_id,model_name,version",
    ).execute()


def train_org_model(org_id: str) -> None:
    """
    Nightly training pipeline:
    1. Load AST graphs for all repos in the org
    2. Train GAT+GraphSAGE via self-supervised link prediction
    3. Persist the checkpoint to model_artifacts
    4. Update RLHF scoring weights from accumulated feedback
    """
    log.info("train_org_model starting for org %s", org_id)

    graphs = _load_org_ast_graphs(org_id)
    log.info("Loaded %d AST graphs for org %s", len(graphs), org_id)

    if graphs:
        result = train_link_prediction(org_id, graphs)
        log.info("GNN training result for org %s: status=%s", org_id, result.get("status"))
        if result.get("status") == "trained":
            _persist_model_artifact(org_id, result)
            log.info(
                "Persisted GNN model for org %s (loss=%.4f, params=%s)",
                org_id,
                result.get("final_loss", 0),
                result.get("params", 0),
            )
    else:
        log.info("No AST graphs available for org %s; skipping GNN training", org_id)

    weights_result = maybe_update_org_weights(org_id)
    log.info(
        "RLHF weights update for org %s: status=%s, pairs=%s",
        org_id,
        weights_result.get("status"),
        weights_result.get("pairs"),
    )
