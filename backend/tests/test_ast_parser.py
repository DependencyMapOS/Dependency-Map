from pathlib import Path

from app.services.ast_parser import build_ast_graph


def test_build_ast_graph_on_typescript(tmp_path: Path) -> None:
    (tmp_path / "hello.ts").write_text(
        "import { x } from 'other';\nexport function foo() { return 1; }\n",
        encoding="utf-8",
    )
    g = build_ast_graph(tmp_path)
    assert g["node_count"] >= 1
