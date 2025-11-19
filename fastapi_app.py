from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import logging
from hybrid_chat import answer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Blue Enigma Hybrid Travel Assistant",
    description="AI-powered travel planning using Neo4j + Pinecone + OpenAI",
    version="1.0.0"
)

# Enable CORS for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class Query(BaseModel):
    query: str = Field(..., min_length=1, description="User's travel query")
    verbose: Optional[bool] = Field(False, description="Enable verbose logging")

class ChatResponse(BaseModel):
    query: str
    answer: str
    timestamp: str
    success: bool

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str

# Endpoints
@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint"""
    return {
        "message": "Welcome to Blue Enigma Travel Assistant API",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(q: Query):
    """
    Main chat endpoint for travel queries
    
    Examples:
    - "create a romantic 4 day itinerary for Vietnam"
    - "best restaurants in Paris"
    - "what to do in Tokyo"
    """
    try:
        logger.info(f"Received query: {q.query}")
        
        # Get answer from hybrid system
        answer_text = answer(q.query, verbose=q.verbose)
        
        logger.info(f"Successfully generated answer")
        
        return {
            "query": q.query,
            "answer": answer_text,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/test", tags=["Testing"])
async def test_query():
    """Test endpoint with predefined query"""
    test_q = "create a romantic 4 day itinerary for Vietnam"
    try:
        result = answer(test_q, verbose=False)
        return {
            "test_query": test_q,
            "answer": result,
            "status": "success"
        }
    except Exception as e:
        return {
            "test_query": test_q,
            "error": str(e),
            "status": "failed"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "fastapi_app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )