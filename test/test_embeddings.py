import asyncio
from hybrid_chat import embed_text

def test_embedding_length():
    vec = asyncio.run(embed_text("hello world"))
    assert isinstance(vec, list)
    assert len(vec) > 100
