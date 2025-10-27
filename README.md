# Clause.AI

**A production-ready blueprint for building AI-powered applications with RAG, LangGraph agents, and LLMOps.**

> **Goal**: Help students and enterprises go from idea to production AI system in days, not months.

> **100% Open Source**: Runs completely locally with Ollama + sentence-transformers. No API keys required!

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

---

## What You Get

This starter kit includes a **complete, working AI system** for contract analysis, demonstrating:

### Core Features (Implemented)
- **Clause-Aware Chunking** - Preserves legal document structure (clause numbers, hierarchy, context)
- **PDF Ingestion Pipeline** - Background workers with Redis queue for async processing
- **Vector Search** - Weaviate with 384D embeddings (all-MiniLM-L6-v2) and HNSW indexing
- **RAG (Retrieval-Augmented Generation)** - Context-aware Q&A with human-friendly responses
- **LangGraph Agents** - Multi-tool reasoning (rag_query, analyze_content, compare_content, generate_report)
- **Real-time Progress Updates** - Redis Pub/Sub + WebSocket streaming for document processing status
- **Human-Friendly NLG** - Conversational AI responses with plain language, bullets, and "Key Takeaway" sections

### Production Features
- **Async/Await Throughout** - FastAPI with type hints and Pydantic validation
- **Plugin Architecture** - Easy swapping of LLM providers, embeddings, and vector databases
- **Docker Compose** - Local development with Postgres, Weaviate, Redis, MinIO, Ollama
- **Makefile Commands** - Single command (`make run`) to start entire system
- **Comprehensive Documentation** - Architecture diagrams, API docs, getting started guide

---

## Quick Start

### Prerequisites
- **Docker** & **Docker Compose** ([Install](https://docs.docker.com/get-docker/))
- **Python 3.11+** ([Install](https://www.python.org/downloads/))

**That's it!** No API keys required. Everything runs locally for free.

### Installation

```bash
# Clone the repository
git clone https://github.com/TejaswiMahapatra/ai-systems-starter.git
cd ai-systems-starter

# Start everything with one command
make run
```

**Press `Ctrl+C` to stop.**

This single command:
- Starts all Docker services (Postgres, Weaviate, Redis, MinIO, Ollama)
- Pulls the Ollama model if needed (llama3.1:8b)
- Starts the backend API + ingestion worker together

**You now have:**
- Backend API: http://localhost:8000/docs
- Ollama (local LLM): http://localhost:11434
- Weaviate (vector DB): http://localhost:8080
- PostgreSQL, Redis, MinIO all running

**Want to use paid APIs?** Edit `.env` and set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`

---

## Architecture Overview

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

**Learn more:**
- [Getting Started Guide](docs/getting-started.md) - Complete setup and testing walkthrough
- [Architecture Documentation](ARCHITECTURE.md) - Detailed technical architecture

---

## Usage Examples

### 1. Upload a PDF Contract

```bash
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -F "file=@examples/contracts/sample_clause_contract.pdf" \
  -F "collection_name=Default"
```

**Returns:** `document_id` (save this for queries)

**Watch your terminal** - the worker processes the document in real-time with clause-aware chunking.

### 2. Check Processing Status

```bash
curl http://localhost:8000/api/v1/ingest/status/{document_id}
```

**Returns:** Status, number of chunks, processing time

### 3. Query with RAG

```bash
curl -X POST http://localhost:8000/api/v1/query/rag \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the termination clauses?",
    "collection_name": "Default",
    "top_k": 3
  }'
```

**Returns:** Human-friendly answer with sources and confidence score

### 4. Use the Agent

```bash
curl -X POST http://localhost:8000/api/v1/query/agent \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize the key terms and risks",
    "collection_name": "Default"
  }'
```

**Returns:** Agent uses multiple tools to analyze and synthesize a comprehensive answer

---

## Available Commands

```bash
make help           # Show all available commands
make run            # Start complete system (backend + worker + infra)
make stop-all       # Stop all processes
make status         # Show status of all services
make logs           # View logs from all services
make shell-postgres # Open PostgreSQL shell
make shell-redis    # Open Redis CLI
make ollama-list    # Show downloaded Ollama models
```

See the [Makefile](Makefile) for all available commands.

---

## Extension Points

This starter is designed to be **easily customizable**:

### Swap Embedding Provider
```python
# backend/plugins/embeddings/custom_embeddings.py
from interfaces.embeddings import EmbeddingProvider

class CustomEmbeddings(EmbeddingProvider):
    async def embed(self, texts):
        # Your implementation
        pass
```

### Add Custom Agent Tool
```python
# backend/tools/custom_tool.py
from langchain_core.tools import tool

@tool
def my_custom_tool(query: str) -> str:
    """Description of what this tool does."""
    # Your logic here
    return result
```

### Swap Vector Database
```python
# backend/plugins/vector_dbs/pinecone_db.py
from interfaces.vector_db import VectorDBInterface

class PineconeDB(VectorDBInterface):
    async def search(self, vector, limit):
        # Your implementation
        pass
```

---

## Tech Stack


**Backend** FastAPI , Async, type hints, auto-docs
**Orchestration** LangGraph , State management, checkpointing
**Vector DB** Weaviate , Easy to use, hybrid search
**Database** PostgreSQL , Reliable, JSONB support
**Cache/Queue** Redis , Fast, simple, dual-purpose
**Storage** MinIO , S3-compatible, local dev
**Frontend** Next.js 14 , App Router, Server Components
**AI SDK** Vercel AI SDK , Streaming, React hooks 
**Observability** Prometheus + Grafana , Industry standard
**LLMOps** LangSmith , Trace every agent step

---

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## License

Apache License 2.0 - see [LICENSE](./LICENSE) for details.

This project is licensed under the Apache License 2.0, which includes explicit patent grants and trademark protection. This makes it safe for both personal and enterprise use.

---

## Learn More

- **Documentation**: [docs/](./docs/)
- **Video Tutorial**: https://youtu.be/MNGdi4wZWsE
- **Community**: [GitHub Discussions](https://github.com/TejaswiMahapatra/ai-systems-starter/discussions)
- **Issues**: [GitHub Issues](https://github.com/TejaswiMahapatra/ai-systems-starter/issues)

---

## Author

**Tejaswi Mahapatra**

Created and maintained by [Tejaswi Mahapatra](https://github.com/TejaswiMahapatra). This project is the result of extensive research into production AI systems, LLMOps best practices, and developer experience design.

---

## Acknowledgments

Built with ❤️ for the AI community. Special thanks to:
- [LangChain](https://langchain.com/) for LangGraph
- [Vercel](https://vercel.com/) for the AI SDK
- [Weaviate](https://weaviate.io/) for vector search
- Everyone building open-source AI tools

---

**Ready to build your AI system?** Run `make run` and let's go! 🚀
