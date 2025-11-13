from hybrid_chat import enrich_graph
import asyncio

def test_graph_fetch():
    facts = asyncio.run(enrich_graph(["hanoi_old_quarter"]))
    assert isinstance(facts, list)
