"""Layer 3: GAT+GraphSAGE-style encoding (optional torch-geometric)."""

from __future__ import annotations

import time
from typing import Any


def infer_gnn_or_none(
    org_id: str,
    ast_graph: dict[str, Any],
    model_row: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Returns dict with attention_valid True only when a trained checkpoint loads and runs.
    Otherwise None (caller must use blast_radius_uniform_fallback).
    """
    if not model_row or not model_row.get("state_dict"):
        return None
    try:
        import torch  # noqa: F401
    except ImportError:
        return None
    t0 = time.perf_counter()
    _ = org_id, ast_graph
    # Placeholder: real PyG forward pass would load state_dict here.
    return {
        "attention_valid": False,
        "inference_ms": int((time.perf_counter() - t0) * 1000),
    }


def train_link_prediction_stub(org_id: str, graphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Reserved for nightly training; no-op without torch-geometric."""
    return {"org_id": org_id, "graphs": len(graphs), "status": "skipped"}
