# AI Systems Starter

**A production-ready blueprint for building AI-powered applications with RAG, LangGraph agents, and LLMOps.**

> **Goal**: Help students and enterprises go from idea to production AI system in days, not months.

> **100% Open Source**: Runs completely locally with Ollama + sentence-transformers. No API keys required!

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-required-blue.svg)](https://www.docker.com/)

---

## What You Get

This starter kit includes a **complete, working AI system** for contract analysis, demonstrating:

### Core AI Features
- **PDF Ingestion Pipeline** (parse → chunk → embed → store)
- **Vector Search** (Weaviate for semantic retrieval)
- **RAG (Retrieval-Augmented Generation)** (context-aware Q&A)
- **LangGraph Agents** (deep reasoning with planning + tools)
- **Background Workers** (Redis Streams for async processing)

### Production Features
- **LLMOps** (LangSmith tracing, cost tracking, prompt versioning)
- **Testing** (unit, integration, LLM evaluation with DeepEval)
- **Observability** (Prometheus + Grafana dashboards)
- **Modern Frontend** (Next.js + Vercel AI SDK for streaming chat)
- **Deployment Ready** (Docker Compose, Kubernetes manifests)

---

## Quick Start

### Prerequisites
- **Docker** & **Docker Compose** ([Install](https://docs.docker.com/get-docker/))
- **Python 3.11+** ([Install](https://www.python.org/downloads/))
- **Node.js 18+** ([Install](https://nodejs.org/)) _(for frontend)_

**That's it!** No API keys required. Everything runs locally for free.

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/TejaswiMahapatra/ai-systems-starter.git
cd ai-systems-starter
# 2. Run initialization (sets up everything)
make init

# 3. Pull an open-source LLM (while services start)
docker exec -it ai-systems-ollama ollama pull llama3.1:8b

# 4. Start development environment  
make dev
```

**That's it!** You now have:
- Backend API running at http://localhost:8000/docs
- Ollama (local LLM) at http://localhost:11434
- Weaviate (vector DB) at http://localhost:8080
- PostgreSQL, Redis, MinIO all running
- Grafana dashboards at http://localhost:3001

**Want to use paid APIs?** Edit `.env` and set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`
- Grafana dashboards at http://localhost:3001

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│              (Next.js + Vercel AI SDK)                  │
│  - Upload PDFs                                          │
│  - Chat interface (streaming)                           │
│  - Agent interactions                                   │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP API
                     │
┌────────────────────▼────────────────────────────────────┐
│                  BACKEND                                │
│              (FastAPI + LangGraph)                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ PDF Service  │  │   Embeddings │  │ LangGraph    │   │
│  │ (pdfplumber) │  │   (OpenAI)   │  │ Agents       │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Redis Queue  │  │   Workers    │  │ Policy Engine│   │
│  │ (Background) │  │   (Async)    │  │ (OPA/Rego)   │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │
┌────────────────────▼────────────────────────────────────┐
│                 DATA LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  PostgreSQL  │  │   Weaviate   │  │     MinIO    │   │
│  │  (Metadata)  │  │   (Vectors)  │  │  (S3-compat) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

For detailed architecture, see [docs/architecture/overview.md](./docs/architecture/overview.md)

---

## Usage Examples

### 1. Upload a PDF Contract

```bash
curl -X POST -F "file=@examples/contracts/sample.pdf" \
  http://localhost:8000/api/ingest
```

### 2. Query the Contract

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the termination clause?",
    "contract_id": "abc123"
  }'
```

### 3. Use the Deep Agent

```bash
curl -X POST http://localhost:8000/api/agent/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Find all risky clauses and explain why",
    "contract_id": "abc123"
  }'
```

---

## Available Commands

```bash
make help           # Show all available commands
make init           # Initial setup (run once)
make dev            # Start development environment
make down           # Stop all services
make clean          # Remove all data (fresh start)
make test           # Run all tests
make seed           # Load sample data
make logs           # View logs from all services
make status         # Show status of all services
```

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

See [docs/examples/](./docs/examples/) for full tutorials.

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

**Ready to build your AI system?** Run `make init` and let's go! 🚀
