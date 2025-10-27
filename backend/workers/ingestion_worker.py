"""
Background Ingestion Worker

This worker processes PDF ingestion jobs from the Redis queue.

Flow:
1. Poll Redis queue for new jobs
2. Download PDF from MinIO
3. Extract text from PDF
4. Chunk text into semantic pieces
5. Generate embeddings for each chunk
6. Store vectors in Weaviate
7. Update document status in PostgreSQL
8. Publish progress updates to Redis (for WebSocket)

Run this worker:
    python -m backend.workers.ingestion_worker
"""

import asyncio
import uuid
import re
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database import get_db_session, init_db
from backend.core.redis_client import get_redis_queue, get_redis_client, get_redis_pubsub
from backend.models.document import Document, DocumentStatus
from backend.services.storage_service import get_storage_service
from backend.services.pdf_service import PDFService
from backend.services.chunking_service import ChunkingService
from backend.services.clause_chunking_service import get_clause_chunking_service
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_service import VectorService


class IngestionWorker:
    """
    Background worker for processing PDF ingestion jobs.

    This worker runs continuously, polling Redis for new jobs.
    When a job arrives, it processes the entire pipeline:
    PDF → text → chunks → embeddings → Weaviate
    """

    def __init__(self):
        """Initialize services."""
        self.storage = get_storage_service()
        self.pdf_service = PDFService()
        self.chunking_service = ChunkingService(chunk_size=500, chunk_overlap=50)
        self.clause_chunking_service = get_clause_chunking_service() 
        self.embedding_service = EmbeddingService()
        self.vector_service = VectorService()
        self.redis_queue = get_redis_queue()
        self.redis = get_redis_client()
        self.pubsub = get_redis_pubsub()  

    def _detect_legal_document(self, text: str, filename: str) -> bool:
        """
        Detect if a document is a legal document.

        Strategy: Hybrid approach
        1. Fast regex/heuristic check (catches 95% of cases)
        2. Optional LLM verification for edge cases (future enhancement)

        Args:
            text: Document text
            filename: Document filename

        Returns:
            True if legal document, False otherwise
        """


        legal_filename_keywords = [
            'contract', 'agreement', 'clause', 'terms', 'conditions',
            'legal', 'policy', 'nda', 'mou', 'sla', 'msa'
        ]

        filename_lower = filename.lower()
        if any(keyword in filename_lower for keyword in legal_filename_keywords):
            print(f"  → Legal doc detected by filename: {filename}")
            return True

        sample_text = text[:5000] 
        clause_pattern = r'\b\d+\.\d+(?:\.\d+)*\s+'
        clause_count = len(re.findall(clause_pattern, sample_text))
        section_pattern = r'\b(Article|Section|ARTICLE|SECTION|Clause|CLAUSE)\s+\d+'
        section_count = len(re.findall(section_pattern, sample_text))

        if clause_count >= 3 or section_count >= 2:
            print(f"  → Legal doc detected: {clause_count} clauses, {section_count} sections")
            return True

        legal_terms = [
            'whereas', 'hereinafter', 'party', 'parties',
            'terminate', 'termination', 'indemnify', 'liability',
            'agreement', 'contract', 'executed'
        ]

        text_lower = sample_text.lower()
        legal_term_count = sum(1 for term in legal_terms if term in text_lower)

        if legal_term_count >= 5:
            print(f"  → Legal doc detected: {legal_term_count} legal terms found")
            return True

        # TODO: Future enhancement - use LLM for uncertain cases
        # if clause_count >= 1 or section_count >= 1:
        #     return await self._llm_verify_legal_doc(text[:1000])

        print(f"  → Not a legal doc (clauses: {clause_count}, sections: {section_count}, terms: {legal_term_count})")
        return False

    async def publish_progress(
        self,
        document_id: str,
        status: str,
        message: str,
        progress: int = 0
    ) -> None:
        """
        Publish progress update to Redis pub/sub for WebSocket clients.

        Args:
            document_id: Document UUID
            status: Current status (queued, processing, completed, failed)
            message: Human-readable progress message
            progress: Progress percentage (0-100)
        """
        update = {
            "document_id": document_id,
            "status": status,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        channel = f"document:{document_id}:progress"
        num_subscribers = await self.pubsub.publish(channel, update)
        subscriber_info = f" [{num_subscribers} subscribers]" if num_subscribers > 0 else ""
        print(f"Progress: {document_id[:8]}... {message} ({progress}%){subscriber_info}")

    async def process_job(self, job_data: Dict[str, Any]) -> None:
        """
        Process a single ingestion job.

        Args:
            job_data: Job data from Redis queue
                {
                    "document_id": "123e4567-...",
                    "filename": "research.pdf",
                    "minio_path": "documents/123e4567-.../research.pdf",
                    "collection_name": "default",
                    "file_size_bytes": 2048576
                }
        """
        document_id = job_data["document_id"]
        filename = job_data["filename"]
        minio_path = job_data["minio_path"]
        collection_name = job_data["collection_name"]

        print(f"\n{'='*80}")
        print(f"Processing job: {document_id}")
        print(f"File: {filename}")
        print(f"Collection: {collection_name}")
        print(f"{'='*80}\n")


        async with get_db_session() as db:
            try:

                await self._update_document_status(
                    db, document_id, DocumentStatus.PROCESSING
                )
                await self.publish_progress(
                    document_id, "processing", "Starting PDF processing...", 5
                )

                print(f"Step 1: Downloading PDF from MinIO...")
                pdf_bytes = await self.storage.download_file(minio_path)
                await self.publish_progress(
                    document_id, "processing", "PDF downloaded", 15
                )

                print(f"Step 2: Extracting text from PDF...")
                text = await self.pdf_service.extract_text(pdf_bytes)
                page_count = await self.pdf_service.get_page_count(pdf_bytes)

                if len(text.strip()) == 0:
                    raise ValueError("PDF contains no extractable text")

                print(f"Extracted {len(text)} characters from {page_count} pages")
                await self.publish_progress(
                    document_id, "processing", f"Extracted text from {page_count} pages", 30
                )

                print(f"Step 3: Chunking text...")

                is_legal_doc = self._detect_legal_document(text, filename)

                if is_legal_doc:
                    print(f"  → Detected legal document, using clause-aware chunking")
                    chunks = await self.clause_chunking_service.chunk_with_metadata(
                        text=text,
                        document_metadata={
                            "document_id": document_id,
                            "filename": filename,
                            "page_count": page_count,
                            "document_type": "legal_contract"
                        }
                    )
                else:
                    print(f"  → Using standard semantic chunking")
                    chunks = await self.chunking_service.chunk_with_metadata(
                        text=text,
                        document_metadata={
                            "document_id": document_id,
                            "filename": filename,
                            "page_count": page_count,
                            "document_type": "general"
                        }
                    )

                chunk_count = len(chunks)
                print(f"Created {chunk_count} chunks")
                await self.publish_progress(
                    document_id, "processing", f"Created {chunk_count} text chunks", 50
                )

                print(f"Step 4: Generating embeddings...")
                chunk_texts = [chunk["text"] for chunk in chunks]
                embeddings = await self.embedding_service.embed_chunks(chunk_texts)
                print(f"Generated {len(embeddings)} embedding vectors")
                await self.publish_progress(
                    document_id, "processing", f"Generated {len(embeddings)} embeddings", 70
                )

                print(f"Step 5: Preparing vector database...")
                if not await self.vector_service.collection_exists(collection_name):
                    vector_dim = self.embedding_service.get_dimension()
                    await self.vector_service.create_collection(
                        collection_name=collection_name,
                        vector_dimension=vector_dim
                    )

                print(f"Step 6: Storing vectors in Weaviate...")
                await self.vector_service.insert_documents(
                    collection_name=collection_name,
                    texts=chunk_texts,
                    vectors=embeddings,
                    metadata_list=chunks
                )
                await self.publish_progress(
                    document_id, "processing", "Vectors stored in Weaviate", 90
                )

                await self._update_document_completed(
                    db=db,
                    document_id=document_id,
                    num_pages=page_count,
                    num_chunks=chunk_count
                )
                await self.publish_progress(
                    document_id, "completed", "Processing complete!", 100
                )

                print(f"\nSuccessfully processed {filename}")
                print(f"Pages: {page_count}, Chunks: {chunk_count}")
                print(f"Collection: {collection_name}\n")

            except Exception as e:
                error_message = str(e)
                print(f"Error processing {filename}: {error_message}")

                await self._update_document_failed(
                    db=db,
                    document_id=document_id,
                    error_message=error_message
                )
                await self.publish_progress(
                    document_id, "failed", f"Processing failed: {error_message}", 0
                )

    async def _update_document_status(
        self,
        db: AsyncSession,
        document_id: str,
        status: DocumentStatus
    ) -> None:
        """Update document status in database."""
        result = await db.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        )
        document = result.scalar_one_or_none()

        if document:
            document.status = status
            document.updated_at = datetime.now(timezone.utc)
            await db.commit()

    async def _update_document_completed(
        self,
        db: AsyncSession,
        document_id: str,
        num_pages: int,
        num_chunks: int
    ) -> None:
        """Update document with completion details."""
        result = await db.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        )
        document = result.scalar_one_or_none()

        if document:
            document.status = DocumentStatus.COMPLETED
            document.num_pages = num_pages
            document.num_chunks = num_chunks
            document.updated_at = datetime.now(timezone.utc)
            document.processed_at = datetime.now(timezone.utc)
            await db.commit()

    async def _update_document_failed(
        self,
        db: AsyncSession,
        document_id: str,
        error_message: str
    ) -> None:
        """Update document with failure details."""
        result = await db.execute(
            select(Document).where(Document.id == uuid.UUID(document_id))
        )
        document = result.scalar_one_or_none()

        if document:
            document.status = DocumentStatus.FAILED
            document.error_message = error_message
            document.updated_at = datetime.now(timezone.utc)
            await db.commit()

    async def run(self) -> None:
        """
        Main worker loop.

        Continuously polls Redis queue for new jobs and processes them.
        """
        print("Ingestion worker starting...")
        print("Polling Redis queue: ingestion_queue")
        print("Press Ctrl+C to stop\n")

        while True:
            try:
                job_data = await self.redis_queue.dequeue(timeout=5)
                if job_data:
                    await self.process_job(job_data)
                else:
                    await asyncio.sleep(1)

            except KeyboardInterrupt:
                print("\n⏸Worker stopped by user")
                break
            
            except Exception as e:
                print(f"Worker error: {e}")
                await asyncio.sleep(5) 



# Main Entry Point

async def main():
    """Initialize database and run worker."""
    await init_db()
    worker = IngestionWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
