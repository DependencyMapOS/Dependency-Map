"""Layer 4: hybrid retrieval (vector + keyword + graph walk) via pgvector + tsvector."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

log = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for lst in ranked_lists:
        for rank, (node_id, _s) in enumerate(lst, start=1):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])


def _get_supabase():
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _vector_search(
    sb,
    repo_id: str,
    query_embedding: list[float],
    top_k: int,
) -> list[tuple[str, float]]:
    """Similarity search via pgvector cosine distance using an RPC function."""
    try:
        res = sb.rpc(
            "match_node_embeddings",
            {
                "query_embedding": query_embedding,
                "match_repo_id": repo_id,
                "match_threshold": 0.5,
                "match_count": top_k,
            },
        ).execute()
        rows = res.data or []
        return [(str(r["node_id"]), float(r.get("similarity", 0.0))) for r in rows]
    except Exception:
        log.exception("pgvector similarity search failed")
        return []


def _keyword_search(
    sb,
    repo_id: str,
    query_text: str,
    top_k: int,
) -> list[tuple[str, float]]:
    """Full-text search over node code snippets via Postgres tsvector."""
    try:
        res = sb.rpc(
            "keyword_search_nodes",
            {
                "search_query": query_text,
                "match_repo_id": repo_id,
                "match_count": top_k,
            },
        ).execute()
        rows = res.data or []
        return [(str(r["node_id"]), float(r.get("rank", 0.0))) for r in rows]
    except Exception:
        log.exception("keyword search failed")
        return []


def _graph_walk_search(
    sb,
    repo_id: str,
    seed_node_ids: list[str],
    top_k: int,
) -> list[tuple[str, float]]:
    """Walk AST graph edges from seed nodes (1-hop neighbors) and rank by connectivity."""
    if not seed_node_ids:
        return []
    try:
        res = (
            sb.table("ast_graph_snapshots")
            .select("graph_json")
            .eq("repo_id", repo_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data or not res.data[0].get("graph_json"):
            return []
        graph = res.data[0]["graph_json"]
        edges = [e for e in (graph.get("edges") or []) if isinstance(e, dict)]

        seed_set = set(seed_node_ids)
        neighbor_counts: dict[str, int] = {}
        for e in edges:
            s, t = str(e.get("source", "")), str(e.get("target", ""))
            if s in seed_set and t not in seed_set:
                neighbor_counts[t] = neighbor_counts.get(t, 0) + 1
            if t in seed_set and s not in seed_set:
                neighbor_counts[s] = neighbor_counts.get(s, 0) + 1

        ranked = sorted(neighbor_counts.items(), key=lambda x: -x[1])[:top_k]
        max_count = ranked[0][1] if ranked else 1
        return [(nid, count / max_count) for nid, count in ranked]
    except Exception:
        log.exception("graph walk search failed")
        return []


def _embed_query(query_text: str) -> list[float] | None:
    """Embed a query string using the same model as node embeddings."""
    if not settings.openai_api_key.strip():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=[query_text],
        )
        return list(resp.data[0].embedding)
    except Exception:
        log.exception("Query embedding failed")
        return None


def hybrid_retrieve(
    repo_id: str,
    query_text: str,
    query_embedding: list[float] | None = None,
    *,
    top_k: int = 20,
) -> list[dict[str, Any]]:
    """
    Hybrid retrieval combining vector similarity, keyword match, and graph walk.
    Falls back gracefully when DB or embeddings are unavailable.
    """
    sb = _get_supabase()
    if sb is None:
        return []

    if query_embedding is None:
        query_embedding = _embed_query(query_text)

    ranked_lists: list[list[tuple[str, float]]] = []

    if query_embedding:
        vec_results = _vector_search(sb, repo_id, query_embedding, top_k * 2)
        if vec_results:
            ranked_lists.append(vec_results)

    kw_results = _keyword_search(sb, repo_id, query_text, top_k * 2)
    if kw_results:
        ranked_lists.append(kw_results)

    if ranked_lists:
        top_seeds = [nid for nid, _ in ranked_lists[0][:5]]
        gw_results = _graph_walk_search(sb, repo_id, top_seeds, top_k)
        if gw_results:
            ranked_lists.append(gw_results)

    if not ranked_lists:
        return []

    fused = reciprocal_rank_fusion(ranked_lists)[:top_k]

    fused_ids = [nid for nid, _ in fused]
    node_details: dict[str, dict[str, Any]] = {}
    try:
        res = (
            sb.table("node_embeddings")
            .select("node_id,content_hash")
            .eq("repo_id", repo_id)
            .in_("node_id", fused_ids)
            .execute()
        )
        for r in res.data or []:
            node_details[str(r["node_id"])] = r
    except Exception:
        pass

    results: list[dict[str, Any]] = []
    for nid, score in fused:
        detail = node_details.get(nid, {})
        file_path = ""
        parts = nid.split(":")
        if len(parts) >= 2:
            file_path = parts[0]
        results.append({
            "node_id": nid,
            "score": round(score, 6),
            "file": file_path,
            "content_hash": detail.get("content_hash", ""),
        })

    return results
