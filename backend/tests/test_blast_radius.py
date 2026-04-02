from app.services.blast_radius import compute_blast_radius


def test_blast_radius_simple() -> None:
    head = {
        "nodes": [{"id": "a.ts"}, {"id": "b.ts"}],
        "edges": [{"source": "b.ts", "target": "a.ts", "type": "import"}],
    }
    out = compute_blast_radius(head, ["a.ts"], base_graph={"edges": []})
    assert "b.ts" in out["impacted_modules"]
    assert out["blast_radius_score"] >= 0
