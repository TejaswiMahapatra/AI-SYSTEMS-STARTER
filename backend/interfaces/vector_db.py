"""
Abstract interface for vector database providers.

This allows pluggable vector DB implementations (Weaviate, Pinecone, etc.)

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    """Result from vector similarity search."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class VectorDatabase(ABC):
    """Abstract base class for vector database operations."""

    @abstractmethod
    async def create_collection(
        self,
        collection_name: str,
        vector_dimension: int,
        metadata_schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new collection in the vector database.

        Args:
            collection_name: Name of the collection
            vector_dimension: Dimension of embedding vectors
            metadata_schema: Optional schema for metadata fields

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from the vector database.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if exists, False otherwise
        """
        pass

    @abstractmethod
    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        texts: List[str],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Insert vectors with associated text and metadata.

        Args:
            collection_name: Name of the collection
            vectors: List of embedding vectors
            texts: List of text chunks
            metadata: List of metadata dictionaries

        Returns:
            List of IDs for the inserted vectors
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors.

        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results ordered by similarity
        """
        pass

    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> bool:
        """
        Delete vectors by ID.

        Args:
            collection_name: Name of the collection
            vector_ids: List of vector IDs to delete

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        Get statistics about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with stats (count, dimension, etc.)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector database is healthy.

        Returns:
            True if healthy, False otherwise
        """
        pass
