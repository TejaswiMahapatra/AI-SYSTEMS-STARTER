"""
PDF Text Extraction Service

This service extracts text from PDF files using pypdf.
For complex PDFs with tables/forms, we use pdfplumber as fallback.

Why pypdf?
- Pure Python (no system dependencies)
- Fast for standard PDFs
- Good Unicode support

Why pdfplumber as fallback?
- Better table extraction
- Handles complex layouts
- More accurate for forms
"""

import io
from typing import Optional
import pypdf
import pdfplumber


class PDFService:
    """
    Extract text from PDF files with automatic fallback.

    Strategy:
    1. Try pypdf first (fast, works for 90% of PDFs)
    2. If pypdf returns < 100 chars, try pdfplumber (handles complex layouts)
    3. If both fail, raise exception
    """

    @staticmethod
    async def extract_text(pdf_bytes: bytes) -> str:
        """
        Extract all text from a PDF file.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            str: Extracted text from all pages (concatenated)

        Raises:
            ValueError: If PDF is invalid or text extraction fails
            Exception: If PDF processing fails

        Example:
            >>> pdf_service = PDFService()
            >>> text = await pdf_service.extract_text(pdf_bytes)
            >>> print(f"Extracted {len(text)} characters")
        """

        try:
            text = PDFService._extract_with_pypdf(pdf_bytes)
            if len(text.strip()) > 100:
                print(f"Extracted {len(text)} chars using pypdf")
                return text

            print("pypdf extracted < 100 chars, trying pdfplumber...")

        except Exception as e:
            print(f"pypdf failed: {e}, trying pdfplumber...")

        try:
            text = PDFService._extract_with_pdfplumber(pdf_bytes)

            if len(text.strip()) > 0:
                print(f"Extracted {len(text)} chars using pdfplumber")
                return text
            else:
                raise ValueError("PDF contains no extractable text (might be scanned images)")

        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

    @staticmethod
    def _extract_with_pypdf(pdf_bytes: bytes) -> str:
        """
        Extract text using pypdf library.

        pypdf is fast but may struggle with:
        - Scanned PDFs (images only)
        - Complex layouts with tables
        - Forms with overlapping text

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            str: Extracted text
        """
        pdf_file = io.BytesIO(pdf_bytes)
        reader = pypdf.PdfReader(pdf_file)

        text_parts = []

        for page_num, page in enumerate(reader.pages, start=1):
            try:
                page_text = page.extract_text()

                if page_text:
                    text_parts.append(f"\n--- Page {page_num} ---\n")
                    text_parts.append(page_text)

            except Exception as e:
                print(f"⚠️ pypdf: Failed to extract page {page_num}: {e}")
                continue

        return "\n".join(text_parts)

    @staticmethod
    def _extract_with_pdfplumber(pdf_bytes: bytes) -> str:
        """
        Extract text using pdfplumber library.

        pdfplumber is slower but better for:
        - Tables (preserves structure)
        - Complex layouts
        - Forms with precise positioning

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            str: Extracted text
        """
        pdf_file = io.BytesIO(pdf_bytes)
        text_parts = []

        with pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                try:
                    page_text = page.extract_text()

                    if page_text:
                        text_parts.append(f"\n--- Page {page_num} ---\n")
                        text_parts.append(page_text)
                        tables = page.extract_tables()
                        if tables:
                            text_parts.append(f"\n[Tables on page {page_num}]\n")
                            for table_idx, table in enumerate(tables):
                                text_parts.append(f"Table {table_idx + 1}:")
                                for row in table:
                                    text_parts.append(" | ".join(str(cell) for cell in row if cell))

                except Exception as e:
                    print(f"⚠️ pdfplumber: Failed to extract page {page_num}: {e}")
                    continue

        return "\n".join(text_parts)

    @staticmethod
    async def get_page_count(pdf_bytes: bytes) -> int:
        """
        Get the number of pages in a PDF.

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            int: Number of pages

        Raises:
            Exception: If PDF is invalid
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)
            return len(reader.pages)
        except Exception as e:
            raise Exception(f"Failed to read PDF page count: {str(e)}")

    @staticmethod
    async def validate_pdf(pdf_bytes: bytes) -> bool:
        """
        Validate that a file is a valid PDF.

        Args:
            pdf_bytes: Raw file bytes

        Returns:
            bool: True if valid PDF, False otherwise
        """
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = pypdf.PdfReader(pdf_file)

            if len(reader.pages) > 0:
                return True
            else:
                return False

        except Exception:
            return False
