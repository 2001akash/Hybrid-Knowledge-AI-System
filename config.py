import os
from dotenv import load_dotenv

load_dotenv()

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "vietnam-travel")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CHAT_MODEL = os.getenv("GROQ_CHAT_MODEL", "mixtral-8x7b-32768")   # Default
GROQ_EMBED_MODEL = os.getenv("GROQ_EMBED_MODEL", "all-MiniLM-L6-v2")   # Local embedding model

def validate_config():
    """Validate required configuration values."""
    required = {
        "NEO4J_PASSWORD": NEO4J_PASSWORD,
        "PINECONE_API_KEY": PINECONE_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY
    }

    missing = [k for k, v in required.items() if not v]

    if missing:
        raise ValueError(f"Missing required configuration variables: {', '.join(missing)}")

    return True


if __name__ == "__main__":
    try:
        validate_config()
        print(" All configurations are valid for Groq setup!")
    except ValueError as e:
        print(f" Configuration error: {e}")
