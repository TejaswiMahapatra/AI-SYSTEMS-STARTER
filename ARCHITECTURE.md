# Clause.AI System Architecture

**Production-ready RAG system with clause-aware chunking, LangGraph agents, and real-time processing.**

---

## High-Level Architecture

```
+-------------------------------------------------------------+
|                     FRONTEND                                |
|              (Next.js + Vercel AI SDK)                      |
|  - Upload PDFs via drag & drop                              |
|  - Chat interface with streaming                            |
|  - Real-time progress via WebSocket                         |
+------------------------+------------------------------------+
                         | HTTP/WebSocket
                         |
+------------------------v------------------------------------+
|                  BACKEND API                                |
|                  (FastAPI)                                  |
|                                                             |
|  +--------------+  +--------------+  +--------------+       |
|  | Ingest API   |  |  Query API   |  |  WebSocket   |       |
|  | /upload      |  |  /rag        |  |  /ws/:id     |       |
|  |              |  |  /agent      |  |              |       |
|  +--------------+  +--------------+  +--------------+       |
+------------------------+------------------------------------+
                         |
           +-------------+-------------+
           |                           |
+----------v------+            +-------v------+
|   WORKER        |            |   SERVICES   |
|  (Background)   |            |              |
|                 |            | - LLM        |
| - PDF Parse     |            | - Embeddings |
| - Chunking      |            | - Vector DB  |
| - Embedding     |            | - Storage    |
| - Storage       |            |              |
+-----------------+            +--------------+
           |                           |
           +-------------+-------------+
                         |
+------------------------v------------------------------------+
|                 DATA LAYER                                  |
|  +--------------+  +--------------+  +--------------+       |
|  |  PostgreSQL  |  |   Weaviate   |  |     MinIO    |       |
|  |  (Metadata)  |  |   (Vectors)  |  |  (PDF Files) |       |
|  +--------------+  +--------------+  +--------------+       |
|  +--------------+                                           |
|  |    Redis     |                                           |
|  | (Queue/PubSub)|                                          |
|  +--------------+                                           |
+-------------------------------------------------------------+
```

---

## Data Flow

### 1. Document Ingestion Pipeline

```
User uploads PDF
    |
    v
Backend receives file
    |
    v
Store PDF in MinIO (S3-compatible)
    |
    v
Create document record in Postgres (status: QUEUED)
    |
    v
Add job to Redis queue (ingestion_queue)
    |
    v
Worker picks up job
    |
    v
Download PDF from MinIO
    |
    v
Extract text with pypdf
    |
    v
Detect document type (legal doc?)
    |
    v
+-------------------------------+
| If LEGAL DOCUMENT:            |
| - Use clause-aware chunking   |
| - Preserve clause numbers     |
| - Maintain hierarchy          |
+-------------------------------+
    |
    v
+-------------------------------+
| If OTHER DOCUMENT:            |
| - Use semantic chunking       |
| - RecursiveTextSplitter       |
+-------------------------------+
    |
    v
Generate embeddings (all-MiniLM-L6-v2, 384D)
    |
    v
Store vectors in Weaviate with metadata
    |
    v
Update Postgres (status: COMPLETED, num_chunks)
    |
    v
Publish progress via Redis Pub/Sub
    |
    v
WebSocket streams updates to frontend
```

### 2. Query Pipeline (RAG)

```
User asks question
    |
    v
Convert question to embedding vector (384D)
    |
    v
Semantic search in Weaviate (cosine similarity)
    |
    v
Retrieve top K chunks with metadata
    |
    v
Format chunks as context for LLM
    |
    v
Send to Ollama (llama3.1:8b)
    |
    v
LLM generates human-friendly answer
    |
    v
Return answer + sources + confidence
```

### 3. Agent Pipeline (LangGraph)

```
User asks complex question
    |
    v
Agent analyzes question
    |
    v
Plans which tools to use:
  - rag_query (search + answer)
  - analyze_content (deep analysis)
  - compare_content (comparisons)
  - generate_report (summaries)
    |
    v
Execute tools in sequence
    |
    v
Agent synthesizes final answer
    |
    v
Return answer + tool usage metadata
```

---

## Component Details

### Backend API (FastAPI)

