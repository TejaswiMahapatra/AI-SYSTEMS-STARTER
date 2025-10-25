# What We've Built: Day 1 Complete

**Author**: Tejaswi Mahapatra
**Last Updated**: October 25, 2025
**Status**: Backend foundation ready for Day 2

---

## Overview

We've completed the foundation for a production-ready AI system with:
- 100% open source stack (no API keys required)
- Pluggable architecture (swap providers easily)
- Full Docker environment (5 services running)
- FastAPI backend with health checks
- Complete development workflow (Makefile commands)

**Total Time**: 5 hours
**Lines of Code**: ~1,500


---

## Day 1: Infrastructure Setup

### What We Built

**Docker Services** (5 containers running):

1. **PostgreSQL 16** (port 5432)
   - Purpose: Store document metadata, LangGraph agent checkpoints
   - Why: Required by LangGraph for state persistence
   - Database: `ai_systems` created

2. **Redis 7** (port 6379)
   - Purpose: Job queues for async processing, caching
   - Why: Decouple PDF upload from processing

3. **Weaviate 1.24.1** (port 8080)
   - Purpose: Vector database for semantic search
   - Why: Open source alternative to Pinecone

4. **MinIO** (ports 9000, 9001)
   - Purpose: S3-compatible object storage for PDFs
   - Why: Self-hosted, no AWS dependency

5. **Ollama** (port 11434)
   - Purpose: Local LLM inference (llama3.1:8b)
   - Why: 100% open source, no API costs

**Configuration Files**:

```
.gitignore
├── Purpose: Security - prevent secrets from being committed
├── Covers: Python, Node.js, Docker, .env files
└── Why: Essential for open source project

.env.example
├── Purpose: Template for environment variables
├── Defaults: 100% open source (Ollama, local embeddings)
├── Optional: Paid APIs (OpenAI, Anthropic) if wanted
└── Why: Show all options, no vendor lock-in

docker-compose.yml
├── Location: infra/docker/docker-compose.yml
├── Services: All 5 containers defined
├── Volumes: Persistent data (postgres_data, weaviate_data, etc.)
└── Why: One-command setup (make up)

Makefile
├── Commands: 25+ developer workflow commands
├── Categories: Setup, services, database, verification
├── Example: make up, make health, make ollama-pull
└── Why: Consistent workflow, easy onboarding

LICENSE + NOTICE
├── License: Apache 2.0
├── Copyright: Tejaswi Mahapatra
├── Why Apache: Patent protection, trademark rights
└── Why not MIT: Apache has explicit patent grant

README.md
├── Badges: License, open source status
├── Sections: Features, prerequisites, installation
├── Author: GitHub link to TejaswiMahapatra
└── Why: Professional first impression
```

### Key Decisions

**Why 100% Open Source?**
- No API key barriers for students
- No usage costs for learning
- Full control over data
- Enterprise can still use paid APIs (optional)

**Why Apache 2.0 License?**
- Patent protection (Section 3)
- Trademark protection (Section 6)
- Contribution terms clear
- More comprehensive than MIT

**Why Docker Compose?**
- Easy local development
- Consistent environment
- One command setup
- Production-like infrastructure

### Commands Available

```bash
# Setup
make init           # Full initialization
make up             # Start all services
make down           # Stop all services

# Verification
make health         # Check all services
make ollama-list    # List Ollama models
make logs           # View all logs

# Database
make db-shell       # PostgreSQL shell
make db-create      # Create database
make redis-cli      # Redis CLI

# Cleanup
make clean          # Remove containers
make clean-volumes  # Remove data volumes
```

---

## Day 1: Backend Foundation

### Architecture Overview

```
backend/
├── main.py                    # FastAPI app (144 lines)
├── config.py                  # Pydantic settings (190 lines)
├── requirements.txt           # 60+ dependencies
│
├── core/                      # Core infrastructure
│   ├── database.py           # Async SQLAlchemy (95 lines)
│   └── redis_client.py       # Redis utilities (192 lines)
│
├── models/                    # Database models
│   └── document.py           # Document metadata (127 lines)
│
├── interfaces/                # Abstract base classes
│   ├── embeddings.py         # Embedding interface (58 lines)
│   └── vector_db.py          # Vector DB interface (146 lines)
│
├── plugins/                   # Concrete implementations
│   ├── embeddings/
│   │   └── local_embeddings.py    # Sentence-transformers (81 lines)
│   └── vector_dbs/
│       └── weaviate_db.py         # Weaviate client (215 lines)
│
└── api/
    └── v1/
        └── health.py         # Health endpoints (189 lines)
```

