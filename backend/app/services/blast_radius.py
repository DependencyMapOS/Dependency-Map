"""Blast-radius from reverse dependency traversal (NetworkX)."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

import networkx as nx

from app.services.graph_builder import diff_graph_edges


def _file_edges(graph: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for e in graph.get("edges", []):
        if not isinstance(e, dict):
            continue
        s, t = e.get("source"), e.get("target")
        if (
            isinstance(s, str)
            and isinstance(t, str)
            and s.endswith((".ts", ".tsx", ".js", ".jsx"))
            and t.endswith((".ts", ".tsx", ".js", ".jsx"))
        ):
            out.append((s, t))
    return out


def build_digraph(graph: dict[str, Any]) -> nx.DiGraph:
    g = nx.DiGraph()
    for e in _file_edges(graph):
        g.add_edge(e[0], e[1])
    return g


def compute_blast_radius(
    head_graph: dict[str, Any],
    changed_files: list[str],
    base_graph: dict[str, Any] | None = None,
    max_depth: int = 5,
    max_nodes: int = 200,
) -> dict[str, Any]:
    """
    Reverse BFS from changed files: who imports these files (transitively).
    """
    g = build_digraph(head_graph)
    added, removed = (
        diff_graph_edges(base_graph or {"edges": []}, head_graph)
        if base_graph is not None
        else ([], [])
    )

    seeds = [f for f in changed_files if f in g]

    if not seeds and not g.nodes:
        return {
            "impacted_modules": [],
            "blast_radius_score": 0,
            "confidence": "low",
            "risks": ["No graph nodes; repository may have no parseable TS/JS imports"],
            "changed_dependency_edges": [*added, *[{**e, "change": "removed"} for e in removed]],
        }

    # Edges are importer -> imported; importers are predecessors in the forward DiGraph.
    seen: set[str] = set()
    depth_map: dict[str, int] = {}
    q: deque[tuple[str, int]] = deque()
    for n in seeds:
        if n in g:
            seen.add(n)
            depth_map[n] = 0
            q.append((n, 0))

    while q and len(seen) < max_nodes:
        node, d = q.popleft()
        if d >= max_depth:
            continue
        for pred in g.predecessors(node):
            if pred in seen:
                continue
            nd = d + 1
            depth_map[pred] = nd
            seen.add(pred)
            q.append((pred, nd))

    impacted = sorted(seen, key=lambda x: depth_map.get(x, 0))
    weight_sum = sum(1.0 / (1.0 + depth_map.get(n, 0)) for n in impacted)
    score = min(100, int(25 * math.log(1 + weight_sum)))
    total_files = len([n for n in head_graph.get("nodes", []) if isinstance(n, dict)])
    confidence = "medium"
    if total_files < 5:
        confidence = "low"

    risks: list[str] = []
    if added:
        risks.append(f"{len(added)} new dependency edge(s)")
    if removed:
        risks.append(f"{len(removed)} removed dependency edge(s)")

    edge_changes: list[dict[str, str]] = [{**e, "change": "added"} for e in added]
    edge_changes.extend({**e, "change": "removed"} for e in removed)

    return {
        "impacted_modules": impacted[:max_nodes],
        "blast_radius_score": score,
        "confidence": confidence,
        "risks": risks or ["No major structural risks flagged"],
        "changed_dependency_edges": edge_changes,
    }


def stub_blast_summary() -> dict[str, Any]:
    return {
        "changed_files": [],
        "changed_dependency_edges": [],
        "impacted_modules": [],
        "blast_radius_score": 0,
        "confidence": "stub",
        "suggested_reviewers": [],
        "risks": ["Graph builder and CODEOWNERS not wired yet"],
    }
