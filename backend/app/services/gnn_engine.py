"""Layer 3: GAT+GraphSAGE encoding via PyTorch Geometric (optional dependency)."""

from __future__ import annotations

import io
import logging
import time
from typing import Any

log = logging.getLogger(__name__)

_HAS_PYG = False
try:
    import torch
    import torch.nn.functional as F
    from torch import Tensor, nn
    from torch_geometric.data import Data
    from torch_geometric.nn import GATConv, SAGEConv

    _HAS_PYG = True
except ImportError:
    pass


if _HAS_PYG:

    class DependencyMapGNN(nn.Module):
        """Two-layer GAT (multi-head attention) followed by a GraphSAGE aggregation layer."""

        def __init__(
            self,
            in_dim: int = 1536,
            hidden_dim: int = 64,
            out_dim: int = 256,
            heads: int = 4,
            dropout: float = 0.3,
        ):
            super().__init__()
            self.proj = nn.Linear(in_dim, hidden_dim * heads)
            self.gat1 = GATConv(
                hidden_dim * heads, hidden_dim,
                heads=heads, concat=True, dropout=dropout,
            )
            self.gat2 = GATConv(
                hidden_dim * heads, hidden_dim,
                heads=heads, concat=True, dropout=dropout,
            )
            self.sage = SAGEConv(hidden_dim * heads, out_dim)
            self.dropout = dropout

        def forward(self, x: Tensor, edge_index: Tensor) -> tuple[Tensor, Tensor, Tensor]:
            """Returns (node_embeddings, attn_weights_layer1, attn_weights_layer2)."""
            h = self.proj(x)
            h, attn1 = self.gat1(h, edge_index, return_attention_weights=True)
            h = F.elu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)
            h, attn2 = self.gat2(h, edge_index, return_attention_weights=True)
            h = F.elu(h)
            h = F.dropout(h, p=self.dropout, training=self.training)
            h = self.sage(h, edge_index)
            return h, attn1[1], attn2[1]

    def _ast_graph_to_pyg(
        ast_graph: dict[str, Any], feature_dim: int = 1536,
    ) -> tuple[Data, list[str]]:
        """Convert ast_graph dict to a PyG Data object with dummy features if embeddings missing."""
        nodes = [n for n in (ast_graph.get("nodes") or []) if isinstance(n, dict)]
        edges = [e for e in (ast_graph.get("edges") or []) if isinstance(e, dict)]
        node_ids = [str(n.get("id", f"node_{i}")) for i, n in enumerate(nodes)]
        id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

        n = len(node_ids) or 1
        x = torch.randn(n, feature_dim) * 0.01

        for i, node in enumerate(nodes):
            emb = node.get("embedding")
            if isinstance(emb, list) and len(emb) == feature_dim:
                x[i] = torch.tensor(emb, dtype=torch.float32)

        src_list: list[int] = []
        tgt_list: list[int] = []
        for e in edges:
            s = id_to_idx.get(str(e.get("source", "")))
            t = id_to_idx.get(str(e.get("target", "")))
            if s is not None and t is not None:
                src_list.append(s)
                tgt_list.append(t)

        if not src_list:
            edge_index = torch.zeros((2, 0), dtype=torch.long)
        else:
            edge_index = torch.tensor([src_list, tgt_list], dtype=torch.long)

        data = Data(x=x, edge_index=edge_index)
        return data, node_ids

    def train_gnn(
        org_id: str,
        graphs: list[dict[str, Any]],
        *,
        feature_dim: int = 1536,
        epochs: int = 50,
        lr: float = 0.005,
        mask_ratio: float = 0.15,
    ) -> dict[str, Any]:
        """
        Self-supervised link prediction training: mask edges, train the model to predict them.
        Returns serialized state_dict bytes + metrics.
        """
        all_datas: list[Data] = []
        for g in graphs:
            data, _ = _ast_graph_to_pyg(g, feature_dim)
            if data.edge_index.size(1) >= 2:
                all_datas.append(data)

        if not all_datas:
            return {"org_id": org_id, "status": "no_data", "graphs": len(graphs)}

        model = DependencyMapGNN(in_dim=feature_dim)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        total_loss = 0.0
        model.train()
        for epoch in range(epochs):
            epoch_loss = 0.0
            for data in all_datas:
                num_edges = data.edge_index.size(1)
                num_mask = max(1, int(num_edges * mask_ratio))
                perm = torch.randperm(num_edges)
                mask_idx = perm[:num_mask]
                train_idx = perm[num_mask:]

                if train_idx.numel() == 0:
                    continue

                train_edge_index = data.edge_index[:, train_idx]
                masked_edges = data.edge_index[:, mask_idx]

                optimizer.zero_grad()
                emb, _, _ = model(data.x, train_edge_index)

                pos_src = emb[masked_edges[0]]
                pos_tgt = emb[masked_edges[1]]
                pos_score = (pos_src * pos_tgt).sum(dim=-1)

                neg_tgt_idx = torch.randint(0, emb.size(0), (num_mask,))
                neg_tgt = emb[neg_tgt_idx]
                neg_score = (pos_src * neg_tgt).sum(dim=-1)

                pos_loss = F.binary_cross_entropy_with_logits(
                    pos_score, torch.ones_like(pos_score),
                )
                neg_loss = F.binary_cross_entropy_with_logits(
                    neg_score, torch.zeros_like(neg_score),
                )
                loss = pos_loss + neg_loss
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            total_loss = epoch_loss

        buf = io.BytesIO()
        torch.save(model.state_dict(), buf)
        state_bytes = buf.getvalue()

        return {
            "org_id": org_id,
            "status": "trained",
            "graphs": len(graphs),
            "final_loss": round(total_loss, 4),
            "state_dict": state_bytes,
            "params": sum(p.numel() for p in model.parameters()),
        }

    def infer_gnn(
        ast_graph: dict[str, Any],
        state_dict_bytes: bytes,
        *,
        feature_dim: int = 1536,
    ) -> dict[str, Any]:
        """Run a forward pass with a trained checkpoint, return enriched embeddings + attention."""
        t0 = time.perf_counter()
        data, node_ids = _ast_graph_to_pyg(ast_graph, feature_dim)

        model = DependencyMapGNN(in_dim=feature_dim)
        buf = io.BytesIO(state_dict_bytes)
        model.load_state_dict(torch.load(buf, weights_only=True, map_location="cpu"))
        model.eval()

        with torch.no_grad():
            emb, attn1, attn2 = model(data.x, data.edge_index)

        avg_attn = ((attn1.mean() + attn2.mean()) / 2).item() if attn1.numel() > 0 else 0.0

        embeddings = {nid: emb[i].tolist() for i, nid in enumerate(node_ids) if i < emb.size(0)}
        edge_attention: dict[str, float] = {}
        if data.edge_index.size(1) > 0 and attn2.numel() > 0:
            for ei in range(data.edge_index.size(1)):
                si = data.edge_index[0, ei].item()
                ti = data.edge_index[1, ei].item()
                src_id = node_ids[si] if si < len(node_ids) else ""
                tgt_id = node_ids[ti] if ti < len(node_ids) else ""
                weight = (
                    attn2[ei].mean().item()
                    if ei < attn2.size(0) else avg_attn
                )
                edge_attention[f"{src_id}->{tgt_id}"] = round(weight, 4)

        return {
            "attention_valid": True,
            "enriched_embeddings": embeddings,
            "edge_attention": edge_attention,
            "inference_ms": int((time.perf_counter() - t0) * 1000),
        }


