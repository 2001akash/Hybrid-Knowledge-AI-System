import os
from dotenv import load_dotenv
from pinecone import Pinecone

# Load .env file
load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "vietnam-travel"

try:
    pc.delete_index(INDEX_NAME)
    print(f"✅ Deleted Pinecone index: {INDEX_NAME}")
except Exception as e:
    print(f"❌ Error deleting index: {e}")
