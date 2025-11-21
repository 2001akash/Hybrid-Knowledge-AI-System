# import os
# from dotenv import load_dotenv

# load_dotenv()

# # Neo4j Configuration
# NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
# NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
# NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# # Pinecone Configuration
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "travel-docs")
# PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")

# # OpenAI Configuration
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
# OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

# # Validate required configurations
# def validate_config():
#     """Validate that all required config values are set"""
#     required = {
#         "NEO4J_PASSWORD": NEO4J_PASSWORD,
#         "PINECONE_API_KEY": PINECONE_API_KEY,
#         "OPENAI_API_KEY": OPENAI_API_KEY
#     }
    
#     missing = [k for k, v in required.items() if not v]
    
#     if missing:
#         raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
#     return True

# if __name__ == "__main__":
#     try:
#         validate_config()
#         print("✅ All configurations are valid!")
#     except ValueError as e:
#         print(f"❌ Configuration error: {e}")