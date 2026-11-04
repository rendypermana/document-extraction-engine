"""PDF loader using PyMuPDF for rendered pages and text-layer evidence."""

from __future__ import annotations

from math import ceil

import pymupdf

from app.config import Settings, get_settings
from app.core.errors import DocumentLoadError, UnsupportedInputError
from app.core.schemas import LoadedDocument, Page
from app.loaders.common import (
    extract_digital_text_blocks,
    extract_ocr_text_blocks,
    validate_file_input,
)


class PDFLoader:
    """Render each PDF page and extract text blocks with normalized bounds."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def supports(self, mime: str, filename: str) -> bool:
        return mime == "application/pdf" and filename.lower().endswith(".pdf")

    def load(
        self,
        data: bytes,
        filename: str,
        declared_mime: str | None = None,
    ) -> LoadedDocument:
        validate_file_input(
            data,
            filename,
            self._settings,
            expected_mime="application/pdf",
            declared_mime=declared_mime,
        )

        try:
            document = pymupdf.open(stream=data, filetype="pdf")
            with document:
                if document.needs_pass:
                    raise DocumentLoadError("Password-protected PDFs are not supported.")
                if document.page_count == 0:
                    raise DocumentLoadError("The PDF contains no pages.")

                pages = [
                    self._load_page(page, page_number)
                    for page_number, page in enumerate(document, start=1)
                ]
        except DocumentLoadError:
            raise
        except (pymupdf.FileDataError, RuntimeError, ValueError, OSError) as exc:
            raise DocumentLoadError("The PDF file could not be read.") from exc

        return LoadedDocument(filename=filename, source_kind="pdf", pages=pages)

    def _load_page(self, page: pymupdf.Page, page_number: int) -> Page:
        page_rect = page.rect
        scale = self._settings.render_dpi / 72
        expected_width = ceil(page_rect.width * scale)
        expected_height = ceil(page_rect.height * scale)
        if expected_width * expected_height > self._settings.max_image_pixels:
            raise UnsupportedInputError(
                f"Rendered PDF page {page_number} exceeds the configured pixel limit."
            )

        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
        if pixmap.width * pixmap.height > self._settings.max_image_pixels:
            raise UnsupportedInputError(
                f"Rendered PDF page {page_number} exceeds the configured pixel limit."
            )

        text_blocks = extract_digital_text_blocks(page, page_number)
        text_source = "digital" if text_blocks else "none"
        ocr_error = None
        if not text_blocks:
            text_blocks, ocr_error = extract_ocr_text_blocks(
                page,
                page_number,
                self._settings,
            )
            if text_blocks:
                text_source = "ocr"

        return Page(
            number=page_number,
            width_px=pixmap.width,
            height_px=pixmap.height,
            image=pixmap.tobytes("png"),
            image_mime="image/png",
            text_blocks=text_blocks,
            text_source=text_source,
            ocr_error=ocr_error,
        )
