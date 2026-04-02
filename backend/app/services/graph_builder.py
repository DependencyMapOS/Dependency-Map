"""Static TS/JS import graph (regex MVP)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FROM_IMPORT_RE = re.compile(
    r"""import\s+(?:type\s+)?(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?["']([^"']+)["']"""
)
EXPORT_FROM_RE = re.compile(r"""export\s+.*?from\s+["']([^"']+)["']""")
REQUIRE_RE = re.compile(r"""require\s*\(\s*["']([^"']+)["']\s*\)""")
DYNAMIC_IMPORT_RE = re.compile(r"""import\s*\(\s*["']([^"']+)["']\s*\)""")

SKIP_DIR_PARTS = frozenset(
    {"node_modules", ".git", "dist", "build", ".next", "coverage", "__pycache__"}
)
SOURCE_EXTS = frozenset({".ts", ".tsx", ".js", ".jsx"})


def _iter_source_files(repo_root: Path) -> list[str]:
    out: list[str] = []
    root = repo_root.resolve()
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix not in SOURCE_EXTS:
            continue
        if any(part in SKIP_DIR_PARTS for part in p.parts):
            continue
        rel = p.relative_to(root).as_posix()
        out.append(rel)
    return sorted(out)


def _resolve_relative(repo_root: Path, source_rel: str, spec: str) -> str | None:
    if not spec.startswith("."):
        return f"package:{spec}"
    src_path = repo_root / source_rel
    base_dir = src_path.parent
    target = (base_dir / spec).resolve()
    try:
        rel = target.relative_to(repo_root.resolve())
    except ValueError:
        return None
    stem = rel.as_posix()
    candidates = [
        stem,
        f"{stem}.ts",
        f"{stem}.tsx",
        f"{stem}.js",
        f"{stem}.jsx",
        f"{stem}/index.ts",
        f"{stem}/index.tsx",
        f"{stem}/index.js",
        f"{stem}/index.jsx",
    ]
    for c in candidates:
        if (repo_root / c).is_file():
            return c
    return None


def _extract_specs(content: str) -> list[str]:
    specs: list[str] = []
    for rx in (FROM_IMPORT_RE, EXPORT_FROM_RE, REQUIRE_RE, DYNAMIC_IMPORT_RE):
        specs.extend(m.group(1) for m in rx.finditer(content))
    return specs


def build_dependency_graph(repo_root: Path) -> dict[str, Any]:
    """Build directed edge list: source file -> target file or package:spec."""
    root = repo_root.resolve()
    files = _iter_source_files(root)
    nodes = [{"id": r, "path": r, "type": "file"} for r in files]
    edges: list[dict[str, str]] = []
    file_set = set(files)

    pkg_path = root / "package.json"
    if pkg_path.is_file():
        try:
            data = json.loads(pkg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        dep_sections = (
            "dependencies",
            "devDependencies",
            "peerDependencies",
            "optionalDependencies",
        )
        for section in dep_sections:
            for name in (data.get(section) or {}):
                edges.append(
                    {"source": "package.json", "target": f"package:{name}", "type": "manifest"}
                )

    for rel in files:
        content = (root / rel).read_text(encoding="utf-8", errors="ignore")
        for spec in _extract_specs(content):
            tgt = _resolve_relative(root, rel, spec)
            if tgt and tgt in file_set:
                edges.append({"source": rel, "target": tgt, "type": "import"})
            elif tgt and tgt.startswith("package:"):
                edges.append({"source": rel, "target": tgt, "type": "import"})

    return {"nodes": nodes, "edges": edges}


def build_stub_graph() -> dict[str, Any]:
    return {"nodes": [], "edges": []}


def _edge_tuple(e: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(e.get("source", "")),
        str(e.get("target", "")),
        str(e.get("type", "")),
    )


def diff_graph_edges(
    base: dict[str, Any],
    head: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    base_edges = [e for e in base.get("edges", []) if isinstance(e, dict)]
    head_edges = [e for e in head.get("edges", []) if isinstance(e, dict)]
    bset = {_edge_tuple(e) for e in base_edges}
    hset = {_edge_tuple(e) for e in head_edges}
    added: list[dict[str, str]] = [
        {"source": t[0], "target": t[1], "type": t[2]} for t in (hset - bset)
    ]
    removed: list[dict[str, str]] = [
        {"source": t[0], "target": t[1], "type": t[2]} for t in (bset - hset)
    ]
    return added, removed
