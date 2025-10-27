"""
Test Weaviate vector storage and retrieval.
Quick diagnostic to verify Weaviate is working correctly.
"""

import asyncio
from backend.plugins.vector_dbs.weaviate_db import WeaviateDB
from backend.services.embedding_service import EmbeddingService

async def test_weaviate_basic():
    """Test basic Weaviate operations"""

    print("=" * 80)
    print("WEAVIATE DIAGNOSTIC TEST")
    print("=" * 80)

    # Initialize
    db = WeaviateDB()
    embedding_service = EmbeddingService()

    # Step 1: Health check
    print("\n1. Checking Weaviate health...")
    is_healthy = await db.health_check()
    print(f"Weaviate is {'healthy' if is_healthy else 'UNHEALTHY'}")

    # Step 2: Create test collection
    collection_name = "TestCollection"
    print(f"\n2. Creating collection '{collection_name}'...")

    # Delete if exists
    if await db.collection_exists(collection_name):
        print(f"   - Collection exists, deleting...")
        await db.delete_collection(collection_name)

    # Create new
    vector_dim = embedding_service.get_dimension()
    success = await db.create_collection(
        collection_name=collection_name,
        vector_dimension=vector_dim,
        metadata_schema={
            "clause_id": "text",
            "clause_type": "text",
        }
    )
    print(f"Collection created: {success}")

    # Step 3: Insert test vectors
    print(f"\n3. Inserting test vectors...")
    test_texts = [
        "Either party may terminate this Agreement upon 30 days written notice.",
        "Client shall pay within 30 days of invoice.",
        "The parties agree to binding arbitration for all disputes.",
    ]

    # Generate embeddings
    print(f"Generating embeddings for {len(test_texts)} texts...")
    embeddings = await embedding_service.embed_chunks(test_texts)
    print(f"Embedding dimension: {len(embeddings[0])}")

    # Prepare metadata
    metadata = [
        {"document_id": "test-doc-1", "chunk_index": 0, "page_number": 1, "clause_id": "1", "clause_type": "termination"},
        {"document_id": "test-doc-1", "chunk_index": 1, "page_number": 1, "clause_id": "2.1", "clause_type": "payment"},
        {"document_id": "test-doc-1", "chunk_index": 2, "page_number": 2, "clause_id": "8", "clause_type": "governing_law"},
    ]

    # Insert
    ids = await db.insert_vectors(
        collection_name=collection_name,
        vectors=embeddings,
        texts=test_texts,
        metadata=metadata
    )
    print(f"Inserted {len(ids)} vectors")

    # Step 4: Verify storage
    print(f"\n4. Verifying storage...")
    stats = await db.get_collection_stats(collection_name)
    print(f"Collection: {stats['name']}")
    print(f"Count: {stats['count']}")
    print(f"Exists: {stats['exists']}")

    if stats['count'] != len(test_texts):
        print(f"WARNING: Expected {len(test_texts)} objects, found {stats['count']}")
    else:
        print(f"All vectors stored correctly")

    # Step 5: Test search
    print(f"\n5. Testing vector search...")
    query_text = "How can I cancel the contract?"
    query_vector = await embedding_service.embed_single(query_text)

    results = await db.search(
        collection_name=collection_name,
        query_vector=query_vector,
        top_k=2
    )

    print(f"Query: '{query_text}'")
    print(f"Results: {len(results)}")
    for i, result in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"Score: {result.score:.3f}")
        print(f"Text: {result.text[:80]}...")
        print(f"Clause: {result.metadata.get('clause_id')} ({result.metadata.get('clause_type')})")

    # Should find termination clause first
    if results and results[0].metadata.get('clause_type') == 'termination':
        print(f"\nSearch is working correctly (found termination clause)")
    else:
        print(f"\nWARNING: Expected termination clause first, got {results[0].metadata.get('clause_type') if results else 'no results'}")

    # Step 6: Cleanup
    print(f"\n6. Cleaning up...")
    await db.delete_collection(collection_name)
    print(f"Test collection deleted")

    db.close()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_weaviate_basic())
