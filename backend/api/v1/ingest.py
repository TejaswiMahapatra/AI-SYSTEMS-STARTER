"""
PDF Ingestion API Endpoints

This module handles PDF file uploads and initiates the ingestion pipeline.
Files are validated, saved to MinIO, and queued for background processing.

Flow:
1. User uploads PDF
2. Validate file (type, size)
3. Create Document record in PostgreSQL
4. Save file to MinIO
5. Queue job in Redis
6. Return document_id for tracking
"""

import uuid
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from backend.core.database import get_db
from backend.core.redis_client import get_redis_queue
from backend.models.document import Document, DocumentStatus
from backend.services.storage_service import get_storage_service


router = APIRouter(prefix="/ingest", tags=["ingestion"])



# Request/Response Models

class IngestResponse(BaseModel):
    """Response after successfully queueing a document for ingestion."""

    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(..., description="Current processing status")
    file_size_bytes: int = Field(..., description="File size in bytes")
    created_at: datetime = Field(..., description="Upload timestamp")
    message: str = Field(..., description="Human-readable status message")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "filename": "research_paper.pdf",
                "status": "queued",
                "file_size_bytes": 2048576,
                "created_at": "2024-01-15T10:30:00Z",
                "message": "Document queued for processing. Use WebSocket /ws/{document_id} to track progress."
            }
        }


class DocumentStatusResponse(BaseModel):
    """Response for document status queries."""

    document_id: str
    filename: str
    status: DocumentStatus
    file_size: int
    num_pages: Optional[int] = None
    num_chunks: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None



# Upload Endpoint

@router.post("/upload", response_model=IngestResponse, status_code=202)
async def upload_pdf(
    file: UploadFile = File(..., description="PDF file to ingest"),
    collection_name: str = "default",
    db: AsyncSession = Depends(get_db)
) -> IngestResponse:
    """
    Upload a PDF file for ingestion into the vector database.

    This endpoint:
    1. Validates the PDF file (type, size)
    2. Creates a Document record in PostgreSQL
    3. Saves the file to MinIO object storage
    4. Queues the document for background processing
    5. Returns immediately with a document ID for tracking

    Args:
        file: Uploaded PDF file (max 50MB)
        collection_name: Weaviate collection to store vectors (default: "default")
        db: Database session (injected)

    Returns:
        IngestResponse with document_id for tracking progress

    Raises:
        HTTPException 400: Invalid file type or size
        HTTPException 500: Storage or database errors
    """

    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported. Please upload a .pdf file."
        )

    if file.content_type != 'application/pdf':
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Expected application/pdf"
        )

    content = await file.read()
    file_size = len(content)

    # Limit to 50MB
    max_size = 50 * 1024 * 1024  # 50MB in bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {file_size / 1024 / 1024:.2f}MB. Maximum size is 50MB."
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty. Please upload a valid PDF file."
        )

    doc_id = uuid.uuid4()
    minio_path = f"documents/{doc_id}/{file.filename}"

    try:

        storage = get_storage_service()
        await storage.upload_file(
            file_content=content,
            object_name=minio_path,
            content_type="application/pdf"
        )


        document = Document(
            id=doc_id,
            filename=file.filename,
            original_filename=file.filename,
            file_size=file_size,
            mime_type="application/pdf",
            weaviate_collection=collection_name,
            minio_path=minio_path,
            status=DocumentStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        db.add(document)
        await db.commit()
        await db.refresh(document)


        redis_queue = get_redis_queue()
        await redis_queue.enqueue({
            "document_id": str(doc_id),
            "filename": file.filename,
            "minio_path": minio_path,
            "collection_name": collection_name,
            "file_size_bytes": file_size
        })

        return IngestResponse(
            document_id=str(doc_id),
            filename=file.filename,
            status=document.status,
            file_size_bytes=file_size,
            created_at=document.created_at,
            message=f"Document queued for processing. Use WebSocket /ws/{doc_id} to track progress."
        )

    except Exception as e:
        await db.rollback()

        try:
            await storage.delete_file(minio_path)
        except:
            pass
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue document for processing: {str(e)}"
        )



# Status Endpoint

@router.get("/status/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: AsyncSession = Depends(get_db)
) -> DocumentStatusResponse:
    """
    Get the current processing status of a document.

    Use this endpoint to poll for updates, or use WebSocket for real-time updates.

    Args:
        document_id: UUID of the document
        db: Database session (injected)

    Returns:
        DocumentStatusResponse with current status

    Raises:
        HTTPException 404: Document not found
        HTTPException 400: Invalid document ID format
    """

    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document ID format: {document_id}"
        )


    result = await db.execute(
        select(Document).where(Document.id == doc_uuid)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document not found: {document_id}"
        )

    return DocumentStatusResponse(
        document_id=str(document.id),
        filename=document.filename,
        status=document.status,
        file_size=document.file_size,
        num_pages=document.num_pages,
        num_chunks=document.num_chunks,
        created_at=document.created_at,
        updated_at=document.updated_at,
        error_message=document.error_message
    )



# List Documents Endpoint

@router.get("/documents", response_model=list[DocumentStatusResponse])
async def list_documents(
    status: Optional[DocumentStatus] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> list[DocumentStatusResponse]:
    """
    List all documents with optional status filtering.

    Args:
        status: Filter by status (queued, processing, completed, failed)
        limit: Maximum number of documents to return (default: 100)
        offset: Number of documents to skip (default: 0)
        db: Database session (injected)

    Returns:
        List of DocumentStatusResponse objects
    """

    query = select(Document).order_by(Document.created_at.desc())

    if status:
        query = query.where(Document.status == status)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    documents = result.scalars().all()

    return [
        DocumentStatusResponse(
            document_id=str(doc.id),
            filename=doc.filename,
            status=doc.status,
            file_size=doc.file_size,
            num_pages=doc.num_pages,
            num_chunks=doc.num_chunks,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            error_message=doc.error_message
        )
        for doc in documents
    ]
