
from dotenv import load_dotenv
from pinecone import Pinecone
import os
# Force load .env file
load_dotenv(dotenv_path=".env")

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("vietnam-travel")

res = index.query(
    vector=[0]*384,      # dummy vector
    top_k=10,
    include_metadata=True
)

print([v["id"] for v in res["matches"]])

