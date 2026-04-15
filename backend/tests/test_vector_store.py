from app.services.vector_store import reciprocal_rank_fusion


def test_reciprocal_rank_fusion() -> None:
    fused = reciprocal_rank_fusion(
        [
            [("a", 1.0), ("b", 0.5)],
            [("b", 1.0), ("c", 0.2)],
        ],
    )
    assert fused[0][0] in {"a", "b", "c"}
