# config.py — fill values before running

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

OPENAI_API_KEY = "sk-replace"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_CHAT_MODEL = "gpt-4o-mini"

PINECONE_API_KEY = "pcsk-replace"
PINECONE_ENV = "us-east4-gcp"      # recommended region
PINECONE_INDEX_NAME = "vietnam-travel"
PINECONE_VECTOR_DIM = 1536         # matches embedding model dimension

BATCH_SIZE = 32
TOP_K = 6
EMBED_CACHE_DB = "embed_cache.db"
NEO4J_MAX_NEIGHBORS = 20
