"""Tests for Layer 3: GAT+GraphSAGE GNN engine."""

from __future__ import annotations

import pytest

from app.services.gnn_engine import (
    _HAS_PYG,
    infer_gnn_or_none,
    train_link_prediction,
    train_link_prediction_stub,
)


def test_infer_gnn_without_model() -> None:
    assert infer_gnn_or_none("org", {"nodes": [], "edges": []}, None) is None


def test_infer_gnn_empty_state_dict() -> None:
    assert infer_gnn_or_none("org", {"nodes": [], "edges": []}, {"state_dict": None}) is None
    assert infer_gnn_or_none("org", {"nodes": [], "edges": []}, {"state_dict": b""}) is None


def test_train_no_graphs() -> None:
    out = train_link_prediction("org", [])
    assert out["status"] in {"no_data", "skipped_no_pyg"}
    assert out["graphs"] == 0


def test_train_stub_backwards_compat() -> None:
    out = train_link_prediction_stub("org", [])
    assert out["status"] in {"no_data", "skipped_no_pyg"}


@pytest.mark.skipif(not _HAS_PYG, reason="torch-geometric not installed")
class TestWithPyG:

    def test_train_simple_graph(self) -> None:
        graph = {
            "nodes": [
                {
                    "id": "a.ts:1:import", "kind": "import",
                    "name": "import", "file": "a.ts",
                    "line": 1, "code_snippet": "import x",
                },
                {
                    "id": "a.ts:3:foo", "kind": "function",
                    "name": "foo", "file": "a.ts",
                    "line": 3, "code_snippet": "function foo()",
                },
                {
                    "id": "b.ts:1:bar", "kind": "function",
                    "name": "bar", "file": "b.ts",
                    "line": 1, "code_snippet": "function bar()",
                },
                {
                    "id": "b.ts:5:baz", "kind": "function",
                    "name": "baz", "file": "b.ts",
                    "line": 5, "code_snippet": "function baz()",
                },
            ],
            "edges": [
                {"source": "a.ts:1:import", "target": "b.ts:1:bar"},
                {"source": "a.ts:3:foo", "target": "b.ts:1:bar"},
                {"source": "b.ts:1:bar", "target": "b.ts:5:baz"},
            ],
        }
        result = train_link_prediction("test-org", [graph])
        assert result["status"] == "trained"
        assert result["final_loss"] >= 0
        assert isinstance(result["state_dict"], bytes)
        assert len(result["state_dict"]) > 0
        assert result["params"] > 0

    def test_train_multiple_graphs(self) -> None:
        g1 = {
            "nodes": [
                {"id": "a:1:f", "kind": "function"},
                {"id": "a:2:g", "kind": "function"},
                {"id": "a:3:h", "kind": "function"},
            ],
            "edges": [
                {"source": "a:1:f", "target": "a:2:g"},
                {"source": "a:2:g", "target": "a:3:h"},
            ],
        }
        g2 = {
            "nodes": [
                {"id": "b:1:x", "kind": "function"},
                {"id": "b:2:y", "kind": "function"},
            ],
            "edges": [
                {"source": "b:1:x", "target": "b:2:y"},
                {"source": "b:2:y", "target": "b:1:x"},
            ],
        }
        result = train_link_prediction("test-org", [g1, g2])
        assert result["status"] == "trained"
        assert result["graphs"] == 2

    def test_train_then_infer(self) -> None:
        graph = {
            "nodes": [
                {"id": "x:1:a", "kind": "function", "name": "a", "file": "x.ts"},
                {"id": "x:2:b", "kind": "function", "name": "b", "file": "x.ts"},
                {"id": "y:1:c", "kind": "function", "name": "c", "file": "y.ts"},
            ],
            "edges": [
                {"source": "x:1:a", "target": "x:2:b"},
                {"source": "x:2:b", "target": "y:1:c"},
            ],
        }
        train_result = train_link_prediction("test-org", [graph])
        assert train_result["status"] == "trained"

        model_row = {"state_dict": train_result["state_dict"]}
        infer_result = infer_gnn_or_none("test-org", graph, model_row)
        assert infer_result is not None
        assert infer_result["attention_valid"] is True
        assert "enriched_embeddings" in infer_result
        assert "edge_attention" in infer_result
        assert infer_result["inference_ms"] >= 0
        assert len(infer_result["enriched_embeddings"]) == 3

    def test_train_graph_too_few_edges(self) -> None:
        graph = {
            "nodes": [{"id": "a:1:f", "kind": "function"}],
            "edges": [{"source": "a:1:f", "target": "a:1:f"}],
        }
        result = train_link_prediction("test-org", [graph])
        assert result["status"] in {"trained", "no_data"}

    def test_infer_corrupt_state_dict(self) -> None:
        result = infer_gnn_or_none(
            "org",
            {"nodes": [{"id": "n"}], "edges": []},
            {"state_dict": b"not-a-valid-pytorch-checkpoint"},
        )
        assert result is None

    def test_model_architecture_params(self) -> None:
        from app.services.gnn_engine import DependencyMapGNN

        model = DependencyMapGNN(in_dim=64, hidden_dim=16, out_dim=32, heads=2)
        total_params = sum(p.numel() for p in model.parameters())
        assert total_params > 0

        import torch
        x = torch.randn(5, 64)
        edge_index = torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.long)
        emb, attn1, attn2 = model(x, edge_index)
        assert emb.shape == (5, 32)
