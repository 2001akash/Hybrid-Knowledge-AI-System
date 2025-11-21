Here is the **final polished README.md** — clean, concise, production-ready, and formatted so you can **copy–paste directly** into your repository.

---

# **Blue Enigma – Hybrid AI Travel Assistant (Groq + Neo4j + Pinecone)**

A **next-generation travel planning system** that combines:

* 🧠 **Groq LLMs** (Mixtral / Llama3) for ultra-fast reasoning
* 🌐 **Neo4j Knowledge Graphs** for structured travel intelligence
* 🔍 **Pinecone Vector DB** for semantic search
* ⚡ **Local SentenceTransformer Embeddings** (FREE, no OpenAI needed)
* 💬 **Interactive Chat + REST API** for seamless integration

This system demonstrates a production-ready hybrid RAG architecture with knowledge graphs, vector search, and LLM-based reasoning.

---

## 🚀 Features

* ✈️ **Smart Itinerary Generation** (1–10 days)
* 🍽️ **Personalized Recommendations** for restaurants, attractions, hotels
* 🧩 **Hybrid Retrieval** (Graph + Vector Fusion)
* 🔎 **Semantic Search over travel guides**
* 🧠 **Real-time LLM reasoning using Groq**
* 💬 **Interactive CLI Chat**
* 🌐 **FastAPI Server** for deployment

---

## 🏗️ Architecture Overview

```
User Query
   ↓
Intent Classifier (Groq)
   ↓
┌───────────────────┬────────────────────┐
│ Neo4j Knowledge   │ Pinecone Semantic  │
│ Graph Retrieval   │ Vector Search      │
└───────────┬────────┴──────────┬────────┘
            │                   │
            └───── Context Fusion ─────┘
                           ↓
                   Groq LLM (Mixtral)
                           ↓
                    Final Response
```

---

## 📋 Requirements

* Python 3.8+
* Docker (for Neo4j)
* **Groq API Key** → [https://console.groq.com](https://console.groq.com)
* Pinecone API Key → [https://www.pinecone.io/](https://www.pinecone.io/)
* Neo4j Desktop or Docker container
* Basic travel JSON and CSV dataset

---

## 📁 Folder Structure

```
hybrid-knowledge-ai-system/
├── data/                   
│   ├── locations.csv       
│   ├── delhi.json         
│   ├── goa.json
│   └── vietnam.json
├── neo4j_loader.py
├── pinecone_upload.py
├── hybrid_chat.py
├── fastapi_app.py
├── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## ⚙️ Installation

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd hybrid-knowledge-ai-system
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup `.env`

```bash
cp .env.example .env
```

Fill in your keys:

```
GROQ_API_KEY=your_key_here
PINECONE_API_KEY=your_pinecone_key
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
PINECONE_INDEX_NAME=vietnam-travel
PINECONE_ENVIRONMENT=us-east-1
```

---

## 🗄️ Start Neo4j

Start Neo4j using Docker:

```bash
docker-compose up -d
```

Access Neo4j Browser:

```
http://localhost:7474
```

---

## 🧩 Prepare Data

### 1. Load data into Neo4j

```bash
python neo4j_loader.py
```

This script:

* Creates constraints
* Loads `locations.csv`
* Builds relationships
* Verifies connectivity

---

### 2. Upload travel documents to Pinecone

This uses **FREE local embeddings** (`all-MiniLM-L6-v2`) so no OpenAI needed.

```bash
python pinecone_upload.py
```

This will:

* Create Pinecone index
* Chunk JSON documents
* Embed using local model
* Upload vectors + metadata

---

## 💬 Interactive Chat Mode (Groq)

Start hybrid AI travel assistant:

```bash
python hybrid_chat.py
```

Example queries:

* "Create a romantic 4-day itinerary for Vietnam"
* "Best beaches in Bali"
* "Top family hotels in Singapore"
* "What are the must-visit temples in Bangkok?"

---

## 🌐 REST API (FastAPI + Groq)

Start the API server:

```bash
python fastapi_app.py
```

Visit documentation:

```
http://localhost:8000/docs
```

Example API call:

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "3-day itinerary for Paris"}'
```

---

## 📊 Testing

### Test Groq connectivity

```bash
python -c "from groq import Groq; print('Groq OK')"
```

### Test Pinecone

```bash
python - <<EOF
from pinecone import Pinecone
pc = Pinecone(api_key="YOUR_KEY")
print(pc.list_indexes())
EOF
```

### Test Neo4j

```bash
python - <<EOF
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j","password"))
driver.verify_connectivity()
print("Neo4j Connected")
EOF
```

---

## 🔍 How Hybrid Retrieval Works

### Neo4j retrieves:

* Countries
* Cities
* Ratings
* Attraction types
* Graph-based relationships

### Pinecone retrieves:

* Contextual descriptions
* Hidden semantic themes
* Travel guides

### Groq fuses both:

* Produces structured itinerary
* Uses reasoning + summarization

---

## 📈 Performance Optimizations

* Local embeddings → no cost
* Pinecone upserts batched
* Neo4j full-text indexes
* Minimal memory retention
* Groq streaming generation (fastest LLM inference)

---

## 🐛 Troubleshooting

### Pinecone dimension mismatch

Delete index and re-upload:

```bash
python delete_index.py
python pinecone_upload.py
```

### Neo4j fails to connect

Ensure Docker is running.

### Groq key invalid

Generate new key in Groq console.

---

## 🔮 Future Enhancements

* Multi-user personalization
* Multi-language support
* Travel cost estimation
* Hotel/Flight API integration
* Conversation history memory
* Real-time weather integration

