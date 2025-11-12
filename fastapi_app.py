from fastapi import FastAPI
from pydantic import BaseModel
from hybrid_chat import answer

app = FastAPI(title="Blue Enigma Hybrid Chat")

class Query(BaseModel):
    query: str

@app.post("/chat")
async def chat(q: Query):
    return {"query": q.query, "answer": answer(q.query)}
