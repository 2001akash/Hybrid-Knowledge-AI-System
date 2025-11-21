import os
from neo4j import GraphDatabase
from groq import Groq
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import config1
from typing import List, Dict, Optional

# Initialize clients
driver = GraphDatabase.driver(
    config1.NEO4J_URI,
    auth=(config1.NEO4J_USER, config1.NEO4J_PASSWORD)
)
pc = Pinecone(api_key=config1.PINECONE_API_KEY)
index = pc.Index(config1.PINECONE_INDEX_NAME)

# Use Groq for chat (FREE!)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Use free local embedding model
print("📦 Loading embedding model...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("✅ Model ready!")

def neo4j_search(query: str, limit: int = 10) -> List[Dict]:
    """Search Neo4j knowledge graph"""
    with driver.session() as session:
        try:
            result = session.run("""
                CALL db.index.fulltext.queryNodes('entityFullTextIndex', $q)
                YIELD node, score
                RETURN node.id AS id,
                       node.name AS name, 
                       node.description AS description, 
                       node.type AS type,
                       labels(node) AS labels,
                       score
                ORDER BY score DESC
                LIMIT $limit
            """, {"q": query, "limit": limit})
            
            results = []
            for record in result:
                results.append({
                    "id": record["id"],
                    "name": record["name"],
                    "description": record["description"],
                    "type": record["type"],
                    "labels": record["labels"],
                    "score": record["score"]
                })
            
            return results
            
        except Exception as e:
            print(f"Neo4j search failed: {e}, using fallback")
            result = session.run("""
                MATCH (n:Entity)
                WHERE n.name CONTAINS $q 
                   OR n.description CONTAINS $q 
                   OR n.type CONTAINS $q
                RETURN n.id AS id,
                       n.name AS name, 
                       n.description AS description, 
                       n.type AS type,
                       labels(n) AS labels
                LIMIT $limit
            """, {"q": query, "limit": limit})
            
            return [dict(record) for record in result]

def get_entity_relationships(entity_id: str, limit: int = 5) -> List[Dict]:
    """Get relationships for a specific entity"""
    with driver.session() as session:
        result = session.run("""
            MATCH (e:Entity {id: $id})-[r]->(related:Entity)
            RETURN type(r) AS relationship,
                   related.name AS name,
                   related.type AS type,
                   related.description AS description
            LIMIT $limit
        """, {"id": entity_id, "limit": limit})
        
        return [dict(record) for record in result]

def pinecone_search(query: str, k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
    """Search Pinecone vector database using free local embeddings"""
    try:
        # Generate embedding locally (FREE!)
        emb = embedding_model.encode([query], show_progress_bar=False)[0].tolist()
        
        # Query Pinecone
        query_params = {
            "vector": emb,
            "top_k": k,
            "include_metadata": True
        }
        
        if filters:
            query_params["filter"] = filters
        
        res = index.query(**query_params)
        
        results = []
        for match in res.matches:
            results.append({
                "id": match.id,
                "score": match.score,
                "text": match.metadata.get("full_chunk", match.metadata.get("chunk_text", "")),
                "source": match.metadata.get("source", ""),
                "title": match.metadata.get("title", ""),
                "country": match.metadata.get("country", ""),
                "city": match.metadata.get("city", "")
            })
        
        return results
        
    except Exception as e:
        print(f"Pinecone search error: {e}")
        return []

def classify_query(query: str) -> str:
    """Classify query type"""
    query_lower = query.lower()
    
    if any(word in query_lower for word in ["itinerary", "trip", "plan", "days", "schedule"]):
        return "itinerary"
    
    if any(word in query_lower for word in ["recommend", "best", "top", "where to"]):
        return "recommendation"
    
    if any(word in query_lower for word in ["what is", "tell me about", "explain"]):
        return "factual"
    
    return "general"

def build_context(query: str, neo4j_results: List[Dict], pinecone_results: List[Dict]) -> str:
    """Build comprehensive context from both sources"""
    context_parts = []
    
    if neo4j_results:
        context_parts.append("=== Knowledge Graph Entities ===")
        for i, result in enumerate(neo4j_results[:5], 1):
            entity_info = f"{i}. {result.get('name', 'Unknown')}"
            if result.get('type'):
                entity_info += f" (Type: {result['type']})"
            if result.get('description'):
                entity_info += f"\n   {result['description']}"
            
            if result.get('id'):
                relationships = get_entity_relationships(result['id'], limit=3)
                if relationships:
                    entity_info += "\n   Connected to: "
                    entity_info += ", ".join([
                        f"{rel['name']} ({rel['relationship']})" 
                        for rel in relationships
                    ])
            
            context_parts.append(entity_info)
    
    if pinecone_results:
        context_parts.append("\n=== Detailed Travel Information ===")
        for i, result in enumerate(pinecone_results[:3], 1):
            doc_info = f"{i}. From {result.get('title', 'Travel Guide')}"
            if result.get('city') or result.get('country'):
                location = [result.get('city'), result.get('country')]
                doc_info += f" ({', '.join(filter(None, location))})"
            doc_info += f":\n   {result.get('text', '')[:400]}..."
            context_parts.append(doc_info)
    
    return "\n\n".join(context_parts)

def generate_answer_groq(query: str, context: str, query_type: str) -> str:
    """Generate answer using Groq (FREE!)"""
    
    system_prompts = {
        "itinerary": """You are an expert travel planner specializing in Vietnam. 
        Create detailed, romantic itineraries with specific locations, timing, and activities.""",
        
        "recommendation": """You are a knowledgeable travel advisor for Vietnam. 
        Provide specific recommendations with reasoning.""",
        
        "factual": """You are a Vietnam travel expert. 
        Provide accurate, informative answers based on the knowledge provided.""",
        
        "general": """You are a helpful Vietnam travel assistant. 
        Provide friendly, informative responses."""
    }
    
    system_prompt = system_prompts.get(query_type, system_prompts["general"])
    
    user_prompt = f"""Based on the following information, answer this question: {query}

{context}

Instructions:
- Use specific entity names and details from the knowledge graph
- Include relevant information from the travel guides
- Be specific about locations, activities, and timing
- If creating an itinerary, organize by days with morning/afternoon/evening activities
- Make the response engaging and helpful
"""
    
    try:
        # Use Groq's FREE API!
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Fast and free!
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating response: {e}"

def answer(query: str, verbose: bool = False) -> str:
    """Main function to answer queries using hybrid search"""
    
    query_type = classify_query(query)
    
    if verbose:
        print(f"\n🔍 Query type: {query_type}")
        print(f"📝 Processing: {query}\n")
    
    # Search both sources
    neo4j_results = neo4j_search(query, limit=10)
    pinecone_results = pinecone_search(query, k=5)
    
    if verbose:
        print(f"📊 Neo4j results: {len(neo4j_results)}")
        print(f"📊 Pinecone results: {len(pinecone_results)}\n")
    
    # Build context
    context = build_context(query, neo4j_results, pinecone_results)
    
    if verbose:
        print("📄 Context built, generating answer with Groq...\n")
    
    # Generate answer with Groq
    answer_text = generate_answer_groq(query, context, query_type)
    
    return answer_text

def interactive_chat():
    """Run interactive chat session"""
    print("=" * 70)
    print("🌏 Vietnam Travel Assistant - Powered by Groq (FREE!)")
    print("=" * 70)
    print("Ask me about Vietnam travel, itineraries, or recommendations!")
    print("Type 'quit' or 'exit' to end the session.\n")
    
    while True:
        try:
            query = input("You: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Happy travels! Goodbye!")
                break
            
            print("\n🤔 Thinking...\n")
            response = answer(query, verbose=True)
            print(f"\n✨ Assistant:\n{response}\n")
            print("-" * 70 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Happy travels! Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    test_query = "create a romantic 4 day itinerary for Vietnam"
    print(f"Testing with: '{test_query}'\n")
    result = answer(test_query, verbose=True)
    print(f"\n{'='*70}")
    print("ANSWER:")
    print('='*70)
    print(result)
    print('='*70)
    
    print("\n\nStarting interactive mode...\n")
    interactive_chat()