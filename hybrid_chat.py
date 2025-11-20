import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI
from pinecone import Pinecone
import re
from typing import List, Dict, Tuple

load_dotenv()

# Initialize clients
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index(os.getenv("PINECONE_INDEX_NAME", "travel-docs"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

def extract_entities(query: str) -> Dict[str, List[str]]:
    """Extract key entities from query using simple pattern matching"""
    entities = {
        "countries": [],
        "cities": [],
        "types": [],
        "keywords": []
    }
    
    # Common travel-related keywords
    location_types = [
        "restaurant", "hotel", "museum", "beach", "park", "temple", 
        "market", "cafe", "bar", "landmark", "attraction", "monument"
    ]
    
    query_lower = query.lower()
    
    # Extract location types
    for loc_type in location_types:
        if loc_type in query_lower:
            entities["types"].append(loc_type)
    
    # Extract potential location names (capitalized words)
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
    entities["keywords"].extend(words)
    
    return entities

def neo4j_search(query: str, limit: int = 5) -> List[Dict]:
    """Search Neo4j knowledge graph using full-text search"""
    with driver.session() as s:
        try:
            # Try full-text search first
            res = s.run("""
                CALL db.index.fulltext.queryNodes('locationFullTextIndex', $q)
                YIELD node, score 
                MATCH (node)-[:IN_COUNTRY]->(c:Country)
                RETURN node.name AS name, 
                       node.description AS description, 
                       node.type AS type,
                       c.name AS country,
                       node.rating AS rating,
                       score
                ORDER BY score DESC
                LIMIT $limit
            """, {"q": query, "limit": limit})
            
            results = []
            for record in res:
                results.append({
                    "name": record["name"],
                    "description": record["description"],
                    "type": record["type"],
                    "country": record["country"],
                    "rating": record["rating"],
                    "score": record["score"]
                })
            
            return results
            
        except Exception as e:
            print(f"Neo4j search error: {e}")
            # Fallback to simple pattern matching
            res = s.run("""
                MATCH (l:Location)-[:IN_COUNTRY]->(c:Country)
                WHERE l.name CONTAINS $q OR l.description CONTAINS $q OR c.name CONTAINS $q
                RETURN l.name AS name, 
                       l.description AS description, 
                       l.type AS type,
                       c.name AS country,
                       l.rating AS rating
                LIMIT $limit
            """, {"q": query, "limit": limit})
            
            return [dict(record) for record in res]

def get_locations_by_country(country: str, limit: int = 10) -> List[Dict]:
    """Get top locations in a specific country"""
    with driver.session() as s:
        res = s.run("""
            MATCH (l:Location)-[:IN_COUNTRY]->(c:Country {name: $country})
            RETURN l.name AS name, 
                   l.description AS description, 
                   l.type AS type,
                   l.rating AS rating
            ORDER BY l.rating DESC
            LIMIT $limit
        """, {"country": country, "limit": limit})
        
        return [dict(record) for record in res]

def pinecone_search(query: str, k: int = 5, filters: Dict = None) -> List[Dict]:
    """Search Pinecone vector database"""
    try:
        emb = openai_client.embeddings.create(
            model=EMBEDDING_MODEL, 
            input=query
        ).data[0].embedding
        
        # Apply filters if provided
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
                "title": match.metadata.get("title", "")
            })
        
        return results
        
    except Exception as e:
        print(f"Pinecone search error: {e}")
        return []

def determine_query_type(query: str) -> str:
    """Classify query to determine best retrieval strategy"""
    query_lower = query.lower()
    
    # Itinerary planning queries
    if any(word in query_lower for word in ["itinerary", "trip", "plan", "days", "visit", "travel to"]):
        return "itinerary"
    
    # Specific location queries
    if any(word in query_lower for word in ["where", "find", "recommend", "best", "top"]):
        return "recommendation"
    
    # Factual queries
    if any(word in query_lower for word in ["what", "who", "when", "how", "why"]):
        return "factual"
    
    return "general"

