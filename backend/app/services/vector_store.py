"""Layer 4: hybrid retrieval (vector + keyword + graph walk)."""

from __future__ import annotations

from typing import Any


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, (node_id, _s) in enumerate(lst, start=1):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def hybrid_retrieve(
    _repo_id: str,
    _query_text: str,
    _query_embedding: list[float] | None,
    *,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """Stub DB hook: extend with pgvector + tsvector queries when wired."""
    return [{"node_id": "", "score": 0.0, "code_snippet": "", "file": "", "reason": "stub"}][:top_k]
