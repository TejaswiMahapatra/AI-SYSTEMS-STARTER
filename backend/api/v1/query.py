"""
RAG Query API - Retrieval-Augmented Generation for contract Q&A.

Copyright 2025 Tejaswi Mahapatra
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_service import VectorService
from backend.services.llm_service import get_llm_service
from backend.services.deep_agent import get_deep_agent
from backend.prompts import get_prompt_manager

router = APIRouter(prefix="/query", tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """RAG query request."""
    question: str = Field(..., min_length=3, max_length=500)
    document_id: Optional[str] = None
    collection_name: str = "Default"
    top_k: int = Field(5, ge=1, le=20)


class SourceInfo(BaseModel):
    """Source clause information."""
    clause_number: Optional[str] = None
    chunk_type: Optional[str] = None
    section_title: Optional[str] = None
    text: str
    score: float
    document_id: str
    page_number: int


class QueryResponse(BaseModel):
    """RAG query response."""
    answer: str
    sources: List[SourceInfo]
    confidence: float
    metadata: dict


@router.post("/rag", response_model=QueryResponse)
async def rag_query(request: QueryRequest):
    """
    RAG endpoint - retrieves relevant context and generates answer.

    Example:
        POST /api/v1/query/rag
        {"question": "What are the termination conditions?", "top_k": 5}
    """
    try:
        logger.info(f"RAG query: {request.question}")

        embedding_service = EmbeddingService()
        query_vector = await embedding_service.embed_single(request.question)

        vector_service = VectorService()

        if not await vector_service.collection_exists(request.collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{request.collection_name}' not found. Upload documents first."
            )

        search_results = await vector_service.search(
            collection_name=request.collection_name,
            query_vector=query_vector,
            top_k=request.top_k,
            metadata_filter={"document_id": request.document_id} if request.document_id else None
        )

        if not search_results:
            raise HTTPException(
                status_code=404,
                detail="No relevant information found. Try rephrasing or upload more documents."
            )

        logger.info(f"Found {len(search_results)} relevant chunks")

        context_parts = []
        for result in search_results:
            clause_info = ""
            if result.metadata.get('clause_number'):
                clause_info = f"Clause {result.metadata.get('clause_number')}"
                if result.metadata.get('chunk_type'):
                    clause_info += f" ({result.metadata.get('chunk_type')})"
                if result.metadata.get('section_title'):
                    clause_info += f" - {result.metadata.get('section_title')}"
                clause_info += ":\n"
            context_parts.append(f"{clause_info}{result.text}")

        context = "\n\n---\n\n".join(context_parts)

        prompt_manager = get_prompt_manager()
        prompt = prompt_manager.format_prompt(
            "rag_answer",
            question=request.question,
            context=context
        )

        llm_service = get_llm_service()
        answer = await llm_service.generate(prompt, max_tokens=500)

        logger.info("Generated answer")

        avg_score = sum(r.score for r in search_results) / len(search_results)
        confidence = min(avg_score, 1.0)

        sources = [
            SourceInfo(
                clause_number=result.metadata.get('clause_number'),
                chunk_type=result.metadata.get('chunk_type'),
                section_title=result.metadata.get('section_title'),
                text=result.text[:200] + "..." if len(result.text) > 200 else result.text,
                score=round(result.score, 3),
                document_id=result.metadata.get('document_id', ''),
                page_number=result.metadata.get('page_number', 0)
            )
            for result in search_results
        ]

        return QueryResponse(
            answer=answer.strip(),
            sources=sources,
            confidence=round(confidence, 3),
            metadata={
                "num_sources": len(search_results),
                "avg_similarity": round(avg_score, 3),
                "model": llm_service.model_name,
                "collection": request.collection_name,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/search", response_model=List[SourceInfo])
async def semantic_search(request: QueryRequest):
    """
    Semantic search only - no LLM generation.

    Example:
        POST /api/v1/query/search
        {"question": "termination clause", "top_k": 10}
    """
    try:
        embedding_service = EmbeddingService()
        query_vector = await embedding_service.embed_single(request.question)

        vector_service = VectorService()

        if not await vector_service.collection_exists(request.collection_name):
            raise HTTPException(
                status_code=404,
                detail=f"Collection '{request.collection_name}' not found"
            )

        results = await vector_service.search(
            collection_name=request.collection_name,
            query_vector=query_vector,
            top_k=request.top_k,
            metadata_filter={"document_id": request.document_id} if request.document_id else None
        )

        return [
            SourceInfo(
                clause_number=r.metadata.get('clause_number'),
                chunk_type=r.metadata.get('chunk_type'),
                section_title=r.metadata.get('section_title'),
                text=r.text,
                score=round(r.score, 3),
                document_id=r.metadata.get('document_id', ''),
                page_number=r.metadata.get('page_number', 0)
            )
            for r in results
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


class DeepAgentRequest(BaseModel):
    """Deep agent request."""
    question: str = Field(..., min_length=3, max_length=1000)
    collection_name: str = "Default"


class DeepAgentResponse(BaseModel):
    """Deep agent response."""
    question: str
    answer: str
    tool_calls: List[dict]
    num_tools_used: int
    metadata: dict


@router.post("/agent", response_model=DeepAgentResponse)
async def deep_agent_query(request: DeepAgentRequest):
    """
    Deep agent query with LangGraph ReAct pattern.

    The agent automatically:
    - Decides which tools to use
    - Executes them in the right order
    - Synthesizes a comprehensive answer

    Works for any type of question: Q&A, analysis, comparison, reports, etc.

    Example:
        POST /api/v1/query/agent
        {"question": "Summarize the key risks in this contract", "collection_name": "Default"}
    """
    try:
        logger.info(f"Deep agent query: {request.question}")

        deep_agent = get_deep_agent()
        result = await deep_agent.run(
            question=request.question,
            collection_name=request.collection_name
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return DeepAgentResponse(
            question=result["question"],
            answer=result["answer"],
            tool_calls=result["tool_calls"],
            num_tools_used=result["num_tools_used"],
            metadata=result["metadata"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deep agent query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")
