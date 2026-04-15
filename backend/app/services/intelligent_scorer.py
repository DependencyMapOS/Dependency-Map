"""Layer 5: intelligent scoring with explicit GNN vs uniform fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from postgrest.exceptions import APIError
from supabase import create_client

from app.config import settings
from app.services.ast_parser import build_ast_graph
from app.services.blast_radius import blast_radius_uniform_fallback, compute_blast_radius
from app.services.embedding_engine import embed_ast_nodes
from app.services.gnn_engine import infer_gnn_or_none

log = logging.getLogger(__name__)


def load_org_model(org_id: str) -> dict[str, Any] | None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    try:
        res = (
            sb.table("model_artifacts")
            .select("*")
            .eq("org_id", org_id)
            .eq("model_name", "gat-sage")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
    except APIError:
        return None
    row = res.data[0] if res.data else None
    if row and row.get("state_dict"):
        return row
    return None


def run_intelligent_scoring(
    org_id: str,
    repo_id: str,
    full_name: str,
    head_graph: dict[str, Any],
    base_graph: dict[str, Any],
    changed_files: list[str],
    *,
    head_repo_root: Path | None = None,
    head_sha: str = "",
) -> dict[str, Any]:
    """
    Returns blast dict, ml_metadata, schema_version, optional ML-enriched fields.
    """
    ml_metadata: dict[str, Any] = {
        "model_version": "gat-sage-v0",
        "embedding_model": "text-embedding-3-small",
        "inference_mode": "uniform_fallback",
    }
    ast_graph: dict[str, Any] = {
        "nodes": [],
        "edges": [],
        "node_count": 0,
        "edge_count": 0,
        "file_count": 0,
    }
    if head_repo_root is not None:
        try:
            ast_graph = build_ast_graph(head_repo_root)
        except Exception:
            log.exception("AST graph build failed for %s", full_name)

    model_row = load_org_model(org_id)
    gnn = infer_gnn_or_none(org_id, ast_graph, model_row)
    attention_valid = bool(gnn and gnn.get("attention_valid"))

    if attention_valid:
        blast = compute_blast_radius(head_graph, changed_files, base_graph)
        ml_metadata["inference_mode"] = "gnn"
        if gnn:
            ml_metadata["inference_ms"] = int(gnn.get("inference_ms", 0))
    else:
        blast = blast_radius_uniform_fallback(head_graph, changed_files, base_graph)
        ml_metadata["inference_mode"] = "uniform_fallback"

    if head_repo_root is not None and int(ast_graph.get("node_count") or 0) > 0:
        try:
            embed_ast_nodes(org_id, repo_id, head_sha, ast_graph)
        except Exception:
            log.exception("Embedding step skipped/failed")

    schema_version = 3 if int(ast_graph.get("node_count") or 0) > 0 else 2
    changed_nodes: list[dict[str, Any]] | None = None
    risk_anomalies: list[dict[str, Any]] | None = None
    if schema_version == 3:
        changed_nodes = [
            {"id": f"{p}:0:file", "kind": "file", "change": "touched"}
            for p in changed_files
        ]
        risk_anomalies = []

    ml_metadata["node_count"] = int(ast_graph.get("node_count") or 0)
    ml_metadata["edge_count"] = int(ast_graph.get("edge_count") or 0)

    return {
        "blast": blast,
        "ml_metadata": ml_metadata,
        "schema_version": schema_version,
        "changed_nodes": changed_nodes,
        "risk_anomalies": risk_anomalies,
    }