**Endpoints:**
- `POST /api/v1/ingest/upload` - Upload PDF for processing
- `GET /api/v1/ingest/status/:id` - Check processing status
- `POST /api/v1/query/rag` - RAG query (search + answer)
- `POST /api/v1/query/agent` - Agent query (multi-tool reasoning)
- `POST /api/v1/query/search` - Semantic search only
- `WS /ws/:id` - WebSocket for real-time progress

**Key Features:**
- Async/await throughout
- Type hints with Pydantic
- Dependency injection
- OpenAPI docs at `/docs`

### Ingestion Worker

**Responsibilities:**
- Poll Redis queue for new jobs
- Download PDFs from MinIO
- Extract text from PDFs
- Detect legal documents (filename + content patterns)
- Chunk text (clause-aware for legal docs)
- Generate embeddings
- Store vectors in Weaviate
- Update Postgres status
- Publish progress updates

**Technologies:**
- pypdf for text extraction
- sentence-transformers for embeddings
- Redis for job queue
- Separate Redis connection for pub/sub

### Services Layer

#### PDF Service
- Extract text from PDFs using pypdf
- Handle encrypted PDFs
- Extract metadata (pages, size)

#### Chunking Service
- **Generic Chunking**: RecursiveTextSplitter
- **Clause-Aware Chunking**: Custom regex-based parser
  - Detects section headers (Article, Section)
  - Extracts clause numbers (5.1, 5.1.1)
  - Preserves hierarchy
  - Maintains context

#### Embedding Service
- Uses all-MiniLM-L6-v2 (384D vectors)
- Batched processing for efficiency
- Plugin architecture for swapping models

#### Vector Service
- Weaviate client wrapper
- Create/delete collections
- Insert vectors with metadata
- Semantic search with filters

#### LLM Service
- Ollama client wrapper (llama3.1:8b)
- Streaming support
- Temperature and context controls
- Plugin architecture (OpenAI, Anthropic)

#### Storage Service
- MinIO client wrapper
- Upload/download PDFs
- S3-compatible operations
- Bucket management

### LangGraph Agent

**Tools Available:**
1. **rag_query**: Search documents + generate answer
2. **analyze_content**: Deep analysis with custom instructions
3. **compare_content**: Compare two pieces of content
4. **generate_report**: Create structured reports

**Agent Flow:**
```
Plan -> Execute Tools -> Synthesize -> Answer
```

**Prompts:**
- `agent_system.txt`: Agent behavior and strategy
- `agent_plan.txt`: Planning instructions
- `agent_synthesize.txt`: Final answer synthesis
- `rag_answer.txt`: RAG response formatting

---

## Data Layer

### PostgreSQL (Port 5433)

**Documents Table:**
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    filename VARCHAR,
    original_filename VARCHAR,
    file_size INTEGER,
    mime_type VARCHAR,
    minio_path VARCHAR,
    minio_bucket VARCHAR,
    status VARCHAR,  -- QUEUED, PROCESSING, COMPLETED, FAILED
    error_message TEXT,
    num_pages INTEGER,
    num_chunks INTEGER,
    total_tokens INTEGER,
    weaviate_collection VARCHAR,
    user_id VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    processed_at TIMESTAMP
);
```

### Weaviate (Port 8080)

**Collection Schema:**
```python
{
    "class": "Default", 
    "properties": [
        {"name": "text", "dataType": ["text"]},
        {"name": "document_id", "dataType": ["text"]},
        {"name": "chunk_index", "dataType": ["int"]},
        {"name": "page_number", "dataType": ["int"]},
        {"name": "filename", "dataType": ["text"]},

        # Clause-specific metadata
        {"name": "clause_number", "dataType": ["text"]},     
        {"name": "section_title", "dataType": ["text"]},     
        {"name": "section_number", "dataType": ["text"]},   
        {"name": "chunk_type", "dataType": ["text"]},         
        {"name": "hierarchy_level", "dataType": ["number"]},  

        # Other metadata
        {"name": "document_type", "dataType": ["text"]},
        {"name": "char_count", "dataType": ["number"]},
        {"name": "page_count", "dataType": ["number"]},
    ],
    "vectorizer": "none", 
    "vectorIndexType": "hnsw",
    "vectorIndexConfig": {
        "distance": "cosine",
        "ef": -1,
        "efConstruction": 128,
        "maxConnections": 64
    }
}
```

### Redis (Port 6379)

**Job Queue:**
- List: `ingestion_queue`
- Format: JSON with `{document_id, filename, collection_name}`

**Pub/Sub Channels:**
- Pattern: `document:{document_id}:progress`
- Messages: `{document_id, status, message, progress, timestamp}`

### MinIO (Port 9000)

**Buckets:**
- `documents/` - Uploaded PDF files
- Path format: `documents/{document_id}/{filename}`

---

## Plugin Architecture

### Embedding Providers

```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        pass
```

**Implementations:**
- `LocalEmbeddings` - sentence-transformers (all-MiniLM-L6-v2)
- `OpenAIEmbeddings` - OpenAI text-embedding-3-small
- Easy to add: Cohere, Anthropic, custom models

### Vector Databases

```python
class VectorDBInterface(ABC):
    @abstractmethod
    async def create_collection(self, name: str, dimension: int):
        pass

    @abstractmethod
    async def insert(self, collection: str, vectors: List, metadata: List):
        pass

    @abstractmethod
    async def search(self, collection: str, vector: List, limit: int):
        pass
