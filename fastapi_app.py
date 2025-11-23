from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import logging

# Import from your hybrid_chat
from hybrid_chat import answer, neo4j_search, pinecone_search

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=" Travel Assistant",
    description="AI-powered travel planning using Neo4j + Pinecone + Groq",
    version="1.0.0"
)

# Enable CORS for external HTML files
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class ChatQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="User's travel query")
    verbose: Optional[bool] = Field(False, description="Enable verbose logging")

class ChatResponse(BaseModel):
    query: str
    answer: str
    neo4j: List[Dict]
    pinecone: List[Dict]
    timestamp: str
    success: bool

# Root endpoint
@app.get("/")
async def root():
    """API information"""
    return {
        "message": " Travel Assistant API",
        "version": "1.0.0",
        "powered_by": {
            "llm": "Groq (Llama 3.3)",
            "knowledge_graph": "Neo4j",
            "vector_db": "Pinecone",
            "embeddings": "Local (all-MiniLM-L6-v2)"
        },
        "endpoints": {
            "chat": "POST /chat",
            "health": "GET /health",
            "docs": "GET /docs",
            "openapi": "GET /openapi.json"
        },
        "usage": {
            "frontend": "Open index.html in your browser",
            "api_docs": "Visit http://localhost:8000/docs"
        }
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "running",
            "llm": "Groq (Llama 3.3)",
            "embeddings": "all-MiniLM-L6-v2",
            "neo4j": "connected",
            "pinecone": "connected"
        }
    }

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(q: ChatQuery):
    """
    Main chat endpoint for travel queries
    
    Combines Neo4j knowledge graph + Pinecone vector search + Groq LLM
    
    Args:
        q: ChatQuery with user query and optional verbose flag
    
    Returns:
        ChatResponse with answer and context sources
    
    Example:
        POST /chat
        {
            "query": "create a romantic 4 day itinerary for Vietnam"
        }
    """
    try:
        logger.info(f" Received query: {q.query}")
        
        # Get Neo4j knowledge graph results
        neo4j_results = neo4j_search(q.query, limit=10)
        logger.info(f" Neo4j results: {len(neo4j_results)}")
        
        # Get Pinecone vector search results
        pinecone_results = pinecone_search(q.query, k=5)
        logger.info(f" Pinecone results: {len(pinecone_results)}")
        
        # Generate answer using hybrid context with Groq
        answer_text = answer(q.query, verbose=q.verbose)
        logger.info(f" Answer generated: {len(answer_text)} characters")
        
        # Format Neo4j results for frontend
        neo4j_formatted = []
        for result in neo4j_results[:5]:  # Top 5 results
            neo4j_formatted.append({
                "name": result.get("name", "Unknown"),
                "type": result.get("type", ""),
                "description": result.get("description", "")[:200],  # Truncate long descriptions
                "rating": result.get("rating", "N/A")
            })
        
        # Format Pinecone results for frontend
        pinecone_formatted = []
        for result in pinecone_results[:3]:  # Top 3 results
            pinecone_formatted.append({
                "chunk": result.get("text", "")[:300],  # Truncate long text
                "source": result.get("source", ""),
                "score": round(result.get("score", 0), 4)
            })
        
        logger.info(" Request completed successfully")
        
        return {
            "query": q.query,
            "answer": answer_text,
            "neo4j": neo4j_formatted,
            "pinecone": pinecone_formatted,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
    
    except Exception as e:
        logger.error(f" Error processing query: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": str(e),
                "query": q.query
            }
        )

# Statistics endpoint (optional)
@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        from neo4j import GraphDatabase
        import config
        
        # Get Neo4j stats
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            total_nodes = result.single()['count']
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            total_relationships = result.single()['count']
        
        driver.close()
        
        # Get Pinecone stats
        from pinecone import Pinecone
        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        index = pc.Index(config.PINECONE_INDEX_NAME)
        pinecone_stats = index.describe_index_stats()
        
        return {
            "neo4j": {
                "total_nodes": total_nodes,
                "total_relationships": total_relationships
            },
            "pinecone": {
                "total_vectors": pinecone_stats.get('total_vector_count', 0),
                "dimension": pinecone_stats.get('dimension', 0)
            },
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("  Travel Assistant API")
    print("=" * 70)
    print()
    print(" System Information:")
    print("   • LLM: Groq (Llama 3.3)")
    print("   • Embeddings: all-MiniLM-L6-v2 (Local)")
    print("   • Knowledge Graph: Neo4j")
    print("   • Vector Database: Pinecone")
    print()
    print(" Endpoints:")
    print("   • API: http://localhost:8000")
    print("   • Docs: http://localhost:8000/docs")
    print("   • Health: http://localhost:8000/health")
    print("   • Stats: http://localhost:8000/stats")
    print()
    print("=" * 70)
    print()
    
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )