import json
from pathlib import Path

from app.services.package_resolver import (
    build_package_registry,
    extract_published_packages,
    resolve_cross_repo_edges,
)


def test_extract_published_packages_workspace(tmp_path: Path) -> None:
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "a").mkdir()
    root_pkg = {
        "name": "root",
        "version": "1.0.0",
        "workspaces": ["packages/*"],
    }
    (tmp_path / "package.json").write_text(json.dumps(root_pkg), encoding="utf-8")
    pkg_a = {"name": "@acme/a", "version": "0.1.0"}
    (tmp_path / "packages" / "a" / "package.json").write_text(json.dumps(pkg_a), encoding="utf-8")
    pkgs = extract_published_packages(tmp_path, branch="main")
    names = {p["name"] for p in pkgs}
    assert "root" in names
    assert "@acme/a" in names


def test_resolve_cross_repo_edges() -> None:
    org_id = "00000000-0000-0000-0000-000000000001"
    ra = "00000000-0000-0000-0000-0000000000a1"
    rb = "00000000-0000-0000-0000-0000000000b2"
    graph_a = {
        "nodes": [{"id": "src/x.ts", "path": "src/x.ts", "type": "file"}],
        "edges": [
            {"source": "src/x.ts", "target": "package:@acme/lib", "type": "import"},
        ],
    }
    graph_b = {"nodes": [], "edges": []}
    reg = build_package_registry(
        [
            {"repo_id": rb, "package_name": "@acme/lib", "branch": "main"},
        ],
    )
    edges = resolve_cross_repo_edges(
        org_id,
        {ra: graph_a, rb: graph_b},
        {ra: {"id": ra}, rb: {"id": rb}},
        reg,
        branch="main",
    )
    assert len(edges) == 1
    assert edges[0]["source_repo_id"] == ra
    assert edges[0]["target_repo_id"] == rb
    assert edges[0]["target_package"] == "@acme/lib"
