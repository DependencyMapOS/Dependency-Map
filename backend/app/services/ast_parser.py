"""Layer 1: tree-sitter AST graph (TS/JS/TSX/JSX)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.services.graph_builder import SKIP_DIR_PARTS, SOURCE_EXTS
from app.services.tree_sitter_languages import parser_for_suffix


def _iter_source_files(repo_root: Path) -> list[str]:
    out: list[str] = []
    root = repo_root.resolve()
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in SOURCE_EXTS:
            continue
        if any(part in SKIP_DIR_PARTS for part in p.parts):
            continue
        out.append(p.relative_to(root).as_posix())
    return sorted(out)


def _walk_imports_and_funcs(
    root_node,
    rel: str,
    source: bytes,
    nodes: list[dict[str, Any]],
    _edges: list[dict[str, Any]],
) -> None:
    stack = [root_node]
    while stack:
        node = stack.pop()
        stack.extend(node.children)
        t = node.type
        if t == "import_statement":
            text = source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
            nid = f"{rel}:{node.start_point[0] + 1}:import"
            nodes.append(
                {
                    "id": nid,
                    "kind": "import",
                    "name": "import",
                    "file": rel,
                    "line": node.start_point[0] + 1,
                    "code_snippet": (text.splitlines()[0][:200] if text else ""),
                    "exports": False,
                    "target_module": text,
                },
            )
        elif t in ("function_declaration", "method_definition", "arrow_function"):
            name = ""
            for ch in node.children:
                if ch.type == "identifier":
                    name = source[ch.start_byte : ch.end_byte].decode("utf-8", errors="ignore")
                    break
            line = node.start_point[0] + 1
            snippet = source[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
            snippet = "\n".join(snippet.splitlines()[:5])
            nid = f"{rel}:{line}:{name or 'anonymous'}"
            nodes.append(
                {
                    "id": nid,
                    "kind": "function",
                    "name": name or "anonymous",
                    "file": rel,
                    "line": line,
                    "code_snippet": snippet[:400],
                    "exports": False,
                },
            )


def build_ast_graph(repo_root: Path) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    root = repo_root.resolve()
    for rel in _iter_source_files(root):
        path = root / rel
        parser = parser_for_suffix(path.suffix)
        if parser is None:
            continue
        source_bytes = path.read_bytes()
        tree = parser.parse(source_bytes)
        _walk_imports_and_funcs(tree.root_node, rel, source_bytes, nodes, edges)

    files = {str(n.get("file")) for n in nodes if isinstance(n, dict) and n.get("file")}
    return {
        "nodes": nodes,
        "edges": edges,
        "file_count": len(files),
        "node_count": len(nodes),
        "edge_count": len(edges),
    }
