# Improvements & Design Decisions

## Summary of changes
1. **Pinecone v2 SDK compatibility**: used `pinecone.Pinecone` and `pc.Index(...)` patterns. Created index if missing via `pc.create_index`.
2. **OpenAI vX client**: used `OpenAI(api_key=...)` for embeddings and chat completions.
3. **Embedding caching**: Added sqlite-backed cache (aio-sqlite) to avoid re-embedding identical texts, reducing cost and latency.
4. **Async parallelism**: Embeddings and graph fetches are parallelized (async + ThreadPoolExecutor for blocking DB calls).
5. **Router agent**: Simple intent classification to vary answer style (itinerary vs factual).
6. **Reranking**: Combined vector score with graph proximity boost to prefer items that are both semantically relevant and graph-connected.
7. **Summarizer**: Summarized top nodes before final answer to give concise context.
8. **Prompt engineering**: Chain-of-thought style short reasoning followed by concise answer; instruct model to cite node ids.
9. **Modularity**: Clear separation: embed cache, pinecone, neo4j, reranker, prompt builder, server.

## Why these choices
- Caching reduces cost and speeds iterative development.
- Async + batching improves throughput and scales to larger datasets.
- Graph signals increase factuality, improving user trust.
- Reranking combines strengths of both stores (semantic + structured).

## Future improvements (bonus ideas)
- Full streaming LLM output (SSE / WebSocket)
- Multi-lingual embeddings & reranking per language
- Automatic index partitioning & sharding for 1M+ nodes
- Robust unit tests and CI integration

