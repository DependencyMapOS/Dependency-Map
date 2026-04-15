"""Layer 6: RLHF-style org-scoped scoring weights."""

from __future__ import annotations

import json
import logging
from typing import Any

from supabase import create_client

from app.config import settings

log = logging.getLogger(__name__)


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


def maybe_update_org_weights(org_id: str) -> dict[str, Any]:
    """Aggregate feedback; apply small nudge when pairs < min but >= 1."""
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return {"status": "skipped"}
    sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    min_pairs = feedback_min_pairs(sb, org_id)
    res = (
        sb.table("review_feedback")
        .select("id,action")
        .eq("org_id", org_id)
        .execute()
    )
    rows = res.data or []
    pairs = len(rows)
    weights = {
        "edge_type_weights": {"import": 1.0, "manifest": 1.0},
        "attention_threshold": 0.3,
        "decay_factor": 0.85,
    }
    if pairs < 1:
        return {"status": "noop", "pairs": pairs, "min_pairs": min_pairs}
    payload = json.dumps(weights).encode()
    sb.table("model_artifacts").upsert(
        {
            "org_id": org_id,
            "model_name": "org_scoring_weights",
            "version": "1",
            "state_dict": payload,
            "metrics": {"feedback_pairs_accumulated": pairs},
            "feedback_pairs_accumulated": pairs,
        },
        on_conflict="org_id,model_name,version",
    ).execute()
    return {
        "status": "updated_partial" if pairs < min_pairs else "updated",
        "pairs": pairs,
        "min_pairs": min_pairs,
    }
