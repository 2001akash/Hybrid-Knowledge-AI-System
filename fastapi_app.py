from fastapi import FastAPI
from pydantic import BaseModel
from hybrid_chat import answer_query
import asyncio

app = FastAPI()

class Query(BaseModel):
    query: str

@app.post("/chat")
async def chat(q: Query):
    return await answer_query(q.query)