def infer_gnn_or_none(
    org_id: str,
    ast_graph: dict[str, Any],
    model_row: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """
    Returns dict with attention_valid=True when a trained checkpoint loads and runs.
    Otherwise None (caller must use blast_radius_uniform_fallback).
    """
    if not model_row or not model_row.get("state_dict"):
        return None
    if not _HAS_PYG:
        log.debug("infer_gnn_or_none: torch-geometric not installed; skip")
        return None
    try:
        state_bytes = model_row["state_dict"]
        if isinstance(state_bytes, memoryview):
            state_bytes = bytes(state_bytes)
        elif isinstance(state_bytes, str):
            import base64
            state_bytes = base64.b64decode(state_bytes)
        result = infer_gnn(ast_graph, state_bytes)
        return result
    except Exception:
        log.exception("GNN inference failed for org %s", org_id)
        return None


def train_link_prediction(org_id: str, graphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Train a GAT+GraphSAGE model on org code graphs via self-supervised link prediction."""
    if not _HAS_PYG:
        return {"org_id": org_id, "graphs": len(graphs), "status": "skipped_no_pyg"}
    if not graphs:
        return {"org_id": org_id, "graphs": 0, "status": "no_data"}
    return train_gnn(org_id, graphs)


def train_link_prediction_stub(org_id: str, graphs: list[dict[str, Any]]) -> dict[str, Any]:
    """Backwards-compatible alias that delegates to the real implementation when available."""
    return train_link_prediction(org_id, graphs)
