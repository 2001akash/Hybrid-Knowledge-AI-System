"""
Advanced Hybrid RAG Agent
- async embedding + pinecone + neo4j
- embedding cache
- query intent router
- reranking algorithm
- summarization of nodes
- chain-of-thought style prompt
- itinerary generator
"""
import asyncio
import aiosqlite
from typing import List, Dict
from openai import OpenAI
from pinecone import Pinecone
from neo4j import GraphDatabase
import config
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor

client = OpenAI(api_key=config.OPENAI_API_KEY)
pc = Pinecone(api_key=config.PINECONE_API_KEY)
INDEX = pc.Index(config.PINECONE_INDEX_NAME)
driver = GraphDatabase.driver(config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
POOL = ThreadPoolExecutor(max_workers=6)

# -------------------------
# EMBEDDING CACHE
# -------------------------
async def ensure_cache():
    async with aiosqlite.connect(config.EMBED_CACHE_DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, vec BLOB)")
        await db.commit()

def hash_text(s: str):
    return hashlib.sha256(s.encode()).hexdigest()

async def cache_get(key: str):
    async with aiosqlite.connect(config.EMBED_CACHE_DB) as db:
        cur = await db.execute("SELECT vec FROM cache WHERE key=?", (key,))
        row = await cur.fetchone()
        if row:
            return pickle.loads(row[0])
    return None

async def cache_set(key: str, val):
    async with aiosqlite.connect(config.EMBED_CACHE_DB) as db:
        await db.execute("INSERT OR REPLACE INTO cache(key, vec) VALUES (?,?)", (key, pickle.dumps(val)))
        await db.commit()

async def embed_text(text: str):
    await ensure_cache()
    h = hash_text(text)
    cached = await cache_get(h)
    if cached:
        return cached
    resp = client.embeddings.create(model=config.OPENAI_EMBEDDING_MODEL, input=[text])
    vec = resp.data[0].embedding
    await cache_set(h, vec)
    return vec

# -------------------------
# INTENT ROUTER
# -------------------------
def classify_intent(q: str):
    ql = q.lower()
    if any(k in ql for k in ["itinerary", "plan", "day", "romantic"]):
        return "itinerary"
    if "best time" in ql or "weather" in ql:
        return "weather"
    return "generic"

# -------------------------
# PINECONE SEARCH
# -------------------------
async def search_pinecone(query: str):
    vec = await embed_text(query)
    result = INDEX.query(vector=vec, top_k=config.TOP_K, include_metadata=True)
    return [
        {"id": m.id, "score": getattr(m, "score", 0), "metadata": m.metadata}
        for m in result.matches
    ]

# -------------------------
# NEO4J ENRICHMENT
# -------------------------
def _neo4j_neighbors(ids: List[str]):
    facts = []
    with driver.session() as session:
        for nid in ids:
            q = """
            MATCH (n:Entity {id:$nid})-[r]-(m:Entity)
            RETURN type(r) as rel, m.id as id, m.name as name, m.description as description
            """
            res = session.run(q, nid=nid)
            for r in res:
                facts.append({
                    "src": nid,
                    "rel": r["rel"],
                    "id": r["id"],
                    "name": r["name"],
                    "desc": (r["description"] or "")[:350]
                })
    return facts

async def enrich_graph(ids: List[str]):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(POOL, _neo4j_neighbors, ids)

# -------------------------
# RERANKING SCORE
# -------------------------
def rerank(matches, facts):
    g_ids = set(f["id"] for f in facts)
    result = []
    for m in matches:
        boost = 0.15 if m["id"] in g_ids else 0
        final = m["score"] + boost
        result.append((final, m))
    result.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in result]

# -------------------------
# SUMMARIZER
# -------------------------
def summarize_nodes(nodes):
    text = "\n".join([
        f"{n['id']}: {n['metadata'].get('name')} ({n['metadata'].get('city')})"
        for n in nodes[:6]
    ])
    sys = "Summarize these travel nodes in 2–3 short sentences."
    resp = client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": text}
        ],
        max_tokens=120
    )
    return resp.choices[0].message.content

# -------------------------
# BUILD PROMPT
# -------------------------
def build_prompt(query, ranked, facts, intent):
    vec_lines = "\n".join([
        f"- {m['id']} | {m['metadata'].get('name')} | {m['metadata'].get('city')}"
        for m in ranked[:8]
    ])
    fact_lines = "\n".join([
        f"- ({f['src']}) -[{f['rel']}]-> ({f['id']}) {f['name']}: {f['desc']}"
        for f in facts[:20]
    ])
    system = (
        "You are an expert Vietnam travel assistant. Use vector results + graph facts. "
        "Provide practical, concise answers. Cite node ids when referencing attractions."
    )
    user = f"""
User query: {query}

Top matches:
{vec_lines}

Graph facts:
{fact_lines}

Intent: {intent}

Produce:
1. A short chain-of-thought reasoning (2 sentences).
2. Final answer with tips.
3. If itinerary: produce day-by-day plan.
"""
    return [{"role": "system", "content": system},
            {"role": "user", "content": user}]

# -------------------------
# MAIN ANSWER PIPELINE
# -------------------------
async def answer_query(query):
    intent = classify_intent(query)
    matches = await search_pinecone(query)
    ids = [m["id"] for m in matches]
    facts = await enrich_graph(ids)
    ranked = rerank(matches, facts)
    summary = summarize_nodes(ranked)

    prompt = build_prompt(query, ranked, facts, intent)
    resp = client.chat.completions.create(
        model=config.OPENAI_CHAT_MODEL,
        messages=prompt,
        max_tokens=600
    )
    return {
        "summary": summary,
        "answer": resp.choices[0].message.content,
        "matches": ranked[:6],
        "facts": facts[:12]
    }

# -------------------------
# CLI
# -------------------------
def cli():
    loop = asyncio.get_event_loop()
    print("🌏 Advanced Hybrid Travel Assistant. Type 'exit' to quit.")
    while True:
        q = input("\nQuery: ").strip()
        if q.lower() in ["exit", "quit"]:
            break
        out = loop.run_until_complete(answer_query(q))
        print("\n=== SUMMARY ===\n", out["summary"])
        print("\n=== ANSWER ===\n", out["answer"])
        print("\n---")

if __name__ == "__main__":
    cli()
