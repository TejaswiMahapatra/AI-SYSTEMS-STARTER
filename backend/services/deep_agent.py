"""
LangGraph Deep Agent using ReAct Pattern

Uses LangGraph's create_react_agent for intelligent tool selection and execution.
The agent automatically:
- Reasons about which tools to use
- Executes tools based on the question
- Iterates until it has enough information
- Synthesizes a final answer

Copyright 2025 Tejaswi Mahapatra
"""

import logging
from typing import Dict, Any, List
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from backend.config import settings
from backend.services.agent_tools import get_agent_tools
from backend.prompts import get_prompt_manager

logger = logging.getLogger(__name__)


class DeepAgent:
    """
    LangGraph ReAct agent with automatic tool selection.

    The agent uses the ReAct pattern:
    1. Reason - Think about what tool to use
    2. Act - Execute the tool
    3. Observe - See the result
    4. Repeat until answer is ready
    """

    def __init__(self):
        self.agent_tools_service = get_agent_tools()
        self.prompt_manager = get_prompt_manager()

        self.llm = ChatOllama(
            base_url=settings.ollama_url,
            model=settings.ollama_model,
            temperature=0.1
        )

        self.tools = self._create_langchain_tools()

        self.system_prompt = self.prompt_manager.load_prompt("agent_system")

        self.agent = create_react_agent(
            self.llm,
            self.tools,
            state_modifier=SystemMessage(content=self.system_prompt)
        )

    def _create_langchain_tools(self) -> List:
        """Create LangChain-compatible tools from our agent tools."""

        @tool
        async def rag_query(question: str, top_k: int = 3, collection_name: str = "Default") -> Dict[str, Any]:
            """
            Ask a question about the documents using the full RAG pipeline.

            This tool combines semantic search, context building, and LLM generation
            to provide a complete answer with sources and confidence scores.

            Args:
                question: The question to ask about the documents
                top_k: Number of relevant sources to retrieve (default: 3, max: 5)
                collection_name: Which document collection to search (default: "Default")

            Returns:
                Dict with 'answer', 'sources', 'confidence', and 'num_sources'
            """
            return await self.agent_tools_service.rag_query(
                question=question,
                collection_name=collection_name,
                top_k=min(top_k, 5)  
            )

        @tool
        async def analyze_content(content: str, analysis_instructions: str) -> Dict[str, Any]:
            """
            Analyze content with custom instructions.

            Args:
                content: The content to analyze
                analysis_instructions: What aspect to analyze (e.g., "identify risks", "summarize key points")

            Returns:
                Analysis results
            """
            return await self.agent_tools_service.analyze_content(
                content=content,
                analysis_instructions=analysis_instructions
            )

        @tool
        async def compare_content(content1: str, content2: str, comparison_aspect: str = "differences and similarities") -> Dict[str, Any]:
            """
            Compare two pieces of content.

            Args:
                content1: First piece of content
                content2: Second piece of content
                comparison_aspect: What to compare (default: "differences and similarities")

            Returns:
                Comparison results
            """
            return await self.agent_tools_service.compare_content(
                content1=content1,
                content2=content2,
                comparison_aspect=comparison_aspect
            )

        @tool
        async def generate_report(findings_summary: str, report_type: str = "detailed_analysis", title: str = "Report") -> Dict[str, Any]:
            """
            Generate a structured report from findings.

            Args:
                findings_summary: Summary of findings to include
                report_type: Type of report (e.g., "executive_summary", "detailed_analysis")
                title: Report title

            Returns:
                Formatted report
            """
            findings = [{"summary": findings_summary}]

            return await self.agent_tools_service.generate_report(
                findings=findings,
                report_type=report_type,
                title=title
            )

        return [rag_query, analyze_content, compare_content, generate_report]

    async def run(
        self,
        question: str,
        collection_name: str = "Default"
    ) -> Dict[str, Any]:
        """
        Run the deep agent on a question.

        The agent will automatically:
        - Decide which tools to use
        - Execute them in the right order
        - Synthesize a final answer

        Args:
            question: User's question
            collection_name: Document collection to search

        Returns:
            Complete execution trace with answer and metadata
        """
        logger.info(f"Starting deep agent for question: {question}")

        try:
            enhanced_question = f"{question}\n\nNote: Search in the '{collection_name}' collection."

            result = await self.agent.ainvoke({
                "messages": [HumanMessage(content=enhanced_question)]
            })

            messages = result.get("messages", [])
            final_answer = ""

            if messages:
                last_message = messages[-1]
                final_answer = last_message.content

            tool_calls = []
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tool_calls.append({
                            "tool": tool_call.get("name"),
                            "args": tool_call.get("args"),
                        })

            logger.info(f"Agent execution complete. Used {len(tool_calls)} tools.")

            return {
                "question": question,
                "answer": final_answer,
                "tool_calls": tool_calls,
                "num_tools_used": len(tool_calls),
                "metadata": {
                    "collection": collection_name,
                    "model": settings.ollama_model
                }
            }

        except Exception as e:
            logger.error(f"Error running deep agent: {e}", exc_info=True)
            return {
                "question": question,
                "answer": f"Agent execution error: {str(e)}",
                "error": str(e)
            }


_deep_agent = None


def get_deep_agent() -> DeepAgent:
    """Get the global DeepAgent instance."""
    global _deep_agent
    if _deep_agent is None:
        _deep_agent = DeepAgent()
    return _deep_agent
