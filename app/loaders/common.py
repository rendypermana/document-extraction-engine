"""Shared content sniffing and input checks for document loaders."""

from pathlib import PurePath

from app.config import Settings
from app.core.errors import UnsupportedInputError

_PDF_SIGNATURE = b"%PDF-"
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"

_EXTENSIONS_BY_MIME = {
    "application/pdf": {".pdf"},
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
}


def sniff_mime_type(data: bytes) -> str | None:
    """Identify supported formats from their file signatures."""
    if _PDF_SIGNATURE in data[:1024]:
        return "application/pdf"
    if data.startswith(_PNG_SIGNATURE):
        return "image/png"
    if data.startswith(_JPEG_SIGNATURE):
        return "image/jpeg"
    return None


def validate_file_input(
    data: bytes,
    filename: str,
    settings: Settings,
    *,
    expected_mime: str | None = None,
    declared_mime: str | None = None,
) -> str:
    """Validate upload size, signature, extension, and optional declared MIME."""
    if not data:
        raise UnsupportedInputError("The uploaded file is empty.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise UnsupportedInputError("The file size exceeds the configured limit.")

    detected_mime = sniff_mime_type(data)
    if detected_mime is None:
        raise UnsupportedInputError("Supported formats are PDF, PNG, and JPG.")

    suffix = PurePath(filename.replace("\\", "/")).suffix.lower()
    if suffix not in _EXTENSIONS_BY_MIME[detected_mime]:
        raise UnsupportedInputError("The file extension does not match its document format.")

    if expected_mime is not None and detected_mime != expected_mime:
        raise UnsupportedInputError("The document content does not match the selected loader.")

    if declared_mime:
        normalized_mime = declared_mime.split(";", maxsplit=1)[0].strip().lower()
        if normalized_mime != detected_mime:
            raise UnsupportedInputError("The declared MIME type does not match the file content.")

    return detected_mime
