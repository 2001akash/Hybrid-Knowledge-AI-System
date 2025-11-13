🌏 Hybrid Knowledge AI System — Advanced RAG Travel Assistant












🚀 Overview

This project implements an Advanced Hybrid Retrieval-Augmented Generation (RAG) System combining:

Pinecone Vector Search → semantic understanding

Neo4j Graph Database → relationships & structured travel knowledge

OpenAI GPT Models → reasoning & itinerary generation

Router + Reranker + Summarizer → enhanced accuracy & creativity

Async Pipeline + Embedding Cache → performance & scalability

It answers complex travel queries like:

“Create a romantic 4-day Vietnam itinerary with food and cultural highlights.”

The system retrieves both semantic and graph knowledge, merges them, reasons over them, and produces beautiful, grounded travel plans.

📚 Table of Contents

🌲 Architecture

📂 Folder Structure

⚙️ Setup Instructions

🗄️ Neo4j Setup

🔍 Pinecone Setup

📥 Uploading Data

🤖 Running the Hybrid Chat System

🌐 FastAPI Endpoint

🧠 Example Query

🚀 Features

🧪 Tests

📈 Screenshots Required for Submission

📝 Improvements Summary

📜 License

🌲 Architecture
                ┌───────────────────────┐
                │       User Query      │
                └────────────┬──────────┘
                             ▼
                 ┌───────────────────────┐
                 │   Intent Router       │
                 │ (itinerary/weather/…) │
                 └────────────┬──────────┘
                             ▼
         ┌──────────────────────────┬─────────────────────────┐
         ▼                          ▼                         ▼
┌────────────────┐       ┌──────────────────┐       ┌─────────────────────┐
│ Async Embedder │       │ Pinecone Vector  │       │ Neo4j Graph Fetch   │
│ + Cache (SQLite│       │ Search (TOP-K)   │       │ (neighbors, edges)  │
└────────────────┘       └──────────────────┘       └─────────────────────┘
         └───────────────┬───────────────┬───────────────┘
                         ▼               ▼
                  ┌──────────────────────────┐
                  │     Reranker (Graph+Vec) │
                  └──────────────┬───────────┘
                                 ▼
                      ┌─────────────────────┐
                      │     Summarizer      │
                      └────────────┬────────┘
                                   ▼
                         ┌───────────────────┐
                         │  GPT Reasoning    │
                         │ (CoT + Final Ans) │
                         └───────────────────┘
                                   ▼
                           ┌────────────┐
                           │ Final Plan │
                           └────────────┘

📂 Folder Structure
Hybrid-Knowledge-AI-System/
│
├── config.py
├── pinecone_upload.py
├── load_to_neo4j.py
├── visualize_graph.py
├── hybrid_chat.py
├── fastapi_app.py
├── improvements.md
├── README.md
│
├── vietnam_travel_dataset.json
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
│
└── tests/
    ├── test_embeddings.py
    ├── test_graph.py
    ├── test_pinecone_index.py
    └── test_reranker.py

⚙️ Setup Instructions
1. Clone Repo
git clone https://github.com/yourusername/Hybrid-Knowledge-AI-System.git
cd Hybrid-Knowledge-AI-System

2. Create Virtual Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

3. Add Your API Keys

Edit:

config.py


Set:

OPENAI_API_KEY

PINECONE_API_KEY

Neo4j credentials

🗄️ Neo4j Setup

Start Neo4j using Docker:

docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.11


Open Neo4j Browser:

👉 http://localhost:7474

Run:

CALL db.index.fulltext.createNodeIndex(
  "entityTextIndex",
  ["Entity"],
  ["name", "description"]
);

🔍 Pinecone Setup

Confirm region inside config.py:

PINECONE_ENV = "us-east4-gcp"


Dashboard:
👉 https://app.pinecone.io

📥 Uploading Data
Load Graph
python load_to_neo4j.py

Visualize Graph
python visualize_graph.py


Outputs file:

neo4j_graph.png

Upload Embeddings to Pinecone
python pinecone_upload.py

🤖 Running the Hybrid Chat System
CLI mode
python hybrid_chat.py


Enter your travel question:

create a romantic 4 day itinerary for Vietnam

🌐 FastAPI Endpoint

Start server:

uvicorn fastapi_app:app --reload --port 8000


POST request:

POST http://localhost:8000/chat
{
  "query": "best food experiences in Hanoi"
}

🧠 Example Query
create a romantic 4 day itinerary for Vietnam focusing on food + culture


Output includes:

Summary of retrieved nodes

Chain-of-thought reasoning

Day-by-day itinerary

Node id citations

Travel tips

🚀 Features
✔ Hybrid RAG — Vector + Graph
✔ Async I/O for speed
✔ Embedding Cache (SQLite)
✔ Query Router (intent classification)
✔ Reranker (Graph + Vector combined)
✔ Summarizer for context
✔ CoT reasoning + structured final output
✔ FastAPI server included
✔ Unit tests included
🧪 Tests

Run all tests:

pytest tests/


Included tests cover:

Embedding returns correct dimension

Pinecone index exists

Graph neighbors fetched correctly

Reranker boosts graph-connected nodes

📈 Screenshots Required for Submission

Create these 5 screenshots:

1. Pinecone Dashboard

Index name

Total vectors

Dimension = 1536

2. Terminal Output — pinecone_upload.py

Shows:

✔ Batch uploaded: 32 vectors

3. Neo4j Browser — Nodes + Relationships

Graph preview

4. visualize_graph.py output

File: neo4j_graph.png

5. hybrid_chat.py output

Sample itinerary answer

📝 Improvements Summary

See:

improvements.md


Covers:

Async pipeline

Embedding cache

Reranking

Router

Prompt improvements

Pinecone/OpenAI v2 fixes

Performance optimizations

📜 License

MIT License — You may use, modify, or extend freely.