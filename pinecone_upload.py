# pinecone_upload.py  (Improved Version for Blue Enigma Evaluation)
import json
import time
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import config
import sys

# -----------------------------
# Config
# -----------------------------
DATA_FILE = "vietnam_travel_dataset.json"
BATCH_SIZE = 32

INDEX_NAME = config.PINECONE_INDEX_NAME
VECTOR_DIM = config.PINECONE_VECTOR_DIM  # 1536 for text-embedding-3-small
REGION = config.PINECONE_ENV  # should be "us-east4-gcp" or "us-west4-gcp" etc.

# -----------------------------
# Initialize clients
# -----------------------------
client = OpenAI(api_key=config.OPENAI_API_KEY)
pc = Pinecone(api_key=config.PINECONE_API_KEY)

# -----------------------------
# Validate Regions
# -----------------------------
VALID_REGIONS = ["us-east4-gcp", "us-west4-gcp", "eu-west1-gcp"]

if REGION not in VALID_REGIONS:
    print(f"❌ ERROR: Invalid Pinecone region: {REGION}")
    print(f"✔ Allowed: {VALID_REGIONS}")
    sys.exit()

# -----------------------------
# Create managed index if needed
# -----------------------------
existing_indexes = pc.list_indexes().names()

if INDEX_NAME not in existing_indexes:
    print(f"🚀 Creating Pinecone index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=VECTOR_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="gcp", region=REGION)
    )
    time.sleep(3)
else:
    print(f"✔ Index '{INDEX_NAME}' already exists")

index = pc.Index(INDEX_NAME)

# -----------------------------
# Helper Functions
# -----------------------------
def get_embeddings(texts, model=config.OPENAI_EMBEDDING_MODEL):
    """Generate embeddings using OpenAI v1.0+ API."""
    try:
        resp = client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]
    except Exception as e:
        print("❌ Embedding error:", e)
        return []

def chunked(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]

# -----------------------------
# Main Upload
# -----------------------------
def main():
    print("📥 Loading dataset:", DATA_FILE)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    items = []
    for node in nodes:
        semantic_text = node.get("semantic_text") or (node.get("description") or "")[:1000]
        if not semantic_text.strip():
            continue
        meta = {
            "id": node.get("id"),
            "type": node.get("type"),
            "name": node.get("name"),
            "city": node.get("city", node.get("region", "")),
            "tags": node.get("tags", [])
        }
        items.append((node["id"], semantic_text, meta))

    print(f"🧠 Total vector items prepared: {len(items)}")

    # -------------------------
    # Batch Upload
    # -------------------------
    for batch in tqdm(list(chunked(items, BATCH_SIZE)), desc="📤 Uploading to Pinecone"):
        ids = [item[0] for item in batch]
        texts = [item[1] for item in batch]
        metas = [item[2] for item in batch]

        # embeddings
        embeddings = get_embeddings(texts)

        # Validate dimension
        for vec in embeddings:
            if len(vec) != VECTOR_DIM:
                print(f"❌ ERROR: Embedding dimension mismatch: {len(vec)} vs {VECTOR_DIM}")
                sys.exit()

        vectors = [
            {"id": _id, "values": emb, "metadata": meta}
            for _id, emb, meta in zip(ids, embeddings, metas)
        ]

        # Upsert
        try:
            index.upsert(vectors, namespace="travel")
        except Exception as e:
            print("❌ Pinecone error:", e)
            time.sleep(1)
            try:
                index.upsert(vectors, namespace="travel")
            except:
                print("❌ Failed again. Stopping.")
                break

        print(f"✔ Batch uploaded: {len(vectors)} vectors")

        time.sleep(0.2)

    print("🎉 All items uploaded successfully!")
    print("📌 Check your Pinecone dashboard for vector count.")

# -----------------------------
if __name__ == "__main__":
    main()
