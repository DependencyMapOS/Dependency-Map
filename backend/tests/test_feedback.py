from app.services.feedback_engine import maybe_update_org_weights


def test_maybe_update_skips_without_supabase(monkeypatch) -> None:
    monkeypatch.setattr("app.services.feedback_engine.settings.supabase_url", "")
    out = maybe_update_org_weights("00000000-0000-0000-0000-000000000001")
    assert out["status"] == "skipped"
