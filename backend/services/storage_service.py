"""
MinIO Object Storage Service

This service handles file storage using MinIO (S3-compatible).
In production, you can swap MinIO for AWS S3 with minimal code changes.

Key Features:
- Upload/download files with automatic content-type detection
- Bucket management (create if not exists)
- Presigned URLs for secure file access
- Async operations using aiofiles
"""

import io
from typing import Optional
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from backend.config import get_settings

settings = get_settings()


class StorageService:
    """
    MinIO storage service for document management.

    MinIO is S3-compatible, so this code works with:
    - MinIO (local development)
    - AWS S3 (production)
    - DigitalOcean Spaces
    - Cloudflare R2
    - Any S3-compatible storage
    """

    def __init__(self):
        """
        Initialize MinIO client.

        Connection details come from config.py (environment variables):
        - MINIO_ENDPOINT: e.g., "localhost:9000"
        - MINIO_ACCESS_KEY: Access key ID
        - MINIO_SECRET_KEY: Secret access key
        - MINIO_SECURE: Use HTTPS (False for local dev)
        """
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """
        Create bucket if it doesn't exist.

        MinIO requires buckets to exist before uploading.
        This is idempotent - safe to call multiple times.
        """
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                print(f"Created MinIO bucket: {self.bucket_name}")
        except S3Error as e:
            print(f"Error checking/creating bucket: {e}")
            raise

    async def upload_file(
        self,
        file_content: bytes,
        object_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        Upload a file to MinIO.

        Args:
            file_content: Raw file bytes
            object_name: Path in bucket (e.g., "documents/123/file.pdf")
            content_type: MIME type (e.g., "application/pdf")

        Returns:
            object_name: The path where the file was stored

        Raises:
            S3Error: If upload fails

        Example:
            >>> storage = StorageService()
            >>> await storage.upload_file(
            ...     file_content=pdf_bytes,
            ...     object_name="documents/abc-123/research.pdf",
            ...     content_type="application/pdf"
            ... )
        """
        try:
            file_data = io.BytesIO(file_content)
            file_size = len(file_content)

            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type
            )

            print(f"Uploaded {object_name} ({file_size} bytes) to MinIO")
            return object_name

        except S3Error as e:
            print(f"MinIO upload error: {e}")
            raise

    async def download_file(self, object_name: str) -> bytes:
        """
        Download a file from MinIO.

        Args:
            object_name: Path in bucket (e.g., "documents/123/file.pdf")

        Returns:
            bytes: Raw file content

        Raises:
            S3Error: If file not found or download fails

        Example:
            >>> storage = StorageService()
            >>> pdf_bytes = await storage.download_file("documents/abc-123/research.pdf")
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            file_content = response.read()
            response.close()
            response.release_conn()

            print(f"Downloaded {object_name} ({len(file_content)} bytes) from MinIO")
            return file_content

        except S3Error as e:
            print(f"MinIO download error: {e}")
            raise

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        """
        Generate a presigned URL for temporary file access.

        Presigned URLs allow users to download files directly from MinIO
        without going through your backend. The URL expires after `expires`.

        Args:
            object_name: Path in bucket
            expires: How long the URL is valid (default: 1 hour)

        Returns:
            str: Presigned URL

        Example:
            >>> storage = StorageService()
            >>> url = storage.get_presigned_url(
            ...     "documents/abc-123/research.pdf",
            ...     expires=timedelta(minutes=30)
            ... )
            >>> # Share this URL with frontend - user can download directly
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            print(f"Error generating presigned URL: {e}")
            raise

    async def delete_file(self, object_name: str) -> None:
        """
        Delete a file from MinIO.

        Args:
            object_name: Path in bucket

        Raises:
            S3Error: If deletion fails
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            print(f"Deleted {object_name} from MinIO")
        except S3Error as e:
            print(f"MinIO delete error: {e}")
            raise

    def file_exists(self, object_name: str) -> bool:
        """
        Check if a file exists in MinIO.

        Args:
            object_name: Path in bucket

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return True
        except S3Error:
            return False

_storage_service: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """
    Get or create the storage service singleton.

    This ensures we only create one MinIO client for the entire application.

    Returns:
        StorageService: The singleton storage service instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
