import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI
import pinecone

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
pinecone.init(api_key=os.getenv("PINECONE_API_KEY"),
              environment=os.getenv("PINECONE_ENVIRONMENT"))
index = pinecone.Index(os.getenv("PINECONE_INDEX_NAME"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def neo4j_search(q):
    with driver.session() as s:
        res = s.run("""
            CALL db.index.fulltext.queryNodes('locationFullTextIndex', $q)
            YIELD node, score RETURN node.name AS name, node.description AS desc LIMIT 5
        """, {"q": q})
        return [dict(r) for r in res]

def pinecone_search(q, k=5):
    emb = openai_client.embeddings.create(
        model=os.getenv("OPENAI_EMBEDDING_MODEL"), input=q
    ).data[0].embedding
    res = index.query(vector=emb, top_k=k, include_metadata=True)
    return res.matches

def answer(q):
    neo_hits = neo4j_search(q)
    pine_hits = pinecone_search(q)
    context = "Facts:\n" + "\n".join(
        [f"{n['name']}: {n['desc']}" for n in neo_hits])
    context += "\n\nDocs:\n" + "\n".join(
        [m.metadata["preview"] for m in pine_hits])
    prompt = f"Question: {q}\n\n{context}\n\nAnswer briefly and accurately."
    resp = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_MODEL"),
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.choices[0].message.content

if __name__ == "__main__":
    q = input("Ask: ")
    print(answer(q))
