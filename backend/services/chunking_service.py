"""
Text Chunking Service

This service splits long text into smaller chunks for embedding.

Why chunking?
- Embedding models have max input length (512 tokens for MiniLM)
- Smaller chunks = more precise semantic search
- Overlap preserves context across chunk boundaries

Strategy:
- RecursiveCharacterTextSplitter (respects sentence boundaries)
- 500 characters per chunk (fits in embedding model context)
- 50 character overlap (preserves context)
"""

from typing import List
from dataclasses import dataclass
from langchain.text_splitter import RecursiveCharacterTextSplitter


@dataclass
class TextChunk:
    """
    A chunk of text with metadata.

    Attributes:
        text: The chunk content
        chunk_index: Position in the original document (0-indexed)
        start_char: Character offset where this chunk starts
        end_char: Character offset where this chunk ends
    """
    text: str
    chunk_index: int
    start_char: int
    end_char: int


class ChunkingService:
    """
    Split text into semantic chunks for embedding.

    Uses LangChain's RecursiveCharacterTextSplitter which:
    1. Tries to split on paragraph boundaries (\n\n)
    2. Falls back to sentence boundaries (. ! ?)
    3. Falls back to word boundaries ( )
    4. Falls back to character boundaries (last resort)

    This preserves semantic meaning better than fixed-size chunks.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        Initialize the chunking service.

        Args:
            chunk_size: Target size for each chunk (in characters)
                - Default 500 works well for most PDFs
                - Smaller = more precise search, more chunks
                - Larger = more context, fewer chunks

            chunk_overlap: How many characters overlap between chunks
                - Default 50 preserves context across boundaries
                - Too small = context loss
                - Too large = duplicate content

        Example:
            Text: "The cat sat on the mat. The dog ran in the park."
            chunk_size=30, overlap=10

            Chunk 1: "The cat sat on the mat."
            Chunk 2: "at. The dog ran in the"  (overlap: "at.")
            Chunk 3: "in the park."
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,  
            separators=[
                "\n\n",  
                "\n",    
                ". ",  
                "! ",    
                "? ",    
                "; ",    
                ", ",     
                " ",     
                ""      
            ]
        )

    async def chunk_text(self, text: str) -> List[TextChunk]:
        """
        Split text into semantic chunks.

        Args:
            text: The full text to chunk

        Returns:
            List[TextChunk]: List of chunks with metadata

        Example:
            >>> chunker = ChunkingService(chunk_size=500, chunk_overlap=50)
            >>> chunks = await chunker.chunk_text(pdf_text)
            >>> print(f"Created {len(chunks)} chunks")
            >>> for chunk in chunks[:3]:
            ...     print(f"Chunk {chunk.chunk_index}: {chunk.text[:100]}...")
        """

        raw_chunks = self.splitter.split_text(text)

        chunks = []
        current_offset = 0

        for idx, chunk_text in enumerate(raw_chunks):
            chunk_start = current_offset
            chunk_end = chunk_start + len(chunk_text)

            chunk = TextChunk(
                text=chunk_text.strip(), 
                chunk_index=idx,
                start_char=chunk_start,
                end_char=chunk_end
            )

            chunks.append(chunk)

            current_offset += len(chunk_text) - self.chunk_overlap

        print(f"Split text into {len(chunks)} chunks (avg size: {sum(len(c.text) for c in chunks) / len(chunks):.0f} chars)")

        return chunks

    async def chunk_with_metadata(
        self,
        text: str,
        document_metadata: dict
    ) -> List[dict]:
        """
        Chunk text and attach document metadata to each chunk.

        This is useful when storing chunks in a vector database -
        you can filter by metadata (e.g., document_id, filename).

        Args:
            text: The full text to chunk
            document_metadata: Metadata to attach to each chunk
                Example: {"document_id": "123", "filename": "paper.pdf"}

        Returns:
            List[dict]: List of chunks with metadata

        Example:
            >>> chunks = await chunker.chunk_with_metadata(
            ...     text=pdf_text,
            ...     document_metadata={
            ...         "document_id": "abc-123",
            ...         "filename": "research.pdf",
            ...         "author": "Jane Doe"
            ...     }
            ... )
            >>> # Each chunk now has: text, chunk_index, document_id, filename, author
        """


        chunks = await self.chunk_text(text)
        chunks_with_metadata = []

        for chunk in chunks:
            chunk_dict = {
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                **document_metadata  
            }
            chunks_with_metadata.append(chunk_dict)

        return chunks_with_metadata

    def estimate_chunk_count(self, text_length: int) -> int:
        """
        Estimate how many chunks will be created for a given text length.

        This is useful for progress tracking and resource planning.

        Args:
            text_length: Length of text in characters

        Returns:
            int: Estimated number of chunks

        Example:
            >>> chunker = ChunkingService(chunk_size=500, chunk_overlap=50)
            >>> estimated = chunker.estimate_chunk_count(10000)
            >>> print(f"Will create ~{estimated} chunks")
        """

        effective_chunk_size = self.chunk_size - self.chunk_overlap

        if effective_chunk_size <= 0:

            return text_length
        estimated = (text_length + effective_chunk_size - 1) // effective_chunk_size
        return max(1, estimated)
