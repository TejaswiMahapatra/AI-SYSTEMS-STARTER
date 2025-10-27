# Getting Started with Clause.AI

**Complete guide to run the system from scratch.**

---

## Quick Start

```bash
make run
```

**That's it!** Press `Ctrl+C` to stop.

**What it does:**
- Starts all Docker services (Postgres, Weaviate, Redis, MinIO, Ollama)
- Pulls Ollama model if needed
- Starts backend + worker together

---

## Manual Setup

### Step 1: Start Infrastructure

```bash
cd infra/docker
docker-compose up -d
sleep 10
docker-compose ps
```

**Services started:** Postgres (5433), Weaviate (8080), Redis (6379), MinIO (9000), Ollama (11434)

### Step 2: Verify Services

```bash
# Postgres
docker exec -it ai-systems-postgres psql -U postgres -d ai_systems -c "SELECT version();"

# Weaviate
curl -s http://localhost:8080/v1/meta | jq '{version, modules}'

# Redis
docker exec -it ai-systems-redis redis-cli ping

# MinIO
curl -s http://localhost:9000/minio/health/live
```

### Step 3: Start Backend (Terminal 1)

```bash
cd ../..
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait for: `Application startup complete.`

### Step 4: Start Worker (Terminal 2)

```bash
cd /Users/tejaswimahapatra/Desktop/nexgAI/ai-systems-starter
source venv/bin/activate
python -m backend.workers.ingestion_worker
```

Wait for: `Polling Redis queue: ingestion_queue`

---

## Testing the System (Terminal 3)

### 1. Health Check

```bash
curl -s http://localhost:8000/api/v1/health | jq '.'
```

**Expected:** `"status": "healthy"`

### 2. Upload Document

```bash
curl -s -X POST http://localhost:8000/api/v1/ingest/upload \
  -F "file=@examples/contracts/sample_clause_contract.pdf" \
  -F "collection_name=Default" | jq '.'
```

**Returns:** `document_id` (save this!)

**Watch Terminal 2** - you'll see real-time processing:
```
Processing job: abc-123...
→ Detected legal document, using clause-aware chunking
Created 12 chunks
```

### 3. Check Status

```bash
# Replace YOUR_DOC_ID with the document_id from step 2
curl -s "http://localhost:8000/api/v1/ingest/status/YOUR_DOC_ID" | jq '.'
```

**Expected:** `"status": "completed"`, `"num_chunks": 12`

### 4. RAG Query

```bash
curl -s -X POST http://localhost:8000/api/v1/query/rag \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the termination clauses?",
    "collection_name": "Default",
    "top_k": 3
  }' | jq '{question, answer, confidence}'
```

**Returns:** Human-friendly answer with sources and confidence score

### 5. Semantic Search

```bash
curl -s -X POST http://localhost:8000/api/v1/query/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "executive obligations",
    "collection_name": "Default",
    "top_k": 3
  }' | jq '[.[] | {text: .text[:150], score, clause_number: .metadata.clause_number}]'
```

**Returns:** Raw vector search results with metadata

### 6. Agent Query

```bash
curl -s -X POST http://localhost:8000/api/v1/query/agent \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize the key terms",
    "collection_name": "Default"
  }' | jq '{answer: .answer[:400], num_tools_used}'
```

**Agent uses RAG tool automatically** and synthesizes answer

### 7. Verify Clause Metadata

```bash
curl -s -X POST http://localhost:8000/api/v1/query/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "section 5",
    "collection_name": "Default",
    "top_k": 3
  }' | jq '[.[] | {clause_number, chunk_type, section_title}]'
```

**Should show:** `clause_number: "5.1"`, `chunk_type: "clause"`

### 8. Test Redis Pub/Sub

```bash
python -m backend.tests.test_pubsub_live
```

**Expected:** `ALL TESTS PASSED`

---

## System Architecture

### Data Flow

```
1. USER uploads PDF via /ingest/upload
   ↓
2. Backend saves PDF to MinIO, creates DB record, adds job to Redis queue
   ↓
3. WORKER picks up job from Redis queue
   ↓
4. Worker: Download PDF → Extract text → Detect if legal doc
   ↓
5. If legal doc: Use clause-aware chunking (preserves clause numbers)
   If not: Use semantic chunking
   ↓
6. Worker: Generate embeddings → Store vectors in Weaviate
   ↓
7. Worker: Update DB with completion status
   ↓
8. USER queries via /query/rag or /query/agent
   ↓
9. Backend: Vector search in Weaviate → Retrieve relevant chunks
   ↓
10. LLM generates human-friendly answer from retrieved chunks
```

---

## Troubleshooting

### Connection Refused

```bash
docker ps              # Check containers running
lsof -i :8000         # Check backend port
lsof -i :11434        # Check Ollama port
```

### Worker Not Processing

```bash
# Check queue (should be 0 if processing)
docker exec -it ai-systems-redis redis-cli LLEN ingestion_queue
```

### Weaviate Issues

```bash
docker logs ai-systems-weaviate
docker restart ai-systems-weaviate
```

### Ollama Model Missing

```bash
docker exec ai-systems-ollama ollama list
docker exec ai-systems-ollama ollama pull llama3.1:8b
```

### Nuclear Reset

```bash
make stop-all
cd infra/docker && docker-compose down -v
make run
```

---

## Useful Commands

```bash
make help          # Show all commands
make run           # Start everything
make stop-all      # Stop all processes
make status        # Check service status
make logs          # View all logs
make shell-postgres # Open Postgres shell
make shell-redis   # Open Redis CLI
make ollama-list   # Show downloaded models
```

---

## Service URLs

- **API Docs**: http://localhost:8000/docs
- **Backend**: http://localhost:8000
- **Weaviate**: http://localhost:8080
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **Ollama**: http://localhost:11434

---

**Ready to build?** Run `make run` and let's go! 🚀
