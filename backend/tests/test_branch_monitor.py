from app.services.branch_monitor import compare_branch_graphs


def test_compare_branch_graphs_overlap() -> None:
    base = {
        "nodes": [{"id": "a.ts", "path": "a.ts", "type": "file"}],
        "edges": [{"source": "a.ts", "target": "b.ts", "type": "import"}],
    }
    head = {
        "nodes": [{"id": "a.ts", "path": "a.ts", "type": "file"}],
        "edges": [
            {"source": "a.ts", "target": "b.ts", "type": "import"},
            {"source": "b.ts", "target": "c.ts", "type": "import"},
        ],
    }
    out = compare_branch_graphs(base, head)
    assert 0.0 <= float(out["overlap_score"]) <= 1.0
    assert len(out["added_edges"]) >= 1
    assert out.get("drift_type")
