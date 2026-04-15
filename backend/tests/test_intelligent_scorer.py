"""Tests for Layer 5: intelligent scoring with GNN vs uniform fallback."""

from pathlib import Path

import pytest

from app.services.intelligent_scorer import run_intelligent_scoring


def test_run_intelligent_scoring_uniform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No live Supabase/OpenAI — scoring path must be deterministic."""
    monkeypatch.setattr("app.services.intelligent_scorer.load_org_model", lambda _oid: None)
    monkeypatch.setattr("app.services.intelligent_scorer.embed_ast_nodes", lambda *a, **k: None)

    (tmp_path / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    head = {"nodes": [{"id": "a.ts", "path": "a.ts", "type": "file"}], "edges": []}
    base = {"nodes": [{"id": "a.ts", "path": "a.ts", "type": "file"}], "edges": []}
    out = run_intelligent_scoring(
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "o/r",
        head,
        base,
        ["a.ts"],
        head_repo_root=tmp_path,
        head_sha="abc",
    )
    assert out["ml_metadata"]["inference_mode"] == "uniform_fallback"
    assert int(out["schema_version"]) in (2, 3)
    assert "blast" in out


def test_scoring_with_gnn_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When GNN returns valid attention, scoring mode should be 'gnn'."""
    monkeypatch.setattr(
        "app.services.intelligent_scorer.load_org_model",
        lambda _oid: {"state_dict": b"mock"},
    )
    monkeypatch.setattr(
        "app.services.intelligent_scorer.infer_gnn_or_none",
        lambda _org, _g, _m: {"attention_valid": True, "inference_ms": 42},
    )
    monkeypatch.setattr("app.services.intelligent_scorer.embed_ast_nodes", lambda *a, **k: None)

    (tmp_path / "a.ts").write_text("export function a() {}\n", encoding="utf-8")
    head = {"nodes": [{"id": "a.ts", "path": "a.ts", "type": "file"}], "edges": []}
    base = {"nodes": [], "edges": []}
    out = run_intelligent_scoring(
        "org-1", "repo-1", "o/r", head, base, ["a.ts"],
        head_repo_root=tmp_path, head_sha="abc",
    )
    assert out["ml_metadata"]["inference_mode"] == "gnn"
    assert out["ml_metadata"]["inference_ms"] == 42


def test_scoring_without_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without repo root, no AST parse happens; schema_version stays at 2."""
    monkeypatch.setattr("app.services.intelligent_scorer.load_org_model", lambda _oid: None)
    monkeypatch.setattr("app.services.intelligent_scorer.embed_ast_nodes", lambda *a, **k: None)
    head = {"nodes": [{"id": "a.ts"}], "edges": []}
    out = run_intelligent_scoring("org", "repo", "o/r", head, head, ["a.ts"])
    assert out["schema_version"] == 2
    assert out["ml_metadata"]["inference_mode"] == "uniform_fallback"


def test_scoring_ast_failure_graceful(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """AST parse failure should not crash; falls back gracefully."""
    monkeypatch.setattr("app.services.intelligent_scorer.load_org_model", lambda _oid: None)
    monkeypatch.setattr("app.services.intelligent_scorer.embed_ast_nodes", lambda *a, **k: None)
    monkeypatch.setattr(
        "app.services.intelligent_scorer.build_ast_graph",
        lambda _p: (_ for _ in ()).throw(RuntimeError("parse failed")),
    )
    head = {"nodes": [{"id": "a.ts"}], "edges": []}
    out = run_intelligent_scoring(
        "org", "repo", "o/r", head, head, ["a.ts"],
        head_repo_root=tmp_path, head_sha="abc",
    )
    assert out["schema_version"] == 2
    assert out["blast"] is not None


def test_scoring_schema_v3_with_ast_nodes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When AST produces nodes, schema_version should be 3 with changed_nodes."""
    monkeypatch.setattr("app.services.intelligent_scorer.load_org_model", lambda _oid: None)
    monkeypatch.setattr("app.services.intelligent_scorer.embed_ast_nodes", lambda *a, **k: None)

    (tmp_path / "a.ts").write_text(
        "import { x } from 'y';\nfunction foo() {}\n",
        encoding="utf-8",
    )
    head = {"nodes": [{"id": "a.ts"}], "edges": []}
    out = run_intelligent_scoring(
        "org", "repo", "o/r", head, head, ["a.ts"],
        head_repo_root=tmp_path, head_sha="abc",
    )
    assert out["schema_version"] == 3
    assert out["changed_nodes"] is not None
    assert len(out["changed_nodes"]) >= 1
    assert out["risk_anomalies"] is not None