### File-by-File Explanation

#### 1. `backend/config.py` - Configuration Management

**Purpose**: Type-safe configuration using Pydantic Settings

**Key Concepts**:
```python
class Settings(BaseSettings):
    # Pydantic automatically loads from .env file
    # Type hints provide IDE autocomplete
    # Validation happens on startup

    llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    # Literal = only these 3 values allowed
    # Default = "ollama" (open source)

    @property
    def database_url(self) -> str:
        # Computed property - builds URL from parts
        return f"postgresql+asyncpg://..."
```

**Why Pydantic Settings?**
- Type safety (catch errors early)
- IDE autocomplete (better DX)
- Validation on startup (fail fast)
- Properties for computed values

**Alternative**: `python-decouple` or `os.getenv`
- Simpler but no type safety
- No validation
- Manual parsing

**Decision**: Pydantic Settings worth the complexity for production

#### 2. `backend/core/database.py` - Database Layer

**Purpose**: Async PostgreSQL connection with SQLAlchemy

**Key Concepts**:
```python
# Async engine for PostgreSQL
engine = create_async_engine(
    settings.database_url,  # postgresql+asyncpg://...
    echo=settings.debug,    # Log SQL queries in debug mode
    pool_pre_ping=True,     # Verify connections before use
)

# Session factory (creates DB sessions)
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,  # Don't refresh objects after commit
    autocommit=False,        # Manual transaction control
    autoflush=False,         # Manual flush control
)

# Dependency injection for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session          # Provide session to route
            await session.commit() # Commit if no errors
        except Exception:
            await session.rollback() # Rollback on error
            raise
        finally:
            await session.close()    # Always close
```

**Why Async SQLAlchemy?**
- Non-blocking I/O (better performance)
- Consistent with FastAPI async patterns
- Scales to more concurrent users

**Why SQLAlchemy at all?**
- LangGraph requires it for checkpointing
- Already a dependency, might as well use it
- Migration support (Alembic)

**Alternative**: Raw asyncpg
- Faster but more boilerplate
- No ORM conveniences
- Still need SQLAlchemy for LangGraph

**Decision**: Use SQLAlchemy since it's required anyway

#### 3. `backend/core/redis_client.py` - Cache & Queue

**Purpose**: Redis connection with helper classes

**Key Concepts**:
```python
# Connection pool (reuse connections)
_redis_pool = ConnectionPool.from_url(
    settings.redis_url,
    decode_responses=True,  # Auto decode bytes to str
    max_connections=10,     # Pool size
)

# Cache helper class
class RedisCache:
    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(key)
        return json.loads(value) if value else None

    async def set(self, key: str, value: Any, ttl: Optional[int]):
        serialized = json.dumps(value)  # Serialize to JSON
        await self.redis.setex(key, ttl, serialized)

# Queue helper class
class RedisQueue:
    async def enqueue(self, job_data: dict):
        serialized = json.dumps(job_data)
        await self.redis.rpush(self.queue_name, serialized)

    async def dequeue(self, timeout: int = 0):
        result = await self.redis.blpop(self.queue_name, timeout)
        # blpop = blocking pop (waits for job)
```

**Why Redis?**
- Fast in-memory storage
- Pub/sub for real-time updates
- Job queues (FIFO with blpop)
- Session storage (future)

**Use Cases**:
- Cache: Embedding results (expensive to compute)
- Queue: PDF processing jobs (async workflow)
- Session: User authentication tokens (future)

**Alternative**: No cache/queue
- Simpler but slower
- Synchronous processing only
- No ability to scale workers

**Decision**: Redis essential for async architecture

#### 4. `backend/models/document.py` - Database Model

**Purpose**: SQLAlchemy model for document metadata

**Key Concepts**:
```python
class Document(Base):
    __tablename__ = "documents"

    # UUID primary key (better than auto-increment)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # Auto-generate UUID
        index=True           # Index for fast lookups
    )

    # Status enum (type-safe)
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus),
        default=DocumentStatus.QUEUED,
        index=True  # Index for "WHERE status = 'processing'"
    )

    # Timezone-aware timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
```

**Why This Model?**
- Tracks PDF processing state machine
- Stores metadata, not content (content in Weaviate)
- Links to MinIO (minio_path) and Weaviate

**Status Flow**:
```
QUEUED → PROCESSING → COMPLETED
           ↓
         FAILED
```

**Why UUID vs Auto-Increment?**
- UUID: Unique across databases, no collisions
- Auto-increment: Sequential, easier to guess

