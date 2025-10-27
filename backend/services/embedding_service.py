"""
Embedding Service

This service generates vector embeddings for text chunks.
It wraps the EmbeddingProvider interface and adds batch processing.

Why batch processing?
- Embedding models are optimized for batches
- 10-50x faster than one-by-one
- Better GPU utilization
"""

from typing import List
from backend.interfaces.embeddings import EmbeddingProvider
from backend.plugins.embeddings.local_embeddings import LocalEmbeddings


class EmbeddingService:
    """
    High-level service for generating embeddings with batching.

    This service:
    1. Takes a list of text chunks
    2. Batches them for efficient processing
    3. Returns corresponding vectors

    The underlying provider (LocalEmbeddings) is pluggable -
    you can swap for OpenAI, Cohere, etc. without changing this code.
    """

    def __init__(
        self,
        provider: EmbeddingProvider = None,
        batch_size: int = 32
    ):
        """
        Initialize the embedding service.

        Args:
            provider: Embedding provider (defaults to LocalEmbeddings)
            batch_size: How many texts to embed at once
                - Default 32 works well for CPU
                - Increase to 64-128 for GPU
                - Decrease to 8-16 for low memory

        Example:
            >>> # Use default (local sentence-transformers)
            >>> service = EmbeddingService()
            >>>
            >>> # Or provide custom provider
            >>> from backend.plugins.embeddings.openai_embeddings import OpenAIEmbeddings
            >>> service = EmbeddingService(provider=OpenAIEmbeddings())
        """
        self.provider = provider or LocalEmbeddings()
        self.batch_size = batch_size

    async def embed_chunks(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text chunks.

        Args:
            texts: List of text strings to embed

        Returns:
            List[List[float]]: List of embedding vectors (same order as input)

        Example:
            >>> service = EmbeddingService()
            >>> chunks = ["The cat sat on the mat.", "The dog ran in the park."]
            >>> embeddings = await service.embed_chunks(chunks)
            >>> print(f"Generated {len(embeddings)} vectors")
            >>> print(f"Vector dimension: {len(embeddings[0])}")
        """

        if not texts:
            return []

        embeddings = await self.provider.embed_batch(texts)

        print(f"Generated {len(embeddings)} embeddings (dimension: {len(embeddings[0])})")

        return embeddings

    async def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        This is a convenience method for one-off embeddings
        (e.g., user queries). For multiple texts, use embed_chunks().

        Args:
            text: Text string to embed

        Returns:
            List[float]: Embedding vector

        Example:
            >>> service = EmbeddingService()
            >>> query = "What is machine learning?"
            >>> query_vector = await service.embed_single(query)
        """

        embedding = await self.provider.embed_text(text)
        return embedding

    def get_dimension(self) -> int:
        """
        Get the dimension of embedding vectors.

        This is useful for:
        - Creating vector database collections
        - Validating vector dimensions
        - Displaying info to users

        Returns:
            int: Vector dimension

        Example:
            >>> service = EmbeddingService()
            >>> dim = service.get_dimension()
            >>> print(f"Using {dim}-dimensional embeddings")
        """
        return self.provider.get_embedding_dimension()
