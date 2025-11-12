import os, json, glob
from tqdm import tqdm
from dotenv import load_dotenv
import pinecone
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pinecone.init(api_key=os.getenv("PINECONE_API_KEY"),
              environment=os.getenv("PINECONE_ENVIRONMENT"))

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
if INDEX_NAME not in pinecone.list_indexes():
    pinecone.create_index(INDEX_NAME, dimension=1536)
index = pinecone.Index(INDEX_NAME)

def chunk_text(text, max_chars=2000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def embed(texts):
    resp = client.embeddings.create(
        model=os.getenv("OPENAI_EMBEDDING_MODEL"),
        input=texts
    )
    return [r.embedding for r in resp.data]

def upsert_docs(folder="data/*.json"):
    files = glob.glob(folder)
    for fpath in tqdm(files):
        doc = json.load(open(fpath))
        text = doc["text"]
        title = doc.get("title", fpath)
        chunks = chunk_text(text)
        vectors = embed(chunks)
        batch = [
            (f"{os.path.basename(fpath)}_{i}", vectors[i],
             {"source": fpath, "chunk": i, "preview": chunks[i][:200]})
            for i in range(len(chunks))
        ]
        index.upsert(vectors=batch)
    print("✅ All documents embedded & upserted to Pinecone.")

if __name__ == "__main__":
    upsert_docs()