**Decision**: UUID for distributed systems

#### 5. `backend/interfaces/embeddings.py` - Abstraction

**Purpose**: Abstract base class for embedding providers

**Key Concepts**:
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass  # Must be implemented by subclass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass  # Batch is more efficient
```

**Why Interfaces?**
- Swap providers without changing code
- Test with mocks
- Clear contract

**Example Usage**:
```python
# In .env: EMBEDDING_PROVIDER=local
embedder = get_embedding_provider()  # Returns LocalEmbeddings

# Change to: EMBEDDING_PROVIDER=openai
embedder = get_embedding_provider()  # Returns OpenAIEmbeddings

# Code using embedder doesn't change!
result = await embedder.embed_text("Hello")
```

**Alternative**: No interface, hardcode provider
- Simpler initially
- Painful to change later
- Can't test easily

**Decision**: Interfaces worth it for flexibility

#### 6. `backend/plugins/embeddings/local_embeddings.py`

**Purpose**: Sentence-transformers implementation

**Key Concepts**:
```python
class LocalEmbeddings(EmbeddingProvider):
    def __init__(self):
        # Load model (cached after first load)
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2",  # 384 dimensions
            device="cpu"          # or "cuda" for GPU
        )

    async def embed_text(self, text: str) -> List[float]:
        # Not truly async (CPU-bound, not I/O-bound)
        # But interface is async for consistency
        embedding = self.model.encode(text)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]):
        # Batch is 10x faster than individual calls
        embeddings = self.model.encode(
            texts,
            batch_size=32,  # Process 32 at once
            show_progress_bar=False
        )
        return [emb.tolist() for emb in embeddings]
```

**Why all-MiniLM-L6-v2?**
- Small (90MB model)
- Fast (CPU inference)
- Good quality for most tasks
- 384 dimensions (vs 1536 for OpenAI)

**Alternative Models**:
- all-mpnet-base-v2: Better quality, slower (768 dim)
- paraphrase-multilingual: Supports 50+ languages

**Why Singleton Pattern?**
```python
_instance = None

def get_local_embeddings():
    global _instance
    if _instance is None:
        _instance = LocalEmbeddings()  # Load model once
    return _instance
```
- Model loading is slow (1-2 seconds)
- Model is large (90MB RAM)
- Reuse same instance across requests

#### 7. `backend/plugins/vector_dbs/weaviate_db.py`

**Purpose**: Weaviate vector database client

**Key Concepts**:
```python
class WeaviateDB(VectorDatabase):
    def __init__(self):
        self.client = weaviate.connect_to_local(
            host=settings.weaviate_url
        )

    async def create_collection(self, name, vector_dimension):
        # Define schema
        properties = [
            Property(name="text", data_type=DataType.TEXT),
            Property(name="document_id", data_type=DataType.TEXT),
            Property(name="chunk_index", data_type=DataType.INT),
        ]

        self.client.collections.create(
            name=name,
            properties=properties,
            vectorizer_config=Configure.Vectorizer.none()
            # We provide vectors, Weaviate doesn't generate them
        )

    async def insert_vectors(self, collection, vectors, texts, metadata):
        collection = self.client.collections.get(collection)

        # Batch insert (efficient)
        with collection.batch.dynamic() as batch:
            for vector, text, meta in zip(vectors, texts, metadata):
                batch.add_object(
                    properties={"text": text, ...},
                    vector=vector  # Our embedding
                )

    async def search(self, collection, query_vector, top_k=5):
        collection = self.client.collections.get(collection)

        # Vector similarity search
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True)
        )

        return [VectorSearchResult(...) for obj in response.objects]
```

**Why Weaviate?**
- Open source
- Fast (HNSW index)
- RESTful API
- GraphQL support
- Built for production

**Alternative**: Chroma, Qdrant, Pinecone
- Chroma: Simpler, less features
- Qdrant: Similar to Weaviate
- Pinecone: Cloud-only, paid

**Decision**: Weaviate for self-hosted production

#### 8. `backend/main.py` - FastAPI Application

**Purpose**: Main application with lifespan management

**Key Concepts**:
```python
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    validate_settings()  # Check config
    await init_db()      # Create tables

    yield  # App runs here

    # Shutdown
    await close_db()     # Close connections
    await close_redis()

app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan  # Register lifecycle
)

