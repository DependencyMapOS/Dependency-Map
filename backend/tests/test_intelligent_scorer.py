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
