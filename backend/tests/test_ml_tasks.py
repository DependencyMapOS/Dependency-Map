"""Tests for ML training task pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.worker.ml_tasks import _load_org_ast_graphs, train_org_model


def test_train_org_model_no_supabase(monkeypatch) -> None:
    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_url", "")
    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_service_role_key", "")
    train_org_model("org-1")


def test_load_ast_graphs_no_supabase(monkeypatch) -> None:
    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_url", "")
    result = _load_org_ast_graphs("org-1")
    assert result == []


def test_load_ast_graphs_with_data(monkeypatch) -> None:
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "repo-1"}, {"id": "repo-2"}]
    )
    snap_responses = [
        MagicMock(data=[{
            "ast_graph_json": {
                "nodes": [{"id": "n1"}],
                "edges": [{"source": "n1", "target": "n1"}],
            }
        }]),
        MagicMock(data=[{"ast_graph_json": {}}]),
    ]
    snap_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.order.return_value.limit.return_value.execute
    )
    snap_exec.side_effect = snap_responses

    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_url", "http://localhost")
    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_service_role_key", "key")

    with patch("supabase.create_client", return_value=mock_sb):
        graphs = _load_org_ast_graphs("org-1")

    assert len(graphs) == 1
    assert graphs[0]["nodes"][0]["id"] == "n1"


def test_train_org_model_full_pipeline(monkeypatch) -> None:
    """Integration: load graphs -> train -> persist -> update weights."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "repo-1"}]
    )
    snap_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.order.return_value.limit.return_value.execute
    )
    snap_exec.return_value = MagicMock(
        data=[{
            "ast_graph_json": {
                "nodes": [
                    {"id": "a:1:f"}, {"id": "a:2:g"}, {"id": "a:3:h"},
                ],
                "edges": [
                    {"source": "a:1:f", "target": "a:2:g"},
                    {"source": "a:2:g", "target": "a:3:h"},
                ],
            }
        }]
    )
    upsert_exec = (
        mock_sb.table.return_value.upsert.return_value.execute
    )
    upsert_exec.return_value = MagicMock(data=[])
    limit_exec = (
        mock_sb.table.return_value.select.return_value
        .eq.return_value.limit.return_value.execute
    )
    limit_exec.return_value = MagicMock(data=[{"settings": {}}])

    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_url", "http://localhost")
    monkeypatch.setattr("app.worker.ml_tasks.settings.supabase_service_role_key", "key")
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_url", "http://localhost")
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_service_role_key", "key")

    with (
        patch("supabase.create_client", return_value=mock_sb),
        patch("app.services.feedback_engine.create_client", return_value=mock_sb),
    ):
        train_org_model("org-1")
