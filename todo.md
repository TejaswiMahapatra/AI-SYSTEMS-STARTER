# TODO

## Core System (Completed)
- Clause-aware chunking
- PDF ingestion pipeline with background workers
- Redis Pub/Sub for real-time progress
- Vector search with Weaviate
- RAG pipeline with human-friendly NLG
- LangGraph agents with multi-tool reasoning
- WebSocket infrastructure
- Makefile for easy system management
- Documentation (Architecture, Getting Started, README)

## Performance & Reliability
- **Agent timeout issues** - Fixed (increased timeout 120s -> 300s, reduced chunks 5 -> 3)
- **Slow Ollama responses** - Consider smaller model or streaming
- Improve retrieval quality (better chunk matching)
- Add caching for embeddings
- Add caching for frequent queries
- Connection pooling optimization

## Production Features
- Authentication (JWT)
- Rate limiting
- Comprehensive test suite (unit + integration)
- LLM evaluation with DeepEval
- Prometheus metrics (partial - endpoint exists)
- Grafana dashboards
- Error recovery and retry logic
- Input validation and sanitization

## Deployment
- Kubernetes manifests
- CI/CD pipeline
- Health checks and readiness probes
- Log aggregation
- Backup and recovery procedures

## Frontend
- Next.js + Vercel AI SDK
- Drag & drop PDF upload
- Real-time chat with streaming
- WebSocket progress indicators
- Document management UI

## Future Enhancements
- Multi-document comparison
- Document versioning
- Export reports (PDF, DOCX)
- Custom clause templates
- Batch document processing
- API key management
- Usage analytics

## LangGraph Agent
- Make it better, more robust