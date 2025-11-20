import os
import json
import glob
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import time
import re

load_dotenv()

# Initialize clients
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "travel-docs")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DIMENSION = 1536  # text-embedding-3-small dimension

def initialize_index():
    """Create or connect to Pinecone index"""
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if INDEX_NAME not in existing_indexes:
        print(f"Creating new index: {INDEX_NAME}")
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region=os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
            )
        )
        # Wait for index to be ready
        time.sleep(1)
    
    return pc.Index(INDEX_NAME)

def chunk_text(text, max_chars=2000, overlap=200):
    """Split text into overlapping chunks for better context retention"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + max_chars
        # Try to break at sentence boundary
        if end < text_len:
            # Look for period, question mark, or exclamation
            for i in range(end, max(start, end - 200), -1):
                if text[i] in '.!?\n':
                    end = i + 1
                    break
        
        chunks.append(text[start:end].strip())
        start = end - overlap if end < text_len else text_len
    
    return chunks

def embed(texts, batch_size=100):
    """Generate embeddings with batching and error handling"""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            resp = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch
            )
            all_embeddings.extend([r.embedding for r in resp.data])
        except Exception as e:
            print(f"Error embedding batch {i//batch_size}: {e}")
            # Retry with smaller batch or individual texts
            for text in batch:
                try:
                    resp = client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=text
                    )
                    all_embeddings.append(resp.data[0].embedding)
                except Exception as inner_e:
                    print(f"Failed to embed text: {inner_e}")
                    all_embeddings.append([0.0] * DIMENSION)
    
    return all_embeddings

def extract_metadata(doc, filepath):
    """Extract rich metadata from documents"""
    metadata = {
        "source": filepath,
        "title": doc.get("title", os.path.basename(filepath))
    }
    
    # Add location-specific metadata if available
    if "country" in doc:
        metadata["country"] = doc["country"]
    if "city" in doc:
        metadata["city"] = doc["city"]
    if "type" in doc:
        metadata["type"] = doc["type"]
    if "tags" in doc:
        metadata["tags"] = ",".join(doc["tags"]) if isinstance(doc["tags"], list) else doc["tags"]
    
    return metadata

def upsert_docs(folder="data/*.json", batch_size=100):
    """Load, chunk, embed and upload documents to Pinecone"""
    index = initialize_index()
    files = glob.glob(folder)
    
    if not files:
        print(f"⚠️  No files found matching pattern: {folder}")
        return
    
    print(f"Found {len(files)} files to process")
    total_chunks = 0
    
    for fpath in tqdm(files, desc="Processing files"):
        try:
            with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                raw = f.read()

            # Remove illegal control characters
            raw = re.sub(r'[\x00-\x1F\x7F]', ' ', raw)

            # Parse JSON safely
            doc = json.loads(raw)
            
            # Get text from document
            text = doc.get("text", "")
            if not text:
                print(f"⚠️  No text found in {fpath}")
                continue
            
            # Extract metadata
            base_metadata = extract_metadata(doc, fpath)
            
            # Chunk the text
            chunks = chunk_text(text)
            
            # Generate embeddings
            vectors = embed(chunks)
            
            # Prepare vectors for upsert
            batch = []
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                vector_id = f"{os.path.basename(fpath).replace('.json', '')}_{i}"
                metadata = base_metadata.copy()
                metadata.update({
                    "chunk_id": i,
                    "chunk_text": chunk[:500],  # Store preview
                    "full_chunk": chunk  # Store full chunk for retrieval
                })
                batch.append((vector_id, vector, metadata))
            
            # Upsert in batches
            for i in range(0, len(batch), batch_size):
                batch_slice = batch[i:i + batch_size]
                index.upsert(vectors=batch_slice)
            
            total_chunks += len(chunks)
            
        except Exception as e:
            print(f"❌ Error processing {fpath}: {e}")
            continue
    
    print(f"✅ Successfully uploaded {total_chunks} chunks from {len(files)} documents to Pinecone")
    
    # Print index stats
    stats = index.describe_index_stats()
    print(f"📊 Index stats: {stats}")

if __name__ == "__main__":
    upsert_docs()