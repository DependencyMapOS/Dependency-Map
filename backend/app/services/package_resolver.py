"""Published package discovery and cross-repo edge resolution."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _glob_packages(repo_root: Path, patterns: list[str]) -> list[Path]:
    roots: set[Path] = set()
    for pat in patterns:
        if not pat or pat.startswith("http"):
            continue
        for p in repo_root.glob(pat):
            if p.is_dir():
                pj = p / "package.json"
                if pj.is_file():
                    roots.add(p.resolve())
            elif p.name == "package.json" and p.is_file():
                roots.add(p.parent.resolve())
    return sorted(roots)


def extract_published_packages(repo_root: Path, branch: str = "main") -> list[dict[str, Any]]:
    """
    Collect package names published from this repo (root + workspace packages).
    Returns dicts: name, version, workspace_path (posix relative or None for root).
    """
    root = repo_root.resolve()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_pkg(pkg_path: Path) -> None:
        data = _read_json(pkg_path)
        name = str(data.get("name") or "").strip()
        if not name or name in seen:
            return
        ver = str(data.get("version") or "").strip()
        rel: str | None
        try:
            rel = pkg_path.parent.relative_to(root).as_posix() if pkg_path.parent != root else None
        except ValueError:
            rel = None
        seen.add(name)
        out.append(
            {
                "name": name,
                "version": ver,
                "workspace_path": rel,
                "branch": branch,
            },
        )

    add_pkg(root / "package.json")

    root_pkg = _read_json(root / "package.json")
    workspaces = root_pkg.get("workspaces")
    if isinstance(workspaces, list):
        for pkg_dir in _glob_packages(root, [str(x) for x in workspaces if x]):
            add_pkg(pkg_dir / "package.json")
    elif isinstance(workspaces, dict):
        pkgs = workspaces.get("packages") or []
        if isinstance(pkgs, list):
            for pkg_dir in _glob_packages(root, [str(x) for x in pkgs]):
                add_pkg(pkg_dir / "package.json")

    pnpm = root / "pnpm-workspace.yaml"
    if pnpm.is_file():
        text = pnpm.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"packages:\s*\n((?:\s*-\s*['\"]?[^\n]+['\"]?\s*\n)+)", text):
            block = m.group(1)
            for line in block.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    pat = line[2:].strip().strip("'\"")
                    for pkg_dir in _glob_packages(root, [pat]):
                        add_pkg(pkg_dir / "package.json")

    return out


def _bare_package_from_spec(spec: str) -> str | None:
    s = spec.strip()
    if s.startswith(".") or s.startswith("/"):
        return None
    if s.startswith("package:"):
        return s[len("package:") :].strip() or None
    return s or None


def resolve_cross_repo_edges(
    org_id: str,
    repo_graphs: dict[str, dict[str, Any]],
    _repo_meta: dict[str, dict[str, Any]],
    package_registry: dict[str, str],
    branch: str = "main",
) -> list[dict[str, Any]]:
    """
    For each repo graph, match edges targeting package:X to another repo in the org.

    repo_graphs: repo_id -> graph_json
    _repo_meta: reserved for future (e.g. scoped package namespaces)
    package_registry: published package name -> publishing repo_id
    """
    edges_out: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for source_repo_id, graph in repo_graphs.items():
        for e in graph.get("edges", []) or []:
            if not isinstance(e, dict):
                continue
            if str(e.get("type", "")) != "import":
                continue
            tgt = str(e.get("target", ""))
            if not tgt.startswith("package:"):
                continue
            pkg = _bare_package_from_spec(tgt)
            if not pkg:
                continue
            target_repo_id = package_registry.get(pkg)
            if not target_repo_id or target_repo_id == source_repo_id:
                continue
            src_path = str(e.get("source", ""))
            key = (source_repo_id, target_repo_id, src_path, pkg, branch)
            if key in seen:
                continue
            seen.add(key)
            edges_out.append(
                {
                    "org_id": org_id,
                    "source_repo_id": source_repo_id,
                    "target_repo_id": target_repo_id,
                    "source_path": src_path,
                    "target_package": pkg,
                    "edge_type": "import",
                    "branch": branch,
                },
            )
    return edges_out


def build_package_registry(repo_packages_rows: list[dict[str, Any]]) -> dict[str, str]:
    """Last writer wins for duplicate package names across repos."""
    reg: dict[str, str] = {}
    for row in repo_packages_rows:
        name = str(row.get("package_name") or "").strip()
        rid = str(row.get("repo_id") or "").strip()
        if name and rid:
            reg[name] = rid
    return reg
