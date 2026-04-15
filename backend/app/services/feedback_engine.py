"""Layer 6: RLHF-style org-scoped scoring weights derived from human feedback."""

from __future__ import annotations

import json
import logging
import math
from collections import Counter
from typing import Any

from supabase import create_client

from app.config import settings

log = logging.getLogger(__name__)

POSITIVE_ACTIONS = {"addressed", "thumbs_up"}
NEGATIVE_ACTIONS = {"dismissed", "thumbs_down"}

DEFAULT_EDGE_WEIGHTS: dict[str, float] = {
    "import": 1.0,
    "manifest": 1.0,
    "call": 1.0,
    "inheritance": 1.0,
    "type_reference": 1.0,
}
DEFAULT_ATTENTION_THRESHOLD = 0.3
DEFAULT_DECAY_FACTOR = 0.85


def feedback_min_pairs(sb: Any, org_id: str) -> int:
    res = sb.table("organizations").select("settings").eq("id", org_id).limit(1).execute()
    if not res.data:
        return 10
    st = res.data[0].get("settings") or {}
    if not isinstance(st, dict):
        return 10
    v = int(st.get("feedback_min_pairs_for_update", 10))
    return max(1, v)


def record_feedback(
    org_id: str,
    analysis_id: str | None,
    comment_node_id: str,
    comment_type: str,
    action: str,
) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    sb.table("review_feedback").insert(
        {
            "org_id": org_id,
            "analysis_id": analysis_id,
            "comment_node_id": comment_node_id,
            "comment_type": comment_type,
            "action": action,
        },
    ).execute()


def _compute_weights_from_feedback(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Derive edge-type weights and scoring parameters from feedback distribution.

    Strategy:
    - Group feedback by comment_type (maps to edge types like import, call, etc.)
    - Compute acceptance ratio per type: addressed / (addressed + dismissed)
    - Scale edge weights proportionally to acceptance ratio (higher acceptance = higher weight)
    - Adjust attention threshold: lower it if most feedback is positive (cast wider net),
      raise it if most is negative (be more selective)
    - Adjust decay factor based on depth-related patterns in feedback
    """
    type_pos: Counter[str] = Counter()
    type_neg: Counter[str] = Counter()
    total_pos = 0
    total_neg = 0

    for r in rows:
        action = str(r.get("action", ""))
        ctype = str(r.get("comment_type", "general"))
        if action in POSITIVE_ACTIONS:
            type_pos[ctype] += 1
            total_pos += 1
        elif action in NEGATIVE_ACTIONS:
            type_neg[ctype] += 1
            total_neg += 1

    total = total_pos + total_neg
    if total == 0:
        return {
            "edge_type_weights": DEFAULT_EDGE_WEIGHTS.copy(),
            "attention_threshold": DEFAULT_ATTENTION_THRESHOLD,
            "decay_factor": DEFAULT_DECAY_FACTOR,
        }

    global_acceptance = total_pos / total

    edge_type_weights: dict[str, float] = {}
    all_types = set(type_pos.keys()) | set(type_neg.keys()) | set(DEFAULT_EDGE_WEIGHTS.keys())
    for t in all_types:
        pos = type_pos.get(t, 0)
        neg = type_neg.get(t, 0)
        type_total = pos + neg
        if type_total == 0:
            edge_type_weights[t] = DEFAULT_EDGE_WEIGHTS.get(t, 1.0)
        else:
            acceptance = pos / type_total
            edge_type_weights[t] = round(0.5 + acceptance, 4)

    attention_threshold = DEFAULT_ATTENTION_THRESHOLD
    if global_acceptance > 0.7:
        attention_threshold = max(0.1, DEFAULT_ATTENTION_THRESHOLD - 0.1)
    elif global_acceptance < 0.3:
        attention_threshold = min(0.6, DEFAULT_ATTENTION_THRESHOLD + 0.15)

    decay_factor = DEFAULT_DECAY_FACTOR
    if global_acceptance > 0.6:
        decay_factor = min(0.95, DEFAULT_DECAY_FACTOR + 0.05)
    elif global_acceptance < 0.4:
        decay_factor = max(0.7, DEFAULT_DECAY_FACTOR - 0.05)

    return {
        "edge_type_weights": edge_type_weights,
        "attention_threshold": round(attention_threshold, 4),
        "decay_factor": round(decay_factor, 4),
    }


def maybe_update_org_weights(org_id: str) -> dict[str, Any]:
    """
    Aggregate feedback and compute real scoring weights.
    Applies partial nudge when pairs < min threshold but >= 1.
    """
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return {"status": "skipped"}
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    min_pairs = feedback_min_pairs(sb, org_id)
    res = (
        sb.table("review_feedback")
        .select("id,action,comment_type,comment_node_id")
        .eq("org_id", org_id)
        .execute()
    )
    rows = res.data or []
    pairs = len(rows)

    if pairs < 1:
        return {"status": "noop", "pairs": pairs, "min_pairs": min_pairs}

    weights = _compute_weights_from_feedback(rows)

    if pairs < min_pairs:
        blend_factor = math.sqrt(pairs / min_pairs)
        blended_edge_weights: dict[str, float] = {}
        for k in set(weights["edge_type_weights"]) | set(DEFAULT_EDGE_WEIGHTS):
            learned = weights["edge_type_weights"].get(k, 1.0)
            default = DEFAULT_EDGE_WEIGHTS.get(k, 1.0)
            blended_edge_weights[k] = round(
                default * (1 - blend_factor) + learned * blend_factor,
                4,
            )
        weights["edge_type_weights"] = blended_edge_weights
        weights["attention_threshold"] = round(
            DEFAULT_ATTENTION_THRESHOLD * (1 - blend_factor)
            + weights["attention_threshold"] * blend_factor,
            4,
        )
        weights["decay_factor"] = round(
            DEFAULT_DECAY_FACTOR * (1 - blend_factor)
            + weights["decay_factor"] * blend_factor,
            4,
        )

    payload = json.dumps(weights).encode()
    sb.table("model_artifacts").upsert(
        {
            "org_id": org_id,
            "model_name": "org_scoring_weights",
            "version": "1",
            "state_dict": payload,
            "metrics": {
                "feedback_pairs_accumulated": pairs,
                "global_acceptance": round(
                    sum(1 for r in rows if r.get("action") in POSITIVE_ACTIONS) / max(pairs, 1),
                    4,
                ),
                "unique_types": len({r.get("comment_type") for r in rows}),
            },
            "feedback_pairs_accumulated": pairs,
        },
        on_conflict="org_id,model_name,version",
    ).execute()

    return {
        "status": "updated_partial" if pairs < min_pairs else "updated",
        "pairs": pairs,
        "min_pairs": min_pairs,
        "weights": weights,
    }
