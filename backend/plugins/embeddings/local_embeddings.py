"""
Local embeddings implementation using sentence-transformers.

100% open source, runs locally without API keys.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

from typing import List
from sentence_transformers import SentenceTransformer
from backend.interfaces.embeddings import EmbeddingProvider
from backend.config import settings

class LocalEmbeddings(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.

    Models:
    - all-MiniLM-L6-v2: 384 dim, fast, good quality (default)
    - all-mpnet-base-v2: 768 dim, slower, better quality
    - paraphrase-multilingual: Supports 50+ languages
    """

    def __init__(self, model_name: str = None, device: str = None):
        """
        Initialize local embeddings.

        Args:
            model_name: Name of sentence-transformers model
            device: Device to run on ('cpu', 'cuda', 'mps')
        """
        self.model_name = model_name or settings.local_embedding_model
        self.device = device or settings.local_embedding_device
        self.model = SentenceTransformer(self.model_name, device=self.device)

    async def embed_text(self, text: str) -> List[float]:
        """Generate embeddings for a single text."""
        embedding = self.model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Batch processing is more efficient than individual calls.
        """
        embeddings = self.model.encode(
            texts,
            convert_to_tensor=False,
            show_progress_bar=False,
            batch_size=32
        )
        return [emb.tolist() for emb in embeddings]

    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self.model.get_sentence_embedding_dimension()

    def get_model_name(self) -> str:
        """Get the name of the embedding model."""
        return self.model_name


_local_embeddings_instance = None


def get_local_embeddings() -> LocalEmbeddings:
    """Get or create singleton instance of LocalEmbeddings."""
    global _local_embeddings_instance
    if _local_embeddings_instance is None:
        _local_embeddings_instance = LocalEmbeddings()
    return _local_embeddings_instance
