import os
import json
import glob
import time
import re
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI

# Load environment variables
load_dotenv()

# ============================
# CONFIG
# ============================
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "travel-docs")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large-oss")
DIMENSION = 3072  # ❗ Correct dimension for text-embedding-3-large-oss
REGION = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")

# ============================
# Initialize Clients
# ============================

# OSS-compatible OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1"
)

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

def initialize_index():
    """Create or connect to Pinecone index."""
    existing = [i.name for i in pc.list_indexes()]

    if INDEX_NAME not in existing:
        print(f"🚀 Creating Pinecone index: {INDEX_NAME}")
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=REGION)
        )
        time.sleep(2)

    return pc.Index(INDEX_NAME)


# ============================
# TEXT CHUNKING
# ============================
def chunk_text(text, max_chars=2000, overlap=200):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    L = len(text)

    while start < L:
        end = min(start + max_chars, L)
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


# ============================
# EMBEDDING FUNCTION
# ============================
def embed_text(text_list):
    """Generate embeddings using OSS model (FREE)."""
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text_list
        )
        return [item.embedding for item in response.data]

    except Exception as e:
        print("❌ Embedding Failed:", e)
        # ❗ Return empty list so we skip upload instead of pushing zeros
        return None


# ============================
# MAIN UPSERT FUNCTION
# ============================
def upsert_docs(folder="data/*.json"):
    index = initialize_index()
    files = glob.glob(folder)

    if not files:
        print("⚠️ No files found in data/")
        return

    print(f"📁 Found {len(files)} JSON files")

    total_vectors = 0

    for fpath in tqdm(files, desc="Processing files"):
        try:
            raw = open(fpath, "r", encoding="utf-8", errors="ignore").read()
            raw = re.sub(r'[\x00-\x1F\x7F]', ' ', raw)  # clean

            doc = json.loads(raw)
            text = doc.get("text", "").strip()

            if not text:
                print(f"⚠️ No text in {fpath}")
                continue

            chunks = chunk_text(text)

            embeddings = embed_text(chunks)
            if embeddings is None:
                print(f"❌ Skipping {fpath} due to embedding failure")
                continue

            upsert_data = []
            for i, (chunk, vec) in enumerate(zip(chunks, embeddings)):
                upsert_data.append({
                    "id": f"{os.path.basename(fpath).replace('.json','')}_{i}",
                    "values": vec,
                    "metadata": {
                        "source": fpath,
                        "chunk": chunk[:300]
                    }
                })

            index.upsert(vectors=upsert_data)
            total_vectors += len(upsert_data)

        except Exception as e:
            print(f"❌ Error in {fpath}: {e}")
            continue

    print(f"✅ Upload Complete — {total_vectors} vectors uploaded!")

    stats = index.describe_index_stats()
    print("📊 Pinecone Stats:", stats)


# ============================
# MAIN
# ============================
if __name__ == "__main__":
    upsert_docs()
