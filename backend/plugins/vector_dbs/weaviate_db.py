"""
Weaviate vector database implementation.

100% open source vector database.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

import uuid
from typing import List, Dict, Any, Optional
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery

from backend.interfaces.vector_db import VectorDatabase, VectorSearchResult
from backend.config import settings


class WeaviateDB(VectorDatabase):
    """Weaviate vector database implementation."""

    def __init__(self, url: str = None):
        """
        Initialize Weaviate client.

        Args:
            url: Weaviate instance URL
        """
        self.url = url or settings.weaviate_url
        self.client = weaviate.connect_to_local(host=self.url.replace("http://", ""))

    async def create_collection(
        self,
        collection_name: str,
        vector_dimension: int,
        metadata_schema: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a new collection in Weaviate."""
        try:
            # Define properties for the collection
            properties = [
                Property(name="text", data_type=DataType.TEXT),
                Property(name="document_id", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="page_number", data_type=DataType.INT),
            ]

            # Add custom metadata properties if provided
            if metadata_schema:
                for key, value_type in metadata_schema.items():
                    if value_type == "text":
                        properties.append(Property(name=key, data_type=DataType.TEXT))
                    elif value_type == "int":
                        properties.append(Property(name=key, data_type=DataType.INT))
                    elif value_type == "float":
                        properties.append(Property(name=key, data_type=DataType.NUMBER))

            # Create collection with vectorizer configuration
            self.client.collections.create(
                name=collection_name,
                properties=properties,
                vectorizer_config=Configure.Vectorizer.none(),  # We provide our own vectors
            )
            return True
        except Exception as e:
            print(f"Error creating collection: {e}")
            return False

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection from Weaviate."""
        try:
            self.client.collections.delete(collection_name)
            return True
        except Exception as e:
            print(f"Error deleting collection: {e}")
            return False

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        try:
            return self.client.collections.exists(collection_name)
        except Exception:
            return False

    async def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        texts: List[str],
        metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """Insert vectors with associated text and metadata."""
        try:
            collection = self.client.collections.get(collection_name)
            ids = []

            # Batch insert for efficiency
            with collection.batch.dynamic() as batch:
                for vector, text, meta in zip(vectors, texts, metadata):
                    object_id = str(uuid.uuid4())
                    batch.add_object(
                        properties={
                            "text": text,
                            "document_id": meta.get("document_id", ""),
                            "chunk_index": meta.get("chunk_index", 0),
                            "page_number": meta.get("page_number", 0),
                            **{k: v for k, v in meta.items() if k not in ["document_id", "chunk_index", "page_number"]}
                        },
                        vector=vector,
                        uuid=object_id
                    )
                    ids.append(object_id)

            return ids
        except Exception as e:
            print(f"Error inserting vectors: {e}")
            return []

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors."""
        try:
            collection = self.client.collections.get(collection_name)

            # Perform vector search
            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                return_metadata=MetadataQuery(distance=True)
            )

            # Convert to VectorSearchResult format
            results = []
            for obj in response.objects:
                results.append(VectorSearchResult(
                    id=str(obj.uuid),
                    text=obj.properties.get("text", ""),
                    score=1.0 - obj.metadata.distance if obj.metadata.distance else 0.0,
                    metadata={
                        "document_id": obj.properties.get("document_id", ""),
                        "chunk_index": obj.properties.get("chunk_index", 0),
                        "page_number": obj.properties.get("page_number", 0),
                    }
                ))

            return results
        except Exception as e:
            print(f"Error searching vectors: {e}")
            return []

    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> bool:
        """Delete vectors by ID."""
        try:
            collection = self.client.collections.get(collection_name)
            for vector_id in vector_ids:
                collection.data.delete_by_id(vector_id)
            return True
        except Exception as e:
            print(f"Error deleting vectors: {e}")
            return False

    async def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics about a collection."""
        try:
            collection = self.client.collections.get(collection_name)

            # Get collection info
            aggregate_response = collection.aggregate.over_all(total_count=True)

            return {
                "name": collection_name,
                "count": aggregate_response.total_count,
                "exists": True
            }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {
                "name": collection_name,
                "count": 0,
                "exists": False
            }

    async def health_check(self) -> bool:
        """Check if Weaviate is healthy."""
        try:
            return self.client.is_ready()
        except Exception:
            return False

    def close(self):
        """Close Weaviate client connection."""
        if self.client:
            self.client.close()


# Singleton instance
_weaviate_instance = None


def get_weaviate() -> WeaviateDB:
    """Get or create singleton instance of WeaviateDB."""
    global _weaviate_instance
    if _weaviate_instance is None:
        _weaviate_instance = WeaviateDB()
    return _weaviate_instance
