"""Blast-radius from reverse dependency traversal (NetworkX)."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

import networkx as nx

from app.services.graph_builder import diff_graph_edges


def blast_radius_uniform_fallback(
    head_graph: dict[str, Any],
    changed_files: list[str],
    base_graph: dict[str, Any] | None = None,
    max_depth: int = 5,
    max_nodes: int = 200,
) -> dict[str, Any]:
    """
    Explicit uniform-edge reverse BFS (used when GNN/attention is unavailable).
    Same semantics as compute_blast_radius.
    """
    return compute_blast_radius(
        head_graph,
        changed_files,
        base_graph=base_graph,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )


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


def _ns(full_name: str, path: str) -> str:
    return f"{full_name}:{path}"


def _add_repo_file_edges(g: nx.DiGraph, full_name: str, graph: dict[str, Any]) -> int:
    n = 0
    for e in _file_edges(graph):
        g.add_edge(_ns(full_name, e[0]), _ns(full_name, e[1]))
        n += 1
    return n


def compute_cross_repo_blast_radius(
    changed_repo_full_name: str,
    changed_repo_id: str,
    head_graph: dict[str, Any],
    changed_files: list[str],
    cross_repo_edges: list[dict[str, Any]],
    consumer_graphs: dict[str, tuple[str, dict[str, Any]]],
    *,
    max_consumer_repos: int = 20,
    max_depth: int = 5,
    max_super_nodes: int = 50_000,
) -> dict[str, Any]:
    """
    Reverse BFS on a namespaced super-graph, including bridges from consumer importers
    to an anchor file in the changed repo so cross-repo reachability is modeled.

    consumer_graphs: repo_id -> (full_name, graph_json)
    """
    cross_repo_truncated = False
    if not changed_files:
        return {
            "cross_repo_impacts": [],
            "aggregate_cross_repo_score": 0,
            "cross_repo_truncated": False,
        }

    # Rank consumers by number of edges into this repo
    counts: dict[str, int] = {}
    for row in cross_repo_edges:
        if str(row.get("target_repo_id")) != changed_repo_id:
            continue
        sid = str(row.get("source_repo_id") or "")
        counts[sid] = counts.get(sid, 0) + 1
    ordered = sorted(counts.keys(), key=lambda r: (-counts[r], r))
    if len(ordered) > max_consumer_repos:
        cross_repo_truncated = True
        ordered = ordered[:max_consumer_repos]

    g = nx.DiGraph()
    edge_budget = 0
    edge_budget += _add_repo_file_edges(g, changed_repo_full_name, head_graph)
    for rid in ordered:
        entry = consumer_graphs.get(rid)
        if not entry:
            continue
        cname, cgraph = entry
        edge_budget += _add_repo_file_edges(g, cname, cgraph)

    anchor = sorted(changed_files)[0]
    anchor_ns = _ns(changed_repo_full_name, anchor)
    for row in cross_repo_edges:
        if str(row.get("target_repo_id")) != changed_repo_id:
            continue
        sid = str(row.get("source_repo_id") or "")
        if sid not in ordered:
            continue
        src = consumer_graphs.get(sid)
        if not src:
            continue
        cname, _ = src
        spath = str(row.get("source_path", ""))
        if not spath.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        g.add_edge(_ns(cname, spath), anchor_ns)
        edge_budget += 1

    if g.number_of_nodes() > max_super_nodes:
        cross_repo_truncated = True
        return {
            "cross_repo_impacts": [],
            "aggregate_cross_repo_score": 0,
            "cross_repo_truncated": True,
        }

    seeds: list[str] = []
    for f in changed_files:
        nid = _ns(changed_repo_full_name, f)
        if nid in g:
            seeds.append(nid)

    if not seeds:
        return {
            "cross_repo_impacts": [],
            "aggregate_cross_repo_score": 0,
            "cross_repo_truncated": cross_repo_truncated,
        }

    seen: set[str] = set()
    depth_map: dict[str, int] = {}
    q: deque[tuple[str, int]] = deque()
    for n in seeds:
        seen.add(n)
        depth_map[n] = 0
        q.append((n, 0))

    while q and len(seen) < max_super_nodes:
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

    by_repo: dict[str, list[tuple[str, int]]] = {}
    for node in seen:
        if ":" not in node:
            continue
        repo_name, path = node.split(":", 1)
        if repo_name == changed_repo_full_name:
            continue
        if not path.endswith((".ts", ".tsx", ".js", ".jsx")):
            continue
        by_repo.setdefault(repo_name, []).append((path, depth_map.get(node, 0)))

    impacts: list[dict[str, Any]] = []
    total_weight = 0.0
    name_to_id = {v[0]: k for k, v in consumer_graphs.items()}
    for repo_name, items in by_repo.items():
        paths = sorted({p for p, _ in items})
        weight = sum(1.0 / (1.0 + d) for _, d in items)
        total_weight += weight
        score = min(100, int(25 * math.log(1 + weight)))
        rid = name_to_id.get(repo_name, "")
        impacts.append(
            {
                "repo_id": rid,
                "repo_name": repo_name,
                "impacted_files": paths,
                "blast_score": score,
            },
        )

    agg = min(100, int(25 * math.log(1 + total_weight))) if total_weight else 0
    return {
        "cross_repo_impacts": sorted(impacts, key=lambda x: -x.get("blast_score", 0)),
        "aggregate_cross_repo_score": agg,
        "cross_repo_truncated": cross_repo_truncated,
    }
