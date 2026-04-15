"""Branch graph comparison, drift signals, merge risk."""

from __future__ import annotations

from typing import Any

from app.services.graph_builder import diff_graph_edges


def _edge_set(graph: dict[str, Any]) -> set[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for e in graph.get("edges", []) or []:
        if not isinstance(e, dict):
            continue
        out.add(
            (
                str(e.get("source", "")),
                str(e.get("target", "")),
                str(e.get("type", "")),
            ),
        )
    return out


def compare_branch_graphs(graph_a: dict[str, Any], graph_b: dict[str, Any]) -> dict[str, Any]:
    added, removed = diff_graph_edges(graph_a, graph_b)
    set_a = _edge_set(graph_a)
    set_b = _edge_set(graph_b)
    shared = set_a & set_b
    total_unique = len(set_a | set_b)
    overlap_score = (len(shared) / total_unique) if total_unique else 1.0

    def _node_ids(graph: dict[str, Any]) -> set[str]:
        out: set[str] = set()
        for n in graph.get("nodes") or []:
            if isinstance(n, dict):
                out.add(str(n.get("id", n.get("path", ""))))
        return out

    nodes_a = _node_ids(graph_a)
    nodes_b = _node_ids(graph_b)
    file_delta = len(nodes_a.symmetric_difference(nodes_b))

    edge_change_ratio = (len(added) + len(removed)) / max(1, total_unique)
    manifest_changed = any(
        str(e.get("type")) == "manifest" for e in [*added, *removed] if isinstance(e, dict)
    )

    if edge_change_ratio > 0.2:
        drift_type = "structural"
    elif manifest_changed:
        drift_type = "dependency"
    elif file_delta > 0:
        drift_type = "file-level"
    else:
        drift_type = "structural" if added or removed else "file-level"

    added_files = {str(e.get("source")) for e in added if isinstance(e, dict)}
    removed_files = {str(e.get("source")) for e in removed if isinstance(e, dict)}
    conflicting_files = sorted(added_files & removed_files)

    drift_signal = {
        "overlap_score": round(overlap_score, 4),
        "added_edges": added,
        "removed_edges": removed,
        "drift_type": drift_type,
        "conflicting_files": conflicting_files,
        "merge_risk": "low",
        "risk_summary": "",
    }
    drift_signal.update(detect_merge_risk(drift_signal))
    return drift_signal


def detect_merge_risk(drift_signal: dict[str, Any]) -> dict[str, Any]:
    overlap = float(drift_signal.get("overlap_score") or 0.0)
    conflicting = drift_signal.get("conflicting_files") or []
    n_conf = len(conflicting) if isinstance(conflicting, list) else 0
    if overlap < 0.7 and n_conf > 10:
        level = "high"
    elif overlap < 0.85 and n_conf > 5:
        level = "medium"
    else:
        level = "low"
    summary = (
        f"Feature branch vs base: overlap={overlap:.2f}, "
        f"{n_conf} file(s) with overlapping edge churn"
    )
    return {"merge_risk": level, "risk_summary": summary}


def compute_drift_signals(
    graph_a: dict[str, Any],
    graph_b: dict[str, Any],
    *,
    base_sha: str,
    head_sha: str,
) -> dict[str, Any]:
    """Diff two graphs and attach resolved SHAs for persistence."""
    sig = compare_branch_graphs(graph_a, graph_b)
    sig["base_sha"] = base_sha
    sig["head_sha"] = head_sha
    return sig
