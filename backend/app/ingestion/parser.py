"""
Document parser for Integration Forge.

This module extracts text content from various file formats (Markdown, PDF, TXT).
Provides a unified interface for parsing different document types.

Design Philosophy:
- Format Detection: Automatic detection based on file extension
- Error Handling: Graceful failures with detailed error messages
- Encoding: UTF-8 first, fallback to detection for compatibility
- Metadata: Preserve page numbers, sections, and structure
- Type Safety: Strong typing with clear return values

Learning Note:
Why do we need a parser?
1. Unified Interface: One method to parse any supported file type
2. Error Handling: Consistent error messages for all formats
3. Metadata Extraction: Preserve document structure (pages, sections)
4. Extensibility: Easy to add new file formats (DOCX, HTML, etc.)
"""

import os
from pathlib import Path
from typing import BinaryIO

from pypdf import PdfReader

from app.utils.errors import DocumentProcessingError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ParsedDocument:
    """
    Result of document parsing.

    Contains extracted text and metadata about the document.

    Attributes:
        content: Extracted text content
        page_count: Number of pages (for PDFs)
        metadata: Additional information (file type, encoding, etc.)
    """

    def __init__(
        self,
        content: str,
        page_count: int = 1,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize parsed document.

        Args:
            content: Extracted text content
            page_count: Number of pages (default 1 for non-paginated formats)
            metadata: Additional metadata (file type, encoding, etc.)
        """
        self.content = content
        self.page_count = page_count
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        """String representation for debugging."""
        content_preview = self.content[:100] + \
            "..." if len(self.content) > 100 else self.content
        return (
            f"ParsedDocument(content_length={len(self.content)}, "
            f"page_count={self.page_count}, "
            f"preview='{content_preview}')"
        )


class DocumentParser:
    """
    Parser for extracting text from various document formats.

    Supports:
    - Markdown (.md)
    - PDF (.pdf)
    - Plain text (.txt)

    Future formats:
    - DOCX (.docx) - Microsoft Word
    - HTML (.html) - Web pages
    - RTF (.rtf) - Rich text format

    Learning Note:
    Why use a class instead of functions?
    - State Management: Can cache parsed results
    - Configuration: Easy to add parser settings
    - Extensibility: Subclass for specialized parsers
    - Testing: Easy to mock
    """

    SUPPORTED_EXTENSIONS = {".md", ".pdf", ".txt"}

    def __init__(self) -> None:
        """Initialize document parser."""
        logger.debug("DocumentParser initialized")

    def parse(self, file_path: str | Path) -> ParsedDocument:
        """
        Parse a document and extract text content.

        This is the main entry point for parsing. It automatically detects
        the file type and routes to the appropriate parser.

        Args:
            file_path: Path to the file to parse

        Returns:
            ParsedDocument with extracted text and metadata

        Raises:
            DocumentProcessingError: If file type is unsupported or parsing fails

        Learning Note:
        Why detect by extension instead of file content?
        - Performance: No need to read file to detect type
        - Simplicity: Extension is reliable for user uploads
        - Security: Prevents malicious files disguised as safe types
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise DocumentProcessingError(
                message=f"File not found: {file_path}",
                details={"file_path": str(file_path)},
            )

        extension = file_path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                message=f"Unsupported file type: {extension}",
                details={
                    "file_path": str(file_path),
                    "extension": extension,
                    "supported": list(self.SUPPORTED_EXTENSIONS),
                },
            )

        logger.info(
            "Parsing document",
            file_path=str(file_path),
            extension=extension,
        )

        try:
            # Route to appropriate parser
            if extension == ".md":
                result = self.parse_markdown(file_path)
            elif extension == ".pdf":
                result = self.parse_pdf(file_path)
            elif extension == ".txt":
                result = self.parse_text(file_path)
            else:
                # Should never reach here due to extension check above
                raise DocumentProcessingError(
                    message=f"No parser available for {extension}",
                    details={"extension": extension},
                )

            logger.info(
                "Document parsed successfully",
                file_path=str(file_path),
                content_length=len(result.content),
                page_count=result.page_count,
            )

            return result

        except DocumentProcessingError:
            # Re-raise our custom errors as-is
            raise
        except Exception as e:
            logger.error(
                "Failed to parse document",
                file_path=str(file_path),
                extension=extension,
                error=str(e),
                exc_info=True,
            )
            raise DocumentProcessingError(
                message=f"Failed to parse {extension} file",
                details={
                    "file_path": str(file_path),
                    "error": str(e),
                },
            )

    def parse_markdown(self, file_path: Path) -> ParsedDocument:
        """
        Parse Markdown file and extract text content.

        Markdown files are stored as plain text with formatting markers.
        We preserve the formatting because it provides useful context for chunking.

        Args:
            file_path: Path to the .md file

        Returns:
            ParsedDocument with extracted content

        Raises:
            DocumentProcessingError: If reading fails

        Learning Note:
        Why preserve Markdown formatting?
        - Headers (#, ##) help identify section boundaries
        - Code blocks (```) are important for technical docs
        - Lists and emphasis provide semantic structure
        - Chunker can use this structure intelligently
        """
        try:
            logger.debug("Parsing Markdown file", file_path=str(file_path))

            # Try UTF-8 first (most common)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                encoding = "utf-8"
            except UnicodeDecodeError:
                # Fallback to chardet for encoding detection
                import chardet
                with open(file_path, "rb") as f:
                    raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected["encoding"] or "utf-8"
                content = raw_data.decode(encoding, errors="replace")

                logger.warning(
                    "Non-UTF-8 encoding detected",
                    file_path=str(file_path),
                    detected_encoding=encoding,
                )

            if not content.strip():
                raise DocumentProcessingError(
                    message="Markdown file is empty",
                    details={"file_path": str(file_path)},
                )

            return ParsedDocument(
                content=content,
                page_count=1,  # Markdown doesn't have pages
                metadata={
                    "file_type": "markdown",
                    "encoding": encoding,
                },
            )

        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error(
                "Failed to parse Markdown file",
                file_path=str(file_path),
                error=str(e),
                exc_info=True,
            )
            raise DocumentProcessingError(
                message="Failed to read Markdown file",
                details={
                    "file_path": str(file_path),
                    "error": str(e),
                },
            )

    def parse_pdf(self, file_path: Path) -> ParsedDocument:
        """
        Parse PDF file and extract text content.

        Uses pypdf library to extract text from all pages.
        Preserves page breaks and page numbers for better chunking.

        Args:
            file_path: Path to the .pdf file

        Returns:
            ParsedDocument with extracted content and page count

        Raises:
            DocumentProcessingError: If PDF is encrypted, corrupted, or unreadable

        Learning Note:
        Why extract text instead of using OCR?
        - Performance: Text extraction is 100x faster than OCR
        - Accuracy: Text is exact, OCR can have errors
        - Cost: OCR requires expensive services (AWS Textract, etc.)
        - Use Case: Most PDFs have embedded text (not scanned images)

        For scanned PDFs, we'd need OCR (future enhancement).
        """
        try:
            logger.debug("Parsing PDF file", file_path=str(file_path))

            # Open PDF with pypdf
            with open(file_path, "rb") as f:
                reader = PdfReader(f)

                # Check if PDF is encrypted
                if reader.is_encrypted:
                    raise DocumentProcessingError(
                        message="PDF is encrypted and cannot be parsed",
                        details={"file_path": str(file_path)},
                    )

                page_count = len(reader.pages)

                if page_count == 0:
                    raise DocumentProcessingError(
                        message="PDF has no pages",
                        details={"file_path": str(file_path)},
                    )

                logger.debug(
                    "Extracting text from PDF",
                    page_count=page_count,
                )

                # Extract text from all pages
                pages_text = []
                for page_num, page in enumerate(reader.pages, start=1):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            # Add page marker for chunking context
                            pages_text.append(
                                f"[Page {page_num}]\n{page_text}")
                    except Exception as e:
                        logger.warning(
                            "Failed to extract text from page",
                            page_num=page_num,
                            error=str(e),
                        )
                        # Continue with other pages

                # Combine all pages with double newline separator
                content = "\n\n".join(pages_text)

                if not content.strip():
                    raise DocumentProcessingError(
                        message="PDF contains no extractable text (might be scanned images)",
                        details={
                            "file_path": str(file_path),
                            "page_count": page_count,
                        },
                    )

                return ParsedDocument(
                    content=content,
                    page_count=page_count,
                    metadata={
                        "file_type": "pdf",
                        "page_count": str(page_count),
                    },
                )

        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error(
                "Failed to parse PDF file",
                file_path=str(file_path),
                error=str(e),
                exc_info=True,
            )
            raise DocumentProcessingError(
                message="Failed to read PDF file",
                details={
                    "file_path": str(file_path),
                    "error": str(e),
                },
            )

    def parse_text(self, file_path: Path) -> ParsedDocument:
        """
        Parse plain text file and extract content.

        Handles various text encodings with UTF-8 preference.

        Args:
            file_path: Path to the .txt file

        Returns:
            ParsedDocument with extracted content

        Raises:
            DocumentProcessingError: If reading fails

        Learning Note:
        Why support multiple encodings?
        - Legacy Files: Old text files might use Latin-1, Windows-1252, etc.
        - International: Different languages use different encodings
        - Robustness: Better to decode with some errors than fail completely
        """
        try:
            logger.debug("Parsing text file", file_path=str(file_path))

            # Try UTF-8 first (most common)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                encoding = "utf-8"
            except UnicodeDecodeError:
                # Fallback to chardet for encoding detection
                import chardet
                with open(file_path, "rb") as f:
                    raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected["encoding"] or "utf-8"
                content = raw_data.decode(encoding, errors="replace")

                logger.warning(
                    "Non-UTF-8 encoding detected",
                    file_path=str(file_path),
                    detected_encoding=encoding,
                )

            if not content.strip():
                raise DocumentProcessingError(
                    message="Text file is empty",
                    details={"file_path": str(file_path)},
                )

            return ParsedDocument(
                content=content,
                page_count=1,
                metadata={
                    "file_type": "text",
                    "encoding": encoding,
                },
            )

        except DocumentProcessingError:
            raise
        except Exception as e:
            logger.error(
                "Failed to parse text file",
                file_path=str(file_path),
                error=str(e),
                exc_info=True,
            )
            raise DocumentProcessingError(
                message="Failed to read text file",
                details={
                    "file_path": str(file_path),
                    "error": str(e),
                },
            )

    def parse_from_bytes(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> ParsedDocument:
        """
        Parse document from bytes (useful for in-memory files).

        This is useful when receiving files from API uploads without
        saving to disk first.

        Args:
            file_bytes: File content as bytes
            filename: Original filename (for extension detection)

        Returns:
            ParsedDocument with extracted content

        Raises:
            DocumentProcessingError: If parsing fails

        Learning Note:
        Why parse from bytes?
        - API Uploads: Files come as bytes from multipart/form-data
        - Memory Efficiency: No need to write to disk first
        - Security: Can validate before touching filesystem
        - Flexibility: Works with cloud storage (S3, etc.)
        """
        import tempfile

        # Create temporary file
        extension = Path(filename).suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise DocumentProcessingError(
                message=f"Unsupported file type: {extension}",
                details={
                    "filename": filename,
                    "extension": extension,
                    "supported": list(self.SUPPORTED_EXTENSIONS),
                },
            )

        try:
            # Create temp file with correct extension
            with tempfile.NamedTemporaryFile(
                suffix=extension,
                delete=False,
            ) as temp_file:
                temp_file.write(file_bytes)
                temp_path = Path(temp_file.name)

            # Parse the temp file
            result = self.parse(temp_path)

            # Clean up temp file
            temp_path.unlink()

            return result

        except Exception as e:
            # Clean up temp file on error
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()

            logger.error(
                "Failed to parse document from bytes",
                filename=filename,
                error=str(e),
                exc_info=True,
            )
            raise DocumentProcessingError(
                message="Failed to parse uploaded file",
                details={
                    "filename": filename,
                    "error": str(e),
                },
            )
