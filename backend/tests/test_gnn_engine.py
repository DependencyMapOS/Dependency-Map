from app.services.gnn_engine import infer_gnn_or_none, train_link_prediction_stub


def test_infer_gnn_without_model() -> None:
    assert infer_gnn_or_none("org", {"nodes": [], "edges": []}, None) is None


def test_train_stub() -> None:
    out = train_link_prediction_stub("org", [])
    assert out["status"] == "skipped"