def build_context(query: str, neo4j_results: List[Dict], pinecone_results: List[Dict]) -> str:
    """Build comprehensive context from both sources"""
    context_parts = []
    
    # Add Neo4j structured data
    if neo4j_results:
        context_parts.append("=== Locations from Knowledge Graph ===")
        for i, result in enumerate(neo4j_results[:5], 1):
            location_info = f"{i}. {result.get('name', 'Unknown')}"
            if result.get('type'):
                location_info += f" ({result['type']})"
            if result.get('country'):
                location_info += f" in {result['country']}"
            if result.get('description'):
                location_info += f"\n   Description: {result['description']}"
            if result.get('rating'):
                location_info += f"\n   Rating: {result['rating']}/5"
            context_parts.append(location_info)
    
    # Add Pinecone unstructured data
    if pinecone_results:
        context_parts.append("\n=== Detailed Travel Information ===")
        for i, result in enumerate(pinecone_results[:3], 1):
            doc_info = f"{i}. From {result.get('title', 'Travel Guide')}:\n   {result.get('text', '')[:500]}..."
            context_parts.append(doc_info)
    
    return "\n\n".join(context_parts)

def generate_answer(query: str, context: str, query_type: str) -> str:
    """Generate answer using OpenAI with context-aware prompting"""
    
    system_prompts = {
        "itinerary": """You are an expert travel planner. Create detailed, day-by-day itineraries 
        that include specific locations, activities, timing, and practical tips. Be specific and organized.""",
        
        "recommendation": """You are a knowledgeable travel advisor. Provide specific recommendations 
        with clear reasoning, considering factors like ratings, location type, and traveler preferences.""",
        
        "factual": """You are a travel information specialist. Provide accurate, concise answers 
        based on the available information. If information is uncertain, say so.""",
        
        "general": """You are a helpful travel assistant. Provide informative, friendly responses 
        that help users plan their travels."""
    }
    
    system_prompt = system_prompts.get(query_type, system_prompts["general"])
    
    user_prompt = f"""Based on the following information, answer this question: {query}

{context}

Instructions:
- Be specific and use information from both the locations database and travel guides
- If creating an itinerary, organize by days and include timing
- Mention specific location names, types, and ratings when relevant
- If information is limited, acknowledge it and provide best available guidance
- Keep the response well-structured and easy to follow
"""
    
    try:
        resp = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        return resp.choices[0].message.content
        
    except Exception as e:
        return f"Error generating response: {e}"

def answer(query: str, verbose: bool = False) -> str:
    """Main function to answer queries using hybrid search"""
    
    # Determine query type
    query_type = determine_query_type(query)
    
    if verbose:
        print(f"\n🔍 Query type: {query_type}")
        print(f"📝 Processing: {query}\n")
    
    # Search both sources
    neo4j_results = neo4j_search(query, limit=10)
    pinecone_results = pinecone_search(query, k=5)
    
    if verbose:
        print(f"📊 Found {len(neo4j_results)} results from Neo4j")
        print(f"📊 Found {len(pinecone_results)} results from Pinecone\n")
    
    # For itinerary queries, also get top locations by country
    entities = extract_entities(query)
    if query_type == "itinerary" and entities["keywords"]:
        for keyword in entities["keywords"]:
            country_locations = get_locations_by_country(keyword, limit=15)
            if country_locations:
                neo4j_results.extend(country_locations)
                if verbose:
                    print(f"📍 Added {len(country_locations)} locations from {keyword}")
    
    # Build context
    context = build_context(query, neo4j_results, pinecone_results)
    
    # Generate answer
    answer_text = generate_answer(query, context, query_type)
    
    return answer_text

def interactive_chat():
    """Run interactive chat session"""
    print("=" * 60)
    print("🌍 Blue Enigma Travel Assistant")
    print("=" * 60)
    print("Ask me about travel destinations, itineraries, or recommendations!")
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
            print(f"\n🌟 Assistant: {response}\n")
            print("-" * 60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Happy travels! Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")

if __name__ == "__main__":
    # Test with example query
    test_query = "create a romantic 4 day itinerary for Vietnam"
    print(f"Testing with: {test_query}\n")
    result = answer(test_query, verbose=True)
    print(f"\nAnswer:\n{result}")
    
    # Start interactive mode
    print("\n" + "=" * 60 + "\n")
    interactive_chat()