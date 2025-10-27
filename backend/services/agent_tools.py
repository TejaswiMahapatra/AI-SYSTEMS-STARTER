"""
Generic Agent Tools for LangGraph Deep Agent

Domain-agnostic tools that work for any type of document or question:
1. rag_query - Use the full RAG pipeline (search + context + LLM answer)
2. analyze_content - Analyze any text with custom instructions
3. compare_content - Compare any two pieces of text
4. generate_report - Generate structured reports from findings

The agent uses RAG as the primary knowledge retrieval tool,
avoiding duplication of search functionality.

Copyright 2025 Tejaswi Mahapatra
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_service import VectorService
from backend.services.llm_service import get_llm_service
from backend.prompts import get_prompt_manager

logger = logging.getLogger(__name__)


class RAGQueryInput(BaseModel):
    """Input for rag_query tool."""
    question: str = Field(description="Question to ask about the documents")
    collection_name: str = Field(default="Default")
    top_k: int = Field(default=5)
    document_id: Optional[str] = Field(default=None)


class AnalyzeInput(BaseModel):
    """Input for analyze_content tool."""
    content: str = Field(description="Content to analyze")
    analysis_instructions: str = Field(description="What aspect to analyze")


class CompareInput(BaseModel):
    """Input for compare_content tool."""
    content1: str = Field(description="First piece of content")
    content2: str = Field(description="Second piece of content")
    comparison_aspect: str = Field(default="differences and similarities")


class ReportInput(BaseModel):
    """Input for generate_report tool."""
    findings: List[Dict[str, Any]] = Field(description="List of findings to include")
    report_type: str = Field(description="Type of report")
    title: str = Field(default="Report")


class AgentTools:
    """Generic, domain-agnostic tools for the LangGraph agent."""

    def __init__(self):
        self.vector_service = VectorService()
        self.embedding_service = EmbeddingService()
        self.llm_service = get_llm_service()
        self.prompt_manager = get_prompt_manager()

    async def rag_query(
        self,
        question: str,
        collection_name: str = "Default",
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query documents using the full RAG pipeline.

        This combines semantic search + context building + LLM generation.
        Returns a complete answer with sources and confidence.

        Works for: any document type and any question.
        """
        logger.info(f"RAG query: {question}")

        try:
            query_vector = await self.embedding_service.embed_single(question)
            metadata_filter = {"document_id": document_id} if document_id else None
            search_results = await self.vector_service.search(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=top_k,
                metadata_filter=metadata_filter
            )

            if not search_results:
                return {
                    "answer": "No relevant information found in the documents.",
                    "sources": [],
                    "confidence": 0.0
                }

            context_parts = []
            for i, result in enumerate(search_results):
                context_parts.append(f"Source {i+1} (relevance: {result.score:.3f}):\n{result.text}")

            context = "\n\n---\n\n".join(context_parts)

            prompt = self.prompt_manager.format_prompt(
                "rag_answer",
                question=question,
                context=context
            )

            answer = await self.llm_service.generate(prompt, max_tokens=800)

            avg_score = sum(r.score for r in search_results) / len(search_results)

            logger.info(f"RAG query complete. Confidence: {avg_score:.3f}")

            return {
                "answer": answer,
                "sources": [
                    {
                        "text": r.text[:300],
                        "score": r.score,
                        "metadata": r.metadata
                    }
                    for r in search_results
                ],
                "confidence": round(avg_score, 3),
                "num_sources": len(search_results)
            }

        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": [],
                "confidence": 0.0
            }

    async def analyze_content(
        self,
        content: str,
        analysis_instructions: str
    ) -> Dict[str, Any]:
        """
        Generic content analysis with custom instructions.

        Examples:
        - "analyze legal risks and obligations"
        - "identify key themes and sentiment"
        - "extract action items and deadlines"
        """
        logger.info(f"Analyzing content: {analysis_instructions}")

        try:
            prompt = self.prompt_manager.format_prompt(
                "analyze_content",
                analysis_instructions=analysis_instructions,
                content=content
            )

            analysis = await self.llm_service.generate(
                prompt,
                max_tokens=1000,
                temperature=0.1
            )

            return {
                "content_preview": content[:300],
                "instructions": analysis_instructions,
                "analysis": analysis
            }

        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return {"error": str(e)}

    async def compare_content(
        self,
        content1: str,
        content2: str,
        comparison_aspect: str = "differences and similarities"
    ) -> Dict[str, Any]:
        """
        Generic content comparison.

        Works for: contract clauses, product versions, research findings, any text
        """
        logger.info(f"Comparing content: {comparison_aspect}")

        try:
            prompt = self.prompt_manager.format_prompt(
                "compare_content",
                content1=content1,
                content2=content2,
                comparison_aspect=comparison_aspect
            )

            comparison = await self.llm_service.generate(
                prompt,
                max_tokens=1200,
                temperature=0.1
            )

            return {
                "content1_preview": content1[:200],
                "content2_preview": content2[:200],
                "comparison_aspect": comparison_aspect,
                "comparison": comparison
            }

        except Exception as e:
            logger.error(f"Error comparing content: {e}")
            return {"error": str(e)}

    async def generate_report(
        self,
        findings: List[Dict[str, Any]],
        report_type: str,
        title: str = "Report"
    ) -> Dict[str, Any]:
        """
        Generate structured reports from findings.

        Report types: executive_summary, detailed_analysis, comparison_report, action_items
        """
        logger.info(f"Generating {report_type} report: {title}")

        try:
            findings_text = "\n\n".join([
                f"Finding {i+1}:\n{str(finding)}"
                for i, finding in enumerate(findings)
            ])

            prompt = self.prompt_manager.format_prompt(
                "generate_report",
                report_type=report_type,
                title=title,
                findings_text=findings_text
            )

            report = await self.llm_service.generate(
                prompt,
                max_tokens=1500,
                temperature=0.2
            )

            return {
                "title": title,
                "report_type": report_type,
                "num_findings": len(findings),
                "report": report
            }

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"error": str(e)}


_agent_tools = None


def get_agent_tools() -> AgentTools:
    """Get the global AgentTools instance."""
    global _agent_tools
    if _agent_tools is None:
        _agent_tools = AgentTools()
    return _agent_tools
