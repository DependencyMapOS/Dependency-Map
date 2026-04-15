from app.services.embedding_engine import _hash_text, embed_with_codebert_fallback


def test_hash_text_stable() -> None:
    assert _hash_text("a") == _hash_text("a")
    assert _hash_text("a") != _hash_text("b")


def test_codebert_optional() -> None:
    out = embed_with_codebert_fallback(["a", "b"])
    assert out is None or isinstance(out, list)
