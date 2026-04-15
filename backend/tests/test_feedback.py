"""Tests for Layer 6: RLHF feedback engine with real weight computation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.feedback_engine import (
    DEFAULT_ATTENTION_THRESHOLD,
    DEFAULT_DECAY_FACTOR,
    DEFAULT_EDGE_WEIGHTS,
    _compute_weights_from_feedback,
    maybe_update_org_weights,
)


def test_maybe_update_skips_without_supabase(monkeypatch) -> None:
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_url", "")
    out = maybe_update_org_weights("00000000-0000-0000-0000-000000000001")
    assert out["status"] == "skipped"


def test_compute_weights_empty_feedback() -> None:
    weights = _compute_weights_from_feedback([])
    assert weights["edge_type_weights"] == DEFAULT_EDGE_WEIGHTS
    assert weights["attention_threshold"] == DEFAULT_ATTENTION_THRESHOLD
    assert weights["decay_factor"] == DEFAULT_DECAY_FACTOR


def test_compute_weights_all_positive() -> None:
    rows = [
        {"action": "addressed", "comment_type": "import"},
        {"action": "thumbs_up", "comment_type": "import"},
        {"action": "addressed", "comment_type": "call"},
        {"action": "thumbs_up", "comment_type": "call"},
    ]
    weights = _compute_weights_from_feedback(rows)
    assert weights["edge_type_weights"]["import"] == 1.5
    assert weights["edge_type_weights"]["call"] == 1.5
    assert weights["attention_threshold"] < DEFAULT_ATTENTION_THRESHOLD
    assert weights["decay_factor"] > DEFAULT_DECAY_FACTOR


def test_compute_weights_all_negative() -> None:
    rows = [
        {"action": "dismissed", "comment_type": "import"},
        {"action": "thumbs_down", "comment_type": "import"},
        {"action": "dismissed", "comment_type": "call"},
        {"action": "thumbs_down", "comment_type": "call"},
    ]
    weights = _compute_weights_from_feedback(rows)
    assert weights["edge_type_weights"]["import"] == 0.5
    assert weights["edge_type_weights"]["call"] == 0.5
    assert weights["attention_threshold"] > DEFAULT_ATTENTION_THRESHOLD
    assert weights["decay_factor"] < DEFAULT_DECAY_FACTOR


def test_compute_weights_mixed_feedback() -> None:
    rows = [
        {"action": "addressed", "comment_type": "import"},
        {"action": "addressed", "comment_type": "import"},
        {"action": "dismissed", "comment_type": "import"},
        {"action": "addressed", "comment_type": "call"},
        {"action": "dismissed", "comment_type": "call"},
        {"action": "dismissed", "comment_type": "call"},
    ]
    weights = _compute_weights_from_feedback(rows)
    import_weight = weights["edge_type_weights"]["import"]
    call_weight = weights["edge_type_weights"]["call"]
    assert import_weight > call_weight, "import has 2/3 acceptance vs call 1/3"
    assert 1.0 < import_weight <= 1.5
    assert 0.5 <= call_weight < 1.0


def test_compute_weights_unseen_types_get_defaults() -> None:
    rows = [
        {"action": "addressed", "comment_type": "custom_type"},
    ]
    weights = _compute_weights_from_feedback(rows)
    assert "custom_type" in weights["edge_type_weights"]
    assert weights["edge_type_weights"]["custom_type"] == 1.5
    for default_type in DEFAULT_EDGE_WEIGHTS:
        assert default_type in weights["edge_type_weights"]
        assert weights["edge_type_weights"][default_type] == DEFAULT_EDGE_WEIGHTS[default_type]


def test_compute_weights_single_type_boundary() -> None:
    rows = [{"action": "addressed", "comment_type": "import"}]
    weights = _compute_weights_from_feedback(rows)
    assert weights["edge_type_weights"]["import"] == 1.5


def test_maybe_update_noop_no_feedback(monkeypatch) -> None:
    mock_sb = MagicMock()
    limit_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.limit.return_value.execute
    )
    limit_exec.return_value = MagicMock(
        data=[{"settings": {"feedback_min_pairs_for_update": 5}}]
    )
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[]
    )
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_url", "http://localhost")
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_service_role_key", "key")

    with patch("app.services.feedback_engine.create_client", return_value=mock_sb):
        out = maybe_update_org_weights("org-1")

    assert out["status"] == "noop"
    assert out["pairs"] == 0


def test_maybe_update_partial_blending(monkeypatch) -> None:
    """Below min_pairs threshold: weights should be blended toward defaults."""
    mock_sb = MagicMock()
    limit_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.limit.return_value.execute
    )
    limit_exec.return_value = MagicMock(
        data=[{"settings": {"feedback_min_pairs_for_update": 100}}]
    )
    feedback_rows = [
        {"id": "1", "action": "addressed", "comment_type": "import", "comment_node_id": "n1"},
        {"id": "2", "action": "addressed", "comment_type": "import", "comment_node_id": "n2"},
        {"id": "3", "action": "dismissed", "comment_type": "call", "comment_node_id": "n3"},
    ]
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=feedback_rows
    )
    mock_sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])

    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_url", "http://localhost")
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_service_role_key", "key")

    with patch("app.services.feedback_engine.create_client", return_value=mock_sb):
        out = maybe_update_org_weights("org-1")

    assert out["status"] == "updated_partial"
    assert out["pairs"] == 3
    weights = out["weights"]
    import_w = weights["edge_type_weights"]["import"]
    assert 1.0 <= import_w <= 1.5, (
        f"Blended weight should be between default and learned: {import_w}"
    )


def test_maybe_update_full_above_threshold(monkeypatch) -> None:
    """Above min_pairs: weights should reflect actual feedback distribution."""
    mock_sb = MagicMock()
    limit_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.limit.return_value.execute
    )
    limit_exec.return_value = MagicMock(
        data=[{"settings": {"feedback_min_pairs_for_update": 2}}]
    )
    feedback_rows = [
        {"id": "1", "action": "addressed", "comment_type": "import", "comment_node_id": "n1"},
        {"id": "2", "action": "addressed", "comment_type": "import", "comment_node_id": "n2"},
        {"id": "3", "action": "dismissed", "comment_type": "call", "comment_node_id": "n3"},
    ]
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=feedback_rows
    )
    mock_sb.table.return_value.upsert.return_value.execute.return_value = MagicMock(data=[])

    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_url", "http://localhost")
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_service_role_key", "key")

    with patch("app.services.feedback_engine.create_client", return_value=mock_sb):
        out = maybe_update_org_weights("org-1")

    assert out["status"] == "updated"
    assert out["pairs"] == 3
    weights = out["weights"]
    assert weights["edge_type_weights"]["import"] == 1.5
    assert weights["edge_type_weights"]["call"] == 0.5