# CORS middleware (allow frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
if settings.enable_prometheus:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# Include routers
app.include_router(health.router, prefix="/api/v1")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(_request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

**Why Lifespan Events?**
- Initialize once on startup
- Clean up on shutdown
- Better than on-demand initialization

**Why CORS?**
- Frontend runs on different port (3000)
- Browser blocks cross-origin requests by default
- CORS middleware allows it

**Why Global Exception Handler?**
- Catch all unhandled errors
- Log for debugging
- Return clean JSON response
- Hide internal details in production

#### 9. `backend/api/v1/health.py` - Health Checks

**Purpose**: Monitor service health

**Key Concepts**:
```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": "development"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    # Check each service
    postgres_ok = await check_db_health()
    redis_ok = await check_redis_health()
    weaviate_ok = await weaviate.health_check()

    # Check Ollama
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.ollama_url}/api/tags")
        ollama_ok = response.status_code == 200

    return {
        "status": "healthy" if all_ok else "degraded",
        "services": {
            "postgresql": {"status": "healthy" if postgres_ok else "unhealthy"},
            "redis": {"status": "healthy" if redis_ok else "unhealthy"},
            ...
        }
    }

@router.get("/readiness")
async def readiness_check():
    # Kubernetes readiness probe
    # Returns 200 only if ready to accept traffic
    db_ok = await check_db_health()
    return {"status": "ready" if db_ok else "not_ready"}

@router.get("/liveness")
async def liveness_check():
    # Kubernetes liveness probe
    # Returns 200 if process is alive (even if not ready)
    return {"status": "alive"}
```

**Why Multiple Health Endpoints?**
- `/health`: Quick check for monitoring
- `/health/detailed`: Debug which service is down
- `/readiness`: K8s knows when to send traffic
- `/liveness`: K8s knows when to restart pod

**Health Check Strategy**:
```
Liveness (is process alive?)
  → Yes, keep running
  → No, restart container

Readiness (ready for traffic?)
  → Yes, send requests
  → No, remove from load balancer (don't restart)
```

### Backend Server Status

**Running**: http://localhost:8001

**Endpoints**:
```bash
GET /                       # API info
GET /api/v1/health          # Basic health
GET /api/v1/health/detailed # All services
GET /api/v1/readiness       # K8s readiness
GET /api/v1/liveness        # K8s liveness
GET /metrics                # Prometheus metrics
GET /docs                   # Swagger UI
GET /redoc                  # ReDoc UI
GET /openapi.json           # OpenAPI schema
```

**Current Health**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "services": {
    "postgresql": "healthy",
    "redis": "healthy",
    "ollama": "healthy"
  }
}
```

---

## Key Technical Decisions

### 1. PostgreSQL + SQLAlchemy

**Question**: Why not just use Weaviate or raw SQL?

**Answer**:
- LangGraph **requires** PostgreSQL for agent checkpointing
- LangGraph uses SQLAlchemy internally
- We need both: PostgreSQL for metadata, Weaviate for vectors
- SQLAlchemy provides migrations (Alembic)

**Tradeoff**:
- Pro: Required by LangGraph, mature ecosystem
- Con: Heavier than raw SQL, learning curve

### 2. Pluggable Architecture

**Question**: Why interfaces instead of direct implementation?

**Answer**:
```python
# Without interfaces
from plugins.embeddings.local_embeddings import LocalEmbeddings
embedder = LocalEmbeddings()  # Hardcoded

# With interfaces
embedder = get_embedding_provider()  # Reads from .env

# Change provider:
# EMBEDDING_PROVIDER=local → EMBEDDING_PROVIDER=openai
# No code changes needed!
```

**Tradeoff**:
- Pro: Swap providers easily, testable, future-proof
- Con: More files, more abstraction

**Decision**: Worth it for production flexibility

### 3. 100% Async

**Question**: Why async everywhere?

**Answer**:
- FastAPI is built for async
- Better performance for I/O (database, Redis, HTTP)
- Scales to more concurrent users
- Consistent patterns across codebase

**Tradeoff**:
- Pro: Better performance, scalability
- Con: More complex (async/await everywhere)

**Decision**: Async is FastAPI best practice

### 4. Pydantic Settings

**Question**: Why not just use os.getenv?

**Answer**:
```python
# os.getenv (simple but error-prone)
port = int(os.getenv("PORT", "8000"))  # Manual parsing
if port < 0 or port > 65535:           # Manual validation
    raise ValueError("Invalid port")

# Pydantic Settings (type-safe)
class Settings(BaseSettings):
    port: int = 8000  # Auto-parsed, auto-validated
