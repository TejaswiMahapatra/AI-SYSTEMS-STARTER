"""
Clause-Aware Chunking Service for Legal Documents

This service intelligently chunks legal documents while preserving their structure:
- Section headers (Article X, Section Y)
- Clause numbers (5.1, 5.1.1, 5.2)
- Sub-clauses and hierarchical relationships

Why clause-aware chunking?
- Legal documents have strict hierarchical structure
- Clause boundaries are semantic boundaries
- Preserving clause numbers enables precise retrieval
- Better than generic chunking for contracts/agreements

Copyright 2025 Tejaswi Mahapatra
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClauseChunk:
    """
    A chunk representing a legal clause or section.

    Attributes:
        text: The full text of the clause
        clause_number: Clause identifier (e.g., "5.1", "5.1.1")
        section_number: Parent section number (e.g., "5")
        section_title: Parent section title (e.g., "Termination")
        chunk_type: Type of chunk (section_header, clause, sub_clause, paragraph)
        chunk_index: Position in document (0-indexed)
        hierarchy_level: Depth in hierarchy (0=section, 1=clause, 2=sub-clause)
    """
    text: str
    clause_number: str
    section_number: str
    section_title: str
    chunk_type: str  
    chunk_index: int
    hierarchy_level: int


class ClauseChunkingService:
    """
    Chunk legal documents while preserving clause structure.

    Handles various legal document formats:
    - Article/Section headers
    - Numbered clauses (1.1, 1.2)
    - Sub-clauses (1.1.1, 1.1.2)
    - Sub-sub-clauses (1.1.1.1)
    - Unnumbered paragraphs

    Example document structure:
        Article 1: Introduction
        1.1 This agreement is between...
        1.2 The effective date is...
            1.2.1 Subject to approval...
    """

    SECTION_HEADER_PATTERN = re.compile(
        r'^(Article|Section|ARTICLE|SECTION|Part|PART)\s+(\d+\.?\d*):?\s*(.*)$',
        re.MULTILINE
    )

    CLAUSE_NUMBER_PATTERN = re.compile(
        r'^(\d+(?:\.\d+)+)\.?\s+(.+)$',
        re.MULTILINE
    )

    LETTERED_CLAUSE_PATTERN = re.compile(
        r'^\(([a-z]|[ivxlcdm]+)\)\s+(.+)$',
        re.MULTILINE | re.IGNORECASE
    )

    def __init__(self):
        """Initialize clause chunking service."""
        self.current_section_number = "0"
        self.current_section_title = "Preamble"

    async def chunk_legal_document(
        self,
        text: str,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1500
    ) -> List[ClauseChunk]:
        """
        Chunk a legal document by clause boundaries.

        Args:
            text: Full document text
            min_chunk_size: Minimum characters per chunk (combine small clauses)
            max_chunk_size: Maximum characters per chunk (split large clauses)

        Returns:
            List of ClauseChunk objects with preserved structure

        Strategy:
            1. Split into paragraphs (double newline)
            2. Detect section headers
            3. Detect clause numbers
            4. Group related sub-clauses
            5. Add section context to each chunk
        """
        chunks: List[ClauseChunk] = []

        text = re.sub(r'\n{3,}', '\n\n', text)  
        text = re.sub(r' +', ' ', text) 

        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

        logger.info(f"Processing {len(paragraphs)} paragraphs for clause detection")

        for para in paragraphs:

            section_match = self.SECTION_HEADER_PATTERN.match(para)
            if section_match:
                section_type = section_match.group(1)
                self.current_section_number = section_match.group(2)
                self.current_section_title = section_match.group(3).strip() or f"{section_type} {self.current_section_number}"

                chunks.append(ClauseChunk(
                    text=para,
                    clause_number=self.current_section_number,
                    section_number=self.current_section_number,
                    section_title=self.current_section_title,
                    chunk_type="section_header",
                    chunk_index=len(chunks),
                    hierarchy_level=0
                ))

                logger.debug(f"Detected section: {self.current_section_number} - {self.current_section_title}")
                continue


            clause_match = self.CLAUSE_NUMBER_PATTERN.match(para)
            if clause_match:
                clause_number = clause_match.group(1)
                clause_text = para 
                hierarchy_level = clause_number.count('.')

                chunk_type = "clause"
                if hierarchy_level >= 2:
                    chunk_type = "sub_clause"

                chunks.append(ClauseChunk(
                    text=clause_text,
                    clause_number=clause_number,
                    section_number=self.current_section_number,
                    section_title=self.current_section_title,
                    chunk_type=chunk_type,
                    chunk_index=len(chunks),
                    hierarchy_level=hierarchy_level
                ))

                logger.debug(f"Detected clause: {clause_number} (level {hierarchy_level})")
                continue

            lettered_match = self.LETTERED_CLAUSE_PATTERN.match(para)
            if lettered_match:
                letter = lettered_match.group(1)
                clause_text = para

                clause_number = f"{self.current_section_number}.{letter}"

                chunks.append(ClauseChunk(
                    text=clause_text,
                    clause_number=clause_number,
                    section_number=self.current_section_number,
                    section_title=self.current_section_title,
                    chunk_type="sub_clause",
                    chunk_index=len(chunks),
                    hierarchy_level=2
                ))

                logger.debug(f"Detected lettered clause: ({letter})")
                continue

            if len(para) > min_chunk_size or chunks:  # Always allow if not first chunk
                chunks.append(ClauseChunk(
                    text=para,
                    clause_number=f"{self.current_section_number}.p{len(chunks)}",
                    section_number=self.current_section_number,
                    section_title=self.current_section_title,
                    chunk_type="paragraph",
                    chunk_index=len(chunks),
                    hierarchy_level=1
                ))

        # Post-processing: Combine very small chunks and split very large ones
        chunks = self._optimize_chunk_sizes(chunks, min_chunk_size, max_chunk_size)

        logger.info(f"Created {len(chunks)} clause-aware chunks")
        self._log_chunk_statistics(chunks)

        return chunks

    def _optimize_chunk_sizes(
        self,
        chunks: List[ClauseChunk],
        min_size: int,
        max_size: int
    ) -> List[ClauseChunk]:
        """
        Optimize chunk sizes by combining small chunks and splitting large ones.

        Rules:
        - Combine consecutive small chunks if total < max_size
        - Split large chunks at sentence boundaries
        - Never merge across section boundaries
        """
        optimized: List[ClauseChunk] = []
        i = 0

        while i < len(chunks):
            current = chunks[i]

            if len(current.text) > max_size:
                split_chunks = self._split_large_chunk(current, max_size)
                optimized.extend(split_chunks)
                i += 1
                continue

            # If chunk is too small, try to combine with next
            if len(current.text) < min_size and i + 1 < len(chunks):
                next_chunk = chunks[i + 1]

                # Only combine if:
                # 1. Same section
                # 2. Combined size < max_size
                # 3. Not section headers
                can_combine = (
                    current.section_number == next_chunk.section_number and
                    len(current.text) + len(next_chunk.text) < max_size and
                    current.chunk_type != "section_header" and
                    next_chunk.chunk_type != "section_header"
                )

                if can_combine:

                    combined_text = f"{current.text}\n\n{next_chunk.text}"
                    combined_clause_num = current.clause_number  

                    combined = ClauseChunk(
                        text=combined_text,
                        clause_number=combined_clause_num,
                        section_number=current.section_number,
                        section_title=current.section_title,
                        chunk_type="combined",
                        chunk_index=len(optimized),
                        hierarchy_level=min(current.hierarchy_level, next_chunk.hierarchy_level)
                    )

                    optimized.append(combined)
                    i += 2  # Skip next chunk (already combined)
                    continue

            # Normal case: add chunk as-is
            optimized.append(current)
            i += 1

        # Reindex
        for idx, chunk in enumerate(optimized):
            chunk.chunk_index = idx

        return optimized

    def _split_large_chunk(self, chunk: ClauseChunk, max_size: int) -> List[ClauseChunk]:
        """
        Split a large chunk into smaller chunks at sentence boundaries.

        Tries to split at:
        1. Period + space + capital letter (sentence boundary)
        2. Newlines
        3. Arbitrary character limit (last resort)
        """
        text = chunk.text
        sub_chunks: List[ClauseChunk] = []

        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)

        current_text = ""
        for sentence in sentences:
            if len(current_text) + len(sentence) < max_size:
                current_text += sentence + " "
            else:
                if current_text.strip():
                    sub_chunks.append(ClauseChunk(
                        text=current_text.strip(),
                        clause_number=f"{chunk.clause_number}.{len(sub_chunks) + 1}",
                        section_number=chunk.section_number,
                        section_title=chunk.section_title,
                        chunk_type=chunk.chunk_type,
                        chunk_index=chunk.chunk_index,
                        hierarchy_level=chunk.hierarchy_level + 1
                    ))

                current_text = sentence + " "

        # Add remaining text
        if current_text.strip():
            sub_chunks.append(ClauseChunk(
                text=current_text.strip(),
                clause_number=f"{chunk.clause_number}.{len(sub_chunks) + 1}",
                section_number=chunk.section_number,
                section_title=chunk.section_title,
                chunk_type=chunk.chunk_type,
                chunk_index=chunk.chunk_index,
                hierarchy_level=chunk.hierarchy_level + 1
            ))

        logger.debug(f"Split large chunk ({len(text)} chars) into {len(sub_chunks)} sub-chunks")

        return sub_chunks if sub_chunks else [chunk]

    def _log_chunk_statistics(self, chunks: List[ClauseChunk]):
        """Log statistics about chunk distribution."""
        if not chunks:
            return

        type_counts = {}
        for chunk in chunks:
            type_counts[chunk.chunk_type] = type_counts.get(chunk.chunk_type, 0) + 1

        total_chars = sum(len(chunk.text) for chunk in chunks)
        avg_size = total_chars / len(chunks) if chunks else 0

        logger.info(f"Chunk statistics:")
        logger.info(f"  Total chunks: {len(chunks)}")
        logger.info(f"  Average size: {avg_size:.0f} characters")
        logger.info(f"  Distribution: {type_counts}")

    def chunk_to_dict(self, chunk: ClauseChunk) -> Dict[str, Any]:
        """
        Convert ClauseChunk to dictionary format for vector database storage.

        Adds all clause metadata for filtering and retrieval.
        """
        return {
            "text": chunk.text,
            "chunk_index": chunk.chunk_index,
            "clause_number": chunk.clause_number,
            "section_number": chunk.section_number,
            "section_title": chunk.section_title,
            "chunk_type": chunk.chunk_type,
            "hierarchy_level": chunk.hierarchy_level,
            "char_count": len(chunk.text)
        }

    async def chunk_with_metadata(
        self,
        text: str,
        document_metadata: dict,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1500
    ) -> List[Dict[str, Any]]:
        """
        Chunk text and attach both clause metadata and document metadata.

        Args:
            text: Full document text
            document_metadata: Document-level metadata (document_id, filename, etc.)
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters

        Returns:
            List of dictionaries ready for vector database insertion

        Example:
            >>> chunks = await chunker.chunk_with_metadata(
            ...     text=contract_text,
            ...     document_metadata={
            ...         "document_id": "abc-123",
            ...         "filename": "contract.pdf",
            ...         "document_type": "legal_contract"
            ...     }
            ... )
            >>> # Each chunk has: text, clause_number, section_title, document_id, etc.
        """
        chunks = await self.chunk_legal_document(text, min_chunk_size, max_chunk_size)

        chunks_with_metadata = []
        for chunk in chunks:
            chunk_dict = self.chunk_to_dict(chunk)
            chunk_dict.update(document_metadata)  
            chunks_with_metadata.append(chunk_dict)

        return chunks_with_metadata


_clause_chunking_service: Optional[ClauseChunkingService] = None


def get_clause_chunking_service() -> ClauseChunkingService:
    """
    Get the global clause chunking service instance.

    Returns:
        ClauseChunkingService: Singleton instance
    """
    global _clause_chunking_service
    if _clause_chunking_service is None:
        _clause_chunking_service = ClauseChunkingService()
    return _clause_chunking_service
