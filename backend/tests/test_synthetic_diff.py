import networkx as nx

from cpg_builder.synthetic_diff import synthetic_diff_payload_from_changed_files


def test_synthetic_diff_maps_changed_files_to_nodes() -> None:
    g = nx.MultiDiGraph()
    g.add_node("n1", file_path="frontend/app/page.tsx", label="file")
    g.add_node("n2", file_path="backend/other.py", label="file")
    payload = synthetic_diff_payload_from_changed_files(g, ["frontend/app/page.tsx"])
    ids = {item["after"]["id"] for item in payload["graph_diff"]["changed_nodes"]}
    assert "n1" in ids
    assert "n2" not in ids
