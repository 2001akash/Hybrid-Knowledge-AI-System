import os
import json
import glob
from tqdm import tqdm
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
import time
import gc

load_dotenv()

# Initialize clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "travel-docs")
DIMENSION = 384  # all-MiniLM-L6-v2 dimension

# Use free local embedding model instead of OpenAI
print("📦 Loading embedding model (one-time download)...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Free, fast, local
print("✅ Model loaded!")

# MEMORY OPTIMIZATION: Smaller batch sizes
EMBED_BATCH_SIZE = 20
UPSERT_BATCH_SIZE = 50
MAX_CHUNK_SIZE = 1500

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
        time.sleep(5)
    
    return pc.Index(INDEX_NAME)

def chunk_text(text, max_chars=MAX_CHUNK_SIZE, overlap=150):
    """Split text into smaller overlapping chunks"""
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + max_chars
        
        if end < text_len:
            # Find sentence boundary
            for i in range(end, max(start, end - 200), -1):
                if text[i] in '.!?\n':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap if end < text_len else text_len
    
    return chunks

def embed_with_local_model(texts, batch_size=EMBED_BATCH_SIZE):
    """Generate embeddings using free local model"""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        print(f"  Embedding batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}", end='\r')
        
        try:
            # Generate embeddings locally (FREE!)
            embeddings = embedding_model.encode(batch, show_progress_bar=False)
            all_embeddings.extend(embeddings.tolist())
            
        except Exception as e:
            print(f"\n  Error in batch {i//batch_size}: {e}")
            # Fallback: embed one by one
            for text in batch:
                try:
                    emb = embedding_model.encode([text], show_progress_bar=False)
                    all_embeddings.append(emb[0].tolist())
                except Exception as inner_e:
                    print(f"  Failed to embed text: {inner_e}")
                    all_embeddings.append([0.0] * DIMENSION)
        
        # Clear memory periodically
        if i % 50 == 0:
            gc.collect()
    
    print()
    return all_embeddings

def extract_metadata(doc, filepath):
    """Extract rich metadata from documents"""
    metadata = {
        "source": os.path.basename(filepath),
        "title": str(doc.get("title", os.path.basename(filepath)))[:200]
    }
    
    if "country" in doc:
        metadata["country"] = str(doc["country"])[:50]
    if "city" in doc:
        metadata["city"] = str(doc["city"])[:50]
    if "type" in doc:
        metadata["type"] = str(doc["type"])[:30]
    if "tags" in doc:
        tags = doc["tags"]
        if isinstance(tags, list):
            metadata["tags"] = ",".join(tags)[:200]
        else:
            metadata["tags"] = str(tags)[:200]
    
    return metadata

def process_file_streaming(fpath, index):
    """Process a single file with streaming to minimize memory usage"""
    print(f"\n📄 Processing: {os.path.basename(fpath)}")
    
    try:
        # Load JSON
        with open(fpath, 'r', encoding='utf-8') as f:
            doc = json.load(f)
        
        text = doc.get("text", "")
        if not text:
            print(f"  ⚠️  No text found, skipping")
            return 0
        
        print(f"  📏 Text length: {len(text)} characters")
        
        # Extract metadata
        base_metadata = extract_metadata(doc, fpath)
        
        # Chunk the text
        print(f"  ✂️  Chunking text...")
        chunks = chunk_text(text)
        print(f"  ✅ Created {len(chunks)} chunks")
        
        if not chunks:
            print(f"  ⚠️  No chunks created, skipping")
            return 0
        
        # Process in smaller sub-batches
        total_uploaded = 0
        chunk_batch_size = 20
        
        for batch_start in range(0, len(chunks), chunk_batch_size):
            batch_end = min(batch_start + chunk_batch_size, len(chunks))
            chunk_batch = chunks[batch_start:batch_end]
            
            print(f"  🔄 Processing chunks {batch_start+1}-{batch_end}/{len(chunks)}")
            
            # Generate embeddings (FREE with local model!)
            print(f"  🧠 Generating embeddings...")
            vectors = embed_with_local_model(chunk_batch)
            
            # Prepare vectors for upsert
            upsert_data = []
            for i, (chunk, vector) in enumerate(zip(chunk_batch, vectors)):
                chunk_idx = batch_start + i
                vector_id = f"{os.path.basename(fpath).replace('.json', '')}_{chunk_idx}"
                
                metadata = base_metadata.copy()
                metadata.update({
                    "chunk_id": chunk_idx,
                    "chunk_text": chunk[:400],
                    "full_chunk": chunk[:2000]
                })
                
                upsert_data.append((vector_id, vector, metadata))
            
            # Upsert to Pinecone
            print(f"  ⬆️  Uploading to Pinecone...")
            for i in range(0, len(upsert_data), UPSERT_BATCH_SIZE):
                batch_slice = upsert_data[i:i + UPSERT_BATCH_SIZE]
                index.upsert(vectors=batch_slice)
                time.sleep(0.2)
            
            total_uploaded += len(upsert_data)
            
            # Clear memory
            del vectors
            del upsert_data
            gc.collect()
            
            print(f"  ✅ Uploaded {total_uploaded}/{len(chunks)} chunks")
        
        # Final cleanup
        del chunks
        del doc
        gc.collect()
        
        print(f"  ✅ Successfully processed {total_uploaded} chunks")
        return total_uploaded
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

def upsert_docs(folder="data/*.json"):
    """Load, chunk, embed and upload documents to Pinecone"""
    
    files = glob.glob(folder)
    
    if not files:
        print(f"⚠️  No files found matching pattern: {folder}")
        return
    
    print(f"📁 Found {len(files)} JSON files")
    for f in files:
        print(f"  - {f} ({os.path.getsize(f) / 1024:.1f} KB)")
    
    # Initialize index
    print(f"\n🔧 Initializing Pinecone index: {INDEX_NAME}")
    index = initialize_index()
    print(f"✅ Index ready")
    
    # Process files one by one
    total_chunks = 0
    successful_files = 0
    
    for fpath in files:
        chunks_uploaded = process_file_streaming(fpath, index)
        total_chunks += chunks_uploaded
        if chunks_uploaded > 0:
            successful_files += 1
        gc.collect()
    
    # Print final stats
    print(f"\n{'='*60}")
    print(f"📊 Upload Summary")
    print(f"{'='*60}")
    print(f"  Files processed: {successful_files}/{len(files)}")
    print(f"  Total chunks uploaded: {total_chunks}")
    
    try:
        stats = index.describe_index_stats()
        print(f"  Pinecone index stats:")
        print(f"    - Total vectors: {stats.get('total_vector_count', 0)}")
        print(f"    - Dimension: {stats.get('dimension', 0)}")
    except Exception as e:
        print(f"  Could not retrieve index stats: {e}")
    
    print(f"{'='*60}")
    print(f"✅ Upload complete!")

if __name__ == "__main__":
    print("🚀 Starting Pinecone upload with FREE local embeddings")
    print("   Using: all-MiniLM-L6-v2 (384 dimensions)")
    print()
    
    upsert_docs()