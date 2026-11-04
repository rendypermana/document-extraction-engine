"""Shared content sniffing and input checks for document loaders."""

from pathlib import PurePath

import pymupdf

from app.config import Settings
from app.core.errors import UnsupportedInputError
from app.core.schemas import TextBlock

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


def extract_ocr_text_blocks(
    page: pymupdf.Page,
    page_number: int,
    settings: Settings,
) -> tuple[list[TextBlock] | None, str | None]:
    """Extract OCR text while preserving normalized source-page coordinates."""
    if not settings.ocr_enabled:
        return None, None

    try:
        text_page = page.get_textpage_ocr(
            language=settings.ocr_language,
            dpi=settings.render_dpi,
            full=True,
        )
    except RuntimeError as error:
        if "Tesseract is not installed" in str(error):
            return (
                None,
                "OCR is unavailable: install Tesseract OCR and the configured language data.",
            )
        return None, f"OCR failed: {error}"

    return _text_blocks_from_dict(page, page_number, text_page.extractDICT()), None


def extract_digital_text_blocks(
    page: pymupdf.Page,
    page_number: int,
) -> list[TextBlock] | None:
    """Extract native PDF text with normalized source-page coordinates."""
    return _text_blocks_from_dict(page, page_number, page.get_text("dict", sort=True))


def _text_blocks_from_dict(
    page: pymupdf.Page,
    page_number: int,
    text_page: dict[str, object],
) -> list[TextBlock] | None:
    page_rect = page.rect
    if page_rect.width <= 0 or page_rect.height <= 0:
        raise ValueError(f"PDF page {page_number} has invalid dimensions.")

    blocks: list[TextBlock] = []
    raw_blocks = text_page.get("blocks", [])
    if not isinstance(raw_blocks, list):
        return None

    for block in raw_blocks:
        if not isinstance(block, dict) or block.get("type") != 0:
            continue
        lines = block.get("lines", [])
        if not isinstance(lines, list):
            continue
        text = "\n".join(
            "".join(
                span.get("text", "")
                for span in line.get("spans", [])
                if isinstance(span, dict)
            )
            for line in lines
            if isinstance(line, dict) and isinstance(line.get("spans", []), list)
        ).strip()
        bbox = block.get("bbox")
        if not text or not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
            continue

        bounds = pymupdf.Rect(bbox) * page.rotation_matrix
        x0 = max(0.0, min(1.0, (bounds.x0 - page_rect.x0) / page_rect.width))
        y0 = max(0.0, min(1.0, (bounds.y0 - page_rect.y0) / page_rect.height))
        x1 = max(0.0, min(1.0, (bounds.x1 - page_rect.x0) / page_rect.width))
        y1 = max(0.0, min(1.0, (bounds.y1 - page_rect.y0) / page_rect.height))
        if x1 <= x0 or y1 <= y0:
            continue

        blocks.append(
            TextBlock(
                id=f"b{len(blocks) + 1}",
                text=text,
                bbox=(x0, y0, x1, y1),
            )
        )

    return blocks or None