```

**Tradeoff**:
- Pro: Type safety, validation, IDE autocomplete
- Con: More code, dependency

**Decision**: Worth it for production reliability

---

## File Structure Summary

```
ai-systems-starter/
├── .gitignore                    # Security (no secrets committed)
├── .env.example                  # Config template
├── LICENSE                       # Apache 2.0
├── NOTICE                        # Copyright notice
├── README.md                     # Project overview
├── Makefile                      # 25+ commands
│
├── infra/docker/
│   └── docker-compose.yml        # 5 services
│
├── backend/                      # FastAPI application
│   ├── main.py                   # App entry (144 lines)
│   ├── config.py                 # Settings (190 lines)
│   ├── requirements.txt          # 60+ deps
│   │
│   ├── core/                     # Infrastructure
│   │   ├── database.py           # SQLAlchemy (95 lines)
│   │   └── redis_client.py       # Redis (192 lines)
│   │
│   ├── models/                   # Database models
│   │   └── document.py           # Document (127 lines)
│   │
│   ├── interfaces/               # Abstract classes
│   │   ├── embeddings.py         # (58 lines)
│   │   └── vector_db.py          # (146 lines)
│   │
│   ├── plugins/                  # Implementations
│   │   ├── embeddings/
│   │   │   └── local_embeddings.py  # (81 lines)
│   │   └── vector_dbs/
│   │       └── weaviate_db.py       # (215 lines)
│   │
│   └── api/v1/
│       └── health.py             # Health checks (189 lines)
│
├── docs/                         # Documentation
│   ├── README.md                 # Docs overview
│   ├── COMPLETED_WORK.md         # This file
│   ├── DAY2_SUMMARY.md           # Day 2 technical details
│   ├── PRODUCTION_ROADMAP.md     # Beyond Day 8
│   └── VERIFICATION_COMMANDS.md  # Health check commands
│
└── venv/                         # Python virtual environment
```


---

## Testing & Verification

### Service Health

```bash
# All services
curl http://localhost:8001/api/v1/health/detailed

# Individual services
docker exec ai-systems-postgres pg_isready
docker exec ai-systems-redis redis-cli ping
curl http://localhost:8080/v1/.well-known/ready  # Weaviate
curl http://localhost:11434  # Ollama
```

### Database Verification

```bash
# Connect to PostgreSQL
psql postgresql://postgres:postgres@localhost:5432/ai_systems

# Check tables
\dt

# Should see:
# documents table created by SQLAlchemy
```

### Backend Verification

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Response:
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development"
}

# API docs
open http://localhost:8001/docs
```

---

## What's Working

- All 5 Docker services running
- PostgreSQL database created
- Backend server responding
- Health checks passing
- Prometheus metrics exposed
- API documentation generated
- Development workflow (Makefile)

---

## What's Next: Day 3

### PDF Ingestion Pipeline

**Goal**: Upload PDF → Extract text → Generate embeddings → Store in Weaviate

**Files to Create**:

1. `backend/api/v1/ingest.py`
   - POST /api/v1/ingest/upload
   - GET /api/v1/ingest/{document_id}

2. `backend/services/pdf_service.py`
   - Extract text with pdfplumber
   - Chunk with LangChain

3. `backend/services/embedding_service.py`
   - Generate embeddings (batch processing)

4. `backend/services/vector_service.py`
   - Store in Weaviate

5. `backend/workers/ingestion_worker.py`
   - Background processing (Redis queue)

6. `backend/api/v1/websocket.py`
   - Real-time progress updates

**Flow**:
```
User uploads PDF
  ↓
Store in MinIO
  ↓
Create Document record (status=QUEUED)
  ↓
Add job to Redis queue
  ↓
Worker picks up job
  ↓
Extract text → Chunk → Embed → Store in Weaviate
  ↓
Update Document status (COMPLETED)
  ↓
Send WebSocket notification
```

**Estimated Lines**: ~800 lines of new code

**Tutorial Video**: Will explain every line of the ingestion pipeline

---

## Learning Resources Created

1. **[PRODUCTION_ROADMAP.md](PRODUCTION_ROADMAP.md)** - Beyond MVP
2. **[VERIFICATION_COMMANDS.md](VERIFICATION_COMMANDS.md)** - Health checks

---

## Quick Commands Reference

```bash
# Start everything
make up

# Check health
make health

# View logs
make logs

# Stop everything
make down

# Start backend (after make up)
source venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8001

# Test endpoints
curl http://localhost:8001/api/v1/health
open http://localhost:8001/docs
```

---

**Completed**: Day 1
**Ready For**: Day 2 - PDF Ingestion Pipeline
**Next Session**: Create video tutorial scripts

**Author**: Tejaswi Mahapatra
**License**: Apache 2.0
