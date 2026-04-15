"""Tests for Layer 4: hybrid retrieval (vector + keyword + graph walk)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.vector_store import (
    hybrid_retrieve,
    reciprocal_rank_fusion,
)


def test_reciprocal_rank_fusion_basic() -> None:
    fused = reciprocal_rank_fusion(
        [
            [("a", 1.0), ("b", 0.5)],
            [("b", 1.0), ("c", 0.2)],
        ],
    )
    ids = [x[0] for x in fused]
    assert "b" in ids
    assert "a" in ids
    assert "c" in ids
    b_score = next(s for n, s in fused if n == "b")
    a_score = next(s for n, s in fused if n == "a")
    assert b_score > a_score, "b appears in both lists, should rank higher"


def test_rrf_single_list() -> None:
    fused = reciprocal_rank_fusion([[("x", 1.0), ("y", 0.5)]])
    assert len(fused) == 2
    assert fused[0][0] == "x"
    assert fused[0][1] > fused[1][1]


def test_rrf_empty_lists() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[]]) == []


def test_rrf_three_lists_overlap() -> None:
    fused = reciprocal_rank_fusion([
        [("a", 1.0), ("b", 0.8), ("c", 0.5)],
        [("c", 1.0), ("a", 0.7)],
        [("a", 1.0), ("d", 0.3)],
    ])
    ids = [x[0] for x in fused]
    a_score = next(s for n, s in fused if n == "a")
    d_score = next(s for n, s in fused if n == "d")
    assert a_score > d_score, "a appears in all 3 lists, d in only 1"
    assert "a" in ids
    assert "d" in ids


def test_rrf_custom_k() -> None:
    fused_low_k = reciprocal_rank_fusion([[("a", 1.0), ("b", 0.5)]], k=1)
    fused_high_k = reciprocal_rank_fusion([[("a", 1.0), ("b", 0.5)]], k=1000)
    a_low = next(s for n, s in fused_low_k if n == "a")
    b_low = next(s for n, s in fused_low_k if n == "b")
    a_high = next(s for n, s in fused_high_k if n == "a")
    b_high = next(s for n, s in fused_high_k if n == "b")
    gap_low = a_low - b_low
    gap_high = a_high - b_high
    assert gap_low > gap_high, "Lower k amplifies rank differences"


def test_hybrid_retrieve_no_supabase(monkeypatch) -> None:
    monkeypatch.setattr("app.services.vector_store.settings.supabase_url", "")
    result = hybrid_retrieve("repo-1", "function auth")
    assert result == []


def test_hybrid_retrieve_with_mock_db(monkeypatch) -> None:
    """Verify full pipeline: vector search -> keyword search -> graph walk -> RRF fusion."""
    mock_sb = MagicMock()

    mock_sb.rpc.return_value.execute.side_effect = [
        MagicMock(data=[
            {"node_id": "auth.ts:5:login", "similarity": 0.92},
            {"node_id": "user.ts:10:getUser", "similarity": 0.85},
            {"node_id": "session.ts:3:validate", "similarity": 0.78},
        ]),
        MagicMock(data=[
            {"node_id": "auth.ts:5:login", "rank": 2.5},
            {"node_id": "middleware.ts:1:authMiddleware", "rank": 1.8},
        ]),
    ]
    snap_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.order.return_value.limit.return_value.execute
    )
    snap_exec.return_value = MagicMock(
        data=[{
            "graph_json": {
                "nodes": [],
                "edges": [
                    {"source": "auth.ts:5:login", "target": "db.ts:20:query"},
                    {"source": "routes.ts:1:setup", "target": "auth.ts:5:login"},
                ],
            }
        }]
    )
    in_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.in_.return_value.execute
    )
    in_exec.return_value = MagicMock(
        data=[
            {"node_id": "auth.ts:5:login", "content_hash": "abc123"},
            {"node_id": "user.ts:10:getUser", "content_hash": "def456"},
        ]
    )

    monkeypatch.setattr("app.services.vector_store.settings.supabase_url", "http://localhost:54321")
    monkeypatch.setattr("app.services.vector_store.settings.supabase_service_role_key", "test-key")

    with patch("app.services.vector_store._get_supabase", return_value=mock_sb):
        results = hybrid_retrieve(
            "repo-1",
            "authentication login",
            query_embedding=[0.1] * 1536,
            top_k=10,
        )

    assert len(results) >= 1
    node_ids = {r["node_id"] for r in results}
    assert "auth.ts:5:login" in node_ids, "Top result from both lists should appear"
    for r in results:
        assert "score" in r
        assert "node_id" in r
        assert r["score"] > 0


def test_hybrid_retrieve_vector_only_fallback(monkeypatch) -> None:
    """When keyword search returns nothing, vector results still come through."""
    mock_sb = MagicMock()
    mock_sb.rpc.return_value.execute.side_effect = [
        MagicMock(data=[
            {"node_id": "a.ts:1:func", "similarity": 0.9},
        ]),
        MagicMock(data=[]),
    ]
    snap_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.order.return_value.limit.return_value.execute
    )
    snap_exec.return_value = MagicMock(data=[])
    in_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.in_.return_value.execute
    )
    in_exec.return_value = MagicMock(data=[])

    monkeypatch.setattr("app.services.vector_store.settings.supabase_url", "http://localhost:54321")
    monkeypatch.setattr("app.services.vector_store.settings.supabase_service_role_key", "test-key")

    with patch("app.services.vector_store._get_supabase", return_value=mock_sb):
        results = hybrid_retrieve("repo-1", "test", query_embedding=[0.1] * 1536)

    assert len(results) >= 1
    assert results[0]["node_id"] == "a.ts:1:func"
