from app.services.blast_radius import compute_cross_repo_blast_radius


def test_compute_cross_repo_blast_radius_reaches_consumer() -> None:
    g_head = {
        "nodes": [
            {"id": "lib.ts", "path": "lib.ts", "type": "file"},
        ],
        "edges": [],
    }
    consumer_graph = {
        "nodes": [{"id": "client.ts", "path": "client.ts", "type": "file"}],
        "edges": [],
    }
    rid_a = "00000000-0000-0000-0000-0000000000aa"
    rid_b = "00000000-0000-0000-0000-0000000000bb"
    cross = [
        {
            "source_repo_id": rid_b,
            "target_repo_id": rid_a,
            "source_path": "client.ts",
            "target_package": "@pkg/a",
            "edge_type": "import",
            "branch": "main",
        },
    ]
    consumers = {rid_b: ("org/consumer", consumer_graph)}
    out = compute_cross_repo_blast_radius(
        "org/provider",
        rid_a,
        g_head,
        ["lib.ts"],
        cross,
        consumers,
        max_consumer_repos=20,
    )
    assert out["aggregate_cross_repo_score"] >= 0
    names = {i.get("repo_name") for i in out["cross_repo_impacts"]}
    assert "org/consumer" in names
