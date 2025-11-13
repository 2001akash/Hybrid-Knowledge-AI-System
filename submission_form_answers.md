Q: WHY USE BOTH PINECONE AND NEO4J INSTEAD OF ONLY ONE?
A: Pinecone (vector DB) provides semantic similarity for unstructured text; Neo4j provides precise relational facts (entities & relationships). Combining both gives both contextual richness and factual grounding, reducing hallucination and improving relevance.

Q: HOW WOULD YOU SCALE THIS TO 1M NODES?
A: Partition indices, use sharding/namespace strategies, shard graph across multiple clusters or use graph partitioning, use approximate nearest neighbor (ANN) backends with indexing (like HNSW), pre-compute embeddings and use incremental upserts, use caching and batch retrieval, and adopt async worker queues for ingestion.

Q: WHAT ARE THE FAILURE MODES OF HYBRID RETRIEVAL?
A: - Mismatch between semantic results and graph facts (contradictions)
- Stale embeddings (outdated content)
- API rate limits / cost spikes
- Over-reliance on poor metadata causing wrong reranking

Q: IF PINECONE API CHANGES AGAIN, HOW WOULD YOU DESIGN FOR FORWARD COMPATIBILITY?
A: Abstract DB client behind an interface, implement adapter pattern for Pinecone/other vector stores, centralize indexing/upsert/query logic, write unit tests & mocks, and use feature flags to toggle new API paths.