```

**Implementations:**
- `WeaviateDB` - Current implementation
- Easy to add: Pinecone, Qdrant, ChromaDB, pgvector

---

## Key Features

### 1. Clause-Aware Chunking

**Why it matters:** Legal documents have hierarchical structure that generic chunking breaks.

**How it works:**
- Regex patterns detect section headers and clause numbers
- Preserves hierarchy (5 -> 5.1 -> 5.1.1)
- Maintains context between parent and child clauses
- Better retrieval precision for legal queries

**Example:**
```
Generic chunking: "...shall terminate... ...within 30 days..."

Clause-aware:     "Section 5.1 (Termination Notice): Either party
                   shall terminate this agreement with 30 days
                   written notice."
```

### 2. Redis Pub/Sub for Real-time Updates

**Why it matters:** Users need to see progress during long document processing.

**How it works:**
- Worker publishes progress updates to Redis channel
- WebSocket subscribes to channel with **separate connection**
- Streams updates to frontend in real-time
- No polling required

**Key insight:** Separate Redis connection per subscriber prevents blocking.

### 3. Human-Friendly AI Responses

**Why it matters:** Raw LLM output is often robotic and verbose.

**How it works:**
- Custom prompts with conversational tone
- Structured formatting (bullets, numbered lists)
- Plain language explanations
- Context about why things matter
- "Key Takeaway" sections

---

## Configuration

### Environment Variables (.env)

```bash
# Postgres (Docker on port 5433 to avoid local conflicts)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=ai_systems

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Weaviate
WEAVIATE_URL=http://localhost:8080

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# LLM Provider
LLM_PROVIDER=ollama  # or openai, anthropic
```

---

## Production Considerations

### Completed
- Async/await throughout
- Type hints with Pydantic
- Error handling and logging
- Redis pub/sub with separate connections
- Docker Compose for local dev
- Makefile for easy commands
- Health check endpoints
- Clause-aware chunking for legal docs
- Human-friendly NLG prompts

### TODO
- Authentication (JWT)
- Rate limiting
- Caching
- Unit + integration tests
- LLM evaluation (DeepEval)
- Prometheus metrics
- Grafana dashboards
- Kubernetes manifests
- CI/CD pipeline
- Frontend (Next.js + Vercel AI SDK)
- Write a better agent

---

## Deployment

### Local Development

```bash
make run  # Starts everything
```

### Production

1. Set environment variables
2. Configure external services (RDS, S3, managed Redis)
3. Deploy with Docker Compose or Kubernetes
4. Enable monitoring (Prometheus + Grafana)
5. Set up LLM API keys (OpenAI, Anthropic)

---

## Additional Resources

- **Getting Started**: [docs/getting-started.md](docs/getting-started.md)
- **API Documentation**: http://localhost:8000/docs
- **Makefile Commands**: Run `make help`

---

**System Status:** Production-ready for v0.1 MVP with 100 users

**Key Achievement:** Built a complete RAG system with clause-aware chunking, real-time progress updates, and human-friendly AI responses in production-ready state.
