from pathlib import Path

from app.services.graph_builder import build_dependency_graph, diff_graph_edges


def test_build_graph_minimal_repo(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        '{"dependencies": {"react": "^18.0.0"}}',
        encoding="utf-8",
    )
    (tmp_path / "a.ts").write_text('import { x } from "./b";', encoding="utf-8")
    (tmp_path / "b.ts").write_text("export const x = 1;", encoding="utf-8")
    g = build_dependency_graph(tmp_path)
    assert any(e["target"] == "b.ts" for e in g["edges"] if e.get("source") == "a.ts")


def test_diff_graph_edges() -> None:
    base = {"edges": [{"source": "a", "target": "b", "type": "import"}]}
    head = {
        "edges": [
            {"source": "a", "target": "b", "type": "import"},
            {"source": "a", "target": "c", "type": "import"},
        ],
    }
    added, removed = diff_graph_edges(base, head)
    assert len(added) == 1 and added[0]["target"] == "c"
    assert removed == []
