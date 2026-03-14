"""
StorageClient abstraction for document file storage.

Provides a Protocol-based interface that allows swapping backends
(Supabase Storage, Azure Blob, local disk, etc.) without changing
calling code.

Usage:
    from app.core.storage import get_storage_client

    storage = get_storage_client()
    path = await storage.upload(data=bytes, path="user_id/doc_id/file.pdf", content_type="application/pdf")
    url  = await storage.get_signed_url(path=path, expires_in=3600)
    await storage.delete(path=path)
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol, runtime_checkable

from app.core.config import get_settings
from app.database.client import SupabaseClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocol – the contract every backend must satisfy
# ---------------------------------------------------------------------------


@runtime_checkable
class StorageClient(Protocol):
    """Abstract interface for file storage backends."""

    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload *data* to *path* inside the configured bucket.

        Args:
            data:         Raw file bytes to store.
            path:         Destination path inside the bucket.
                          Convention: ``{user_id}/{document_id}/{filename}``
            content_type: MIME type of the file.

        Returns:
            The storage path that was written (same as *path* on success).

        Raises:
            StorageUploadError: If the upload fails.
        """
        ...

    async def get_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a time-limited signed/pre-signed URL for *path*.

        Args:
            path:       Storage path returned by :meth:`upload`.
            expires_in: URL validity in seconds (default 1 hour).

        Returns:
            HTTPS URL that grants read access to the file for *expires_in* seconds.

        Raises:
            StorageNotFoundError: If *path* does not exist in the bucket.
            StorageSignedUrlError: If URL generation fails.
        """
        ...

    async def delete(self, path: str) -> None:
        """
        Remove a file from storage.

        Args:
            path: Storage path returned by :meth:`upload`.

        Raises:
            StorageDeleteError: If the deletion fails.
        """
        ...


# ---------------------------------------------------------------------------
# Supabase Storage implementation
# ---------------------------------------------------------------------------


class SupabaseStorageClient:
    """StorageClient backed by Supabase Storage (S3-compatible).

    The client uses the **service-role key** so that it bypasses Row-Level
    Security on ``storage.objects``.  Per-user access control is enforced
    via the custom storage RLS policies created in migration
    ``20260307_create_storage_documents_bucket``.
    """

    def __init__(self, bucket: str) -> None:
        self._bucket = bucket

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _storage(self) -> Any:
        """Return the supabase-py storage bucket proxy."""
        return SupabaseClient.get_client().storage.from_(self._bucket)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def upload(
        self,
        data: bytes,
        path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload *data* to *path* in the Supabase ``documents`` bucket.

        The supabase-py storage client is synchronous (httpx without an async
        wrapper), so the call is offloaded to a thread via asyncio.to_thread
        to avoid blocking the event loop.
        """
        try:
            logger.debug("Uploading file to Supabase Storage", path=path, bucket=self._bucket)
            await asyncio.to_thread(
                lambda: self._storage().upload(
                    path=path,
                    file=data,
                    file_options={"content-type": content_type, "upsert": "true"},
                )
            )
            logger.info("File uploaded to storage", path=path, bucket=self._bucket)
            return path
        except Exception as exc:
            logger.error("Storage upload failed", path=path, error=str(exc))
            raise StorageUploadError(f"Failed to upload file to storage: {exc}") from exc

    async def get_signed_url(
        self,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a signed URL for *path* in Supabase Storage."""
        try:
            logger.debug("Generating signed URL", path=path, expires_in=expires_in)
            result = await asyncio.to_thread(
                lambda: self._storage().create_signed_url(path=path, expires_in=expires_in)
            )

            # supabase-py returns {"signedURL": "..."} or raises on failure
            signed_url: str | None = None
            if isinstance(result, dict):
                signed_url = result.get("signedURL") or result.get("signedUrl")
            elif hasattr(result, "signed_url"):
                signed_url = result.signed_url

            if not signed_url:
                raise StorageSignedUrlError(f"No signedURL in response: {result!r}")

            logger.debug("Signed URL generated", path=path)
            return signed_url
        except (StorageSignedUrlError, StorageNotFoundError):
            raise
        except Exception as exc:
            # Detect missing-object errors from the Supabase storage3 library.
            # StorageApiError carries a .status attribute (int or str) set from
            # the HTTP response status code; 404 means the object doesn't exist.
            status = getattr(exc, "status", None)
            if status is not None and int(status) == 404:
                logger.warning("Storage object not found", path=path)
                raise StorageNotFoundError(f"Object not found at path: {path}") from exc
            logger.error("Failed to generate signed URL", path=path, error=str(exc))
            raise StorageSignedUrlError(f"Failed to generate signed URL: {exc}") from exc

    async def delete(self, path: str) -> None:
        """Delete *path* from Supabase Storage."""
        try:
            logger.debug("Deleting file from storage", path=path, bucket=self._bucket)
            await asyncio.to_thread(lambda: self._storage().remove([path]))
            logger.info("File deleted from storage", path=path)
        except Exception as exc:
            logger.error("Storage deletion failed", path=path, error=str(exc))
            raise StorageDeleteError(f"Failed to delete file from storage: {exc}") from exc


# ---------------------------------------------------------------------------
# Stub for future Azure Blob Storage backend
# ---------------------------------------------------------------------------


class AzureBlobStorageClient:
    """Stub — wires in Azure Blob Storage when configured.

    Set ``STORAGE_BACKEND=azure`` in the environment and provide the
    necessary ``AZURE_STORAGE_CONNECTION_STRING`` / ``AZURE_STORAGE_CONTAINER``
    variables.  Not yet implemented.
    """

    def __init__(self, container: str) -> None:  # noqa: D107
        self._container = container

    async def upload(
        self, data: bytes, path: str, content_type: str = "application/octet-stream"
    ) -> str:
        raise NotImplementedError("Azure Blob Storage backend is not yet implemented.")

    async def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("Azure Blob Storage backend is not yet implemented.")

    async def delete(self, path: str) -> None:
        raise NotImplementedError("Azure Blob Storage backend is not yet implemented.")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StorageError(Exception):
    """Base class for storage errors."""


class StorageUploadError(StorageError):
    """Raised when a file upload fails."""


class StorageNotFoundError(StorageError):
    """Raised when the requested path does not exist in storage."""


class StorageSignedUrlError(StorageError):
    """Raised when signed URL generation fails."""


class StorageDeleteError(StorageError):
    """Raised when a file deletion fails."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    """Return (and lazily create) the application-wide StorageClient.

    The backend is selected by ``settings.storage_backend``:
    - ``"supabase"`` (default) → :class:`SupabaseStorageClient`
    - ``"azure"``              → not yet implemented; raises ``ValueError`` at startup.

    Returns:
        A :class:`StorageClient` instance.

    Raises:
        ValueError: If ``storage_backend`` is unsupported or not yet implemented.
    """
    global _storage_client

    if _storage_client is not None:
        return _storage_client

    settings = get_settings()
    backend = settings.storage_backend.lower()
    bucket = settings.storage_bucket

    if backend == "supabase":
        _storage_client = SupabaseStorageClient(bucket=bucket)
    elif backend == "azure":
        raise ValueError(
            "Azure Blob Storage backend is not yet implemented. Set STORAGE_BACKEND to 'supabase'."
        )
    else:
        raise ValueError(
            f"Unsupported storage backend: {backend!r}. Set STORAGE_BACKEND to 'supabase'."
        )

    logger.info("Storage client initialised", backend=backend, bucket=bucket)
    return _storage_client
