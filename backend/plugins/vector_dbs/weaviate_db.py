"""
Weaviate vector database implementation.

100% open source vector database.

Copyright 2025 Tejaswi Mahapatra
Licensed under the Apache License, Version 2.0
"""

import uuid
import time
from typing import List, Dict, Any, Optional
import weaviate
from weaviate.classes.config import Configure, Property, DataType, VectorDistances
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
        self.client = weaviate.connect_to_custom(
            http_host="localhost",
            http_port=8080,
            http_secure=False,
            grpc_host="localhost",
            grpc_port=50051,
            grpc_secure=False,
            skip_init_checks=True  # Skip gRPC health check
        )

    async def create_collection(
        self,
        collection_name: str,
        vector_dimension: int,
        metadata_schema: Optional[Dict[str, Any]] = None,
        distance_metric: str = "cosine"
    ) -> bool:
        """
        Create a new collection in Weaviate.

        Args:
            collection_name: Name of the collection
            vector_dimension: Dimension of embedding vectors
            metadata_schema: Optional schema for additional properties
            distance_metric: Distance metric (cosine, euclidean, dot) - defaults to cosine
        """
        try:

            properties = [
                Property(name="text", data_type=DataType.TEXT),
                Property(name="document_id", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="page_number", data_type=DataType.INT),
                Property(name="clause_number", data_type=DataType.TEXT),
                Property(name="chunk_type", data_type=DataType.TEXT),
                Property(name="section_title", data_type=DataType.TEXT),
                Property(name="parent_section", data_type=DataType.TEXT),
                Property(name="hierarchy_level", data_type=DataType.INT),
            ]

            if metadata_schema:
                for key, value_type in metadata_schema.items():
                    if value_type == "text":
                        properties.append(Property(name=key, data_type=DataType.TEXT))
                    elif value_type == "int":
                        properties.append(Property(name=key, data_type=DataType.INT))
                    elif value_type == "float":
                        properties.append(Property(name=key, data_type=DataType.NUMBER))

            distance_map = {
                "cosine": VectorDistances.COSINE,
                "euclidean": VectorDistances.L2_SQUARED,
                "dot": VectorDistances.DOT,
            }

            self.client.collections.create(
                name=collection_name,
                properties=properties,
                vectorizer_config=Configure.Vectorizer.none(),  
                vector_index_config=Configure.VectorIndex.hnsw(
                    distance_metric=distance_map.get(distance_metric, VectorDistances.COSINE)
                )
            )
            print(f"Created collection '{collection_name}' with {vector_dimension}D vectors")
            return True
        except Exception as e:
            print(f"Error creating collection: {e}")
            import traceback
            traceback.print_exc()
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

            print(f"Inserting {len(vectors)} vectors into '{collection_name}'...")


            for i, (vector, text, meta) in enumerate(zip(vectors, texts, metadata)):
                try:
                    object_id = str(uuid.uuid4())

                    properties = {
                        "text": text,
                        "document_id": str(meta.get("document_id", "")),
                        "chunk_index": int(meta.get("chunk_index", 0)),
                        "page_number": int(meta.get("page_number", 0)),
                    }

                    for k, v in meta.items():
                        if k not in ["document_id", "chunk_index", "page_number", "text"]:
                            if isinstance(v, (int, float)):
                                properties[k] = v
                            else:
                                properties[k] = str(v)

                    result_uuid = collection.data.insert(
                        properties=properties,
                        vector=vector,
                        uuid=object_id
                    )

                    ids.append(str(result_uuid))

                    if (i + 1) % 10 == 0:
                        print(f"  Inserted {i + 1}/{len(vectors)} objects...")

                except Exception as e:
                    print(f"Error inserting object {i}: {e}")

                    continue

            print(f"Insertion complete. Inserted {len(ids)}/{len(vectors)} objects.")
            time.sleep(0.3)
            stats = await self.get_collection_stats(collection_name)
            print(f"Verified: {stats['count']} total objects in '{collection_name}'")

            return ids

        except Exception as e:
            print(f"Error in insert_vectors: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar vectors using Weaviate v4 client."""
        try:
            collection = self.client.collections.get(collection_name)

            response = collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                return_metadata=MetadataQuery(distance=True)
            )

            results = []
            for obj in response.objects:
                props = obj.properties
                metadata = {
                    "document_id": props.get("document_id", ""),
                    "chunk_index": props.get("chunk_index", 0),
                    "page_number": props.get("page_number", 0),
                }

                if "clause_number" in props:
                    metadata["clause_number"] = props.get("clause_number")
                if "chunk_type" in props:
                    metadata["chunk_type"] = props.get("chunk_type")
                if "section_title" in props:
                    metadata["section_title"] = props.get("section_title")
                if "parent_section" in props:
                    metadata["parent_section"] = props.get("parent_section")
                if "hierarchy_level" in props:
                    metadata["hierarchy_level"] = props.get("hierarchy_level")

                results.append(VectorSearchResult(
                    id=str(obj.uuid),
                    text=props.get("text", ""),
                    score=1.0 - obj.metadata.distance if obj.metadata.distance else 0.0,
                    metadata=metadata
                ))

            return results

        except Exception as e:
            print(f"Error searching vectors: {e}")
            import traceback
            traceback.print_exc()
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


_weaviate_instance = None


def get_weaviate() -> WeaviateDB:
    """Get or create singleton instance of WeaviateDB."""
    global _weaviate_instance
    if _weaviate_instance is None:
        _weaviate_instance = WeaviateDB()
    return _weaviate_instance
