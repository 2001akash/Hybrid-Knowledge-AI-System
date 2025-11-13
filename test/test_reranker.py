from hybrid_chat import rerank

def test_reranker():
    matches = [
        {"id": "a", "score": 0.3, "metadata": {}},
        {"id": "b", "score": 0.2, "metadata": {}}
    ]
    facts = [{"id": "b"}]
    r = rerank(matches, facts)
    assert r[0]["id"] == "b"
