"""
Vector Storage Service

This service manages vector storage in Weaviate.
It wraps the VectorDatabase interface and adds convenience methods.

Key features:
- Collection management (create/delete)
- Batch insertion with progress tracking
- Semantic search
- Metadata filtering
"""

from typing import List, Dict, Any, Optional
from backend.interfaces.vector_db import VectorDatabase, VectorSearchResult
from backend.plugins.vector_dbs.weaviate_db import WeaviateDB


class VectorService:
    """
    High-level service for vector storage operations.

    This service provides:
    - Collection management
    - Batch insertion with chunking
    - Search with metadata filtering
    - Cleanup utilities

    The underlying provider (WeaviateDB) is pluggable.
    """

    def __init__(self, provider: VectorDatabase = None):
        """
        Initialize the vector service.

        Args:
            provider: Vector database provider (defaults to WeaviateDB)

        Example:
            >>> # Use default (Weaviate)
            >>> service = VectorService()
            >>>
            >>> # Or provide custom provider
            >>> from backend.plugins.vector_dbs.qdrant_db import QdrantDB
            >>> service = VectorService(provider=QdrantDB())
        """
        self.provider = provider or WeaviateDB()

    async def create_collection(
        self,
        collection_name: str,
        vector_dimension: int = 384,
        distance_metric: str = "cosine"
    ) -> None:
        """
        Create a new collection for storing vectors.

        Args:
            collection_name: Name of the collection (e.g., "research_papers")
            vector_dimension: Dimension of vectors (384 for MiniLM, 1536 for OpenAI)
            distance_metric: "cosine", "euclidean", or "dot"

        Example:
            >>> service = VectorService()
            >>> await service.create_collection(
            ...     collection_name="my_documents",
            ...     vector_dimension=384
            ... )
        """
        await self.provider.create_collection(
            collection_name=collection_name,
            vector_dimension=vector_dimension,
            distance_metric=distance_metric
        )

        print(f"Created collection '{collection_name}' (dimension: {vector_dimension})")

    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            bool: True if collection exists, False otherwise
        """
        return await self.provider.collection_exists(collection_name)

    async def insert_documents(
        self,
        collection_name: str,
        texts: List[str],
        vectors: List[List[float]],
        metadata_list: List[Dict[str, Any]]
    ) -> int:
        """
        Insert documents (text + vectors + metadata) into a collection.

        Args:
            collection_name: Target collection
            texts: List of text chunks
            vectors: List of embedding vectors (same order as texts)
            metadata_list: List of metadata dicts (same order as texts)

        Returns:
            int: Number of documents inserted

        Example:
            >>> service = VectorService()
            >>> await service.insert_documents(
            ...     collection_name="my_docs",
            ...     texts=["chunk 1", "chunk 2"],
            ...     vectors=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
            ...     metadata_list=[
            ...         {"document_id": "123", "chunk_index": 0},
            ...         {"document_id": "123", "chunk_index": 1}
            ...     ]
            ... )
        """

        if not (len(texts) == len(vectors) == len(metadata_list)):
            raise ValueError(
                f"Length mismatch: texts={len(texts)}, "
                f"vectors={len(vectors)}, metadata={len(metadata_list)}"
            )

        await self.provider.insert_vectors(
            collection_name=collection_name,
            vectors=vectors,
            texts=texts,
            metadata=metadata_list
        )

        print(f"Inserted {len(texts)} documents into '{collection_name}'")

        return len(texts)

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Semantic search for similar documents.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding vector
            top_k: Number of results to return (default: 5)
            metadata_filter: Optional metadata filter
                Example: {"document_id": "123"} - only search within document 123

        Returns:
            List[VectorSearchResult]: Top-k most similar documents

        Example:
            >>> # Search across all documents
            >>> results = await service.search(
            ...     collection_name="my_docs",
            ...     query_vector=query_embedding,
            ...     top_k=5
            ... )
            >>>
            >>> # Search within specific document
            >>> results = await service.search(
            ...     collection_name="my_docs",
            ...     query_vector=query_embedding,
            ...     top_k=3,
            ...     metadata_filter={"document_id": "abc-123"}
            ... )
        """

        results = await self.provider.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k,
            filters=metadata_filter
        )

        print(f"Found {len(results)} results in '{collection_name}'")

        return results

    async def delete_by_metadata(
        self,
        collection_name: str,
        metadata_filter: Dict[str, Any]
    ) -> int:
        """
        Delete documents matching metadata filter.

        This is useful for:
        - Deleting all chunks from a specific document
        - Removing old documents
        - Cleaning up test data

        Args:
            collection_name: Collection to delete from
            metadata_filter: Filter for which documents to delete
                Example: {"document_id": "123"} - delete all chunks from doc 123

        Returns:
            int: Number of documents deleted

        Example:
            >>> # Delete all chunks from document abc-123
            >>> deleted = await service.delete_by_metadata(
            ...     collection_name="my_docs",
            ...     metadata_filter={"document_id": "abc-123"}
            ... )
            >>> print(f"Deleted {deleted} chunks")
        """

        count = await self.provider.delete_by_metadata(
            collection_name=collection_name,
            metadata_filter=metadata_filter
        )

        print(f"Deleted {count} documents from '{collection_name}'")

        return count

    async def delete_collection(self, collection_name: str) -> None:
        """
        Delete an entire collection.

        WARNING: This permanently deletes all data in the collection.

        Args:
            collection_name: Collection to delete

        Example:
            >>> service = VectorService()
            >>> await service.delete_collection("old_collection")
        """

        await self.provider.delete_collection(collection_name)

        print(f"Deleted collection '{collection_name}'")

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics about a collection.

        Args:
            collection_name: Collection name

        Returns:
            dict: Statistics (count, vector_dimension, etc.)

        Example:
            >>> stats = await service.get_collection_stats("my_docs")
            >>> print(f"Collection has {stats['count']} documents")
        """

        if hasattr(self.provider, 'get_collection_stats'):
            stats = await self.provider.get_collection_stats(collection_name)
            return stats
        else:
            return {"error": "Provider does not support stats"}
