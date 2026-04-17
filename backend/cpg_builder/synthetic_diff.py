"""Build a minimal graph diff payload from PR changed files (no .git required)."""

from __future__ import annotations

from typing import Any

import networkx as nx


def synthetic_diff_payload_from_changed_files(
    graph: nx.MultiDiGraph,
    changed_files: list[str],
    *,
    max_nodes: int = 800,
) -> dict[str, Any]:
    """Map changed file paths to graph node ids for path_miner seeding.

    Used when the worker has a tarball checkout without git refs but GitHub
    compare already produced a changed-files list.
    """
    normalized = [p.replace("\\", "/").strip() for p in changed_files if p and str(p).strip()]
    if not normalized:
        return {"changed_files": [], "graph_diff": {"changed_nodes": []}}

    matched: list[str] = []
    for nid, attrs in graph.nodes(data=True):
        fp = attrs.get("file_path")
        if not fp:
            continue
        fp_norm = str(fp).replace("\\", "/")
        if _file_matches_changed(fp_norm, normalized):
            matched.append(str(nid))
            if len(matched) >= max_nodes:
                break

    changed_nodes = [{"before": {"id": nid}, "after": {"id": nid}} for nid in matched]
    return {
        "changed_files": normalized,
        "graph_diff": {
            "added_nodes": [],
            "removed_nodes": [],
            "changed_nodes": changed_nodes,
            "added_edges": [],
            "removed_edges": [],
            "changed_edges": [],
        },
    }


def _file_matches_changed(fp_norm: str, normalized: list[str]) -> bool:
    for cf in normalized:
        c = cf.lstrip("/")
        if fp_norm == cf or fp_norm == c or fp_norm.endswith("/" + c):
            return True
    return False
