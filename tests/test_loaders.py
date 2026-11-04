from io import BytesIO

import pymupdf
import pytest
from app.config import Settings
from app.core.errors import DocumentLoadError, UnsupportedInputError
from app.loaders.image import ImageLoader
from app.loaders.pdf import PDFLoader
from app.loaders.registry import LoaderRegistry, load_document
from PIL import Image


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **overrides)


def _pdf_bytes(*, pages: int = 1, rotate_first: bool = False, with_text: bool = True) -> bytes:
    document = pymupdf.open()
    for index in range(pages):
        page = document.new_page(width=200, height=100)
        if with_text:
            page.insert_text((20, 30), f"Evidence page {index + 1}")
        if rotate_first and index == 0:
            page.set_rotation(90)
    return document.tobytes()


def _image_bytes(
    image_format: str = "PNG",
    size: tuple[int, int] = (20, 10),
    *,
    exif_orientation: int | None = None,
) -> bytes:
    image = Image.new("RGB", size, color="white")
    output = BytesIO()
    options: dict[str, object] = {}
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation
        options["exif"] = exif
    image.save(output, format=image_format, **options)
    return output.getvalue()


def test_pdf_loader_reads_each_page_and_normalizes_text_block_bounds() -> None:
    document = PDFLoader(_settings(render_dpi=72)).load(
        _pdf_bytes(pages=2),
        "research.pdf",
    )

    assert document.source_kind == "pdf"
    assert len(document.pages) == 2
    assert document.pages[0].number == 1
    assert document.pages[1].number == 2
    assert document.pages[0].image_mime == "image/png"
    assert document.pages[0].text_blocks
    assert document.pages[0].text_source == "digital"
    assert document.pages[0].text_blocks[0].text == "Evidence page 1"
    x0, y0, x1, y1 = document.pages[0].text_blocks[0].bbox
    assert 0 <= x0 < x1 <= 1
    assert 0 <= y0 < y1 <= 1


def test_pdf_loader_applies_page_rotation_to_render_and_text_bounds() -> None:
    page = (
        PDFLoader(_settings(render_dpi=72))
        .load(
            _pdf_bytes(rotate_first=True),
            "rotated.pdf",
        )
        .pages[0]
    )

    assert (page.width_px, page.height_px) == (100, 200)
    assert page.text_blocks
    x0, y0, x1, y1 = page.text_blocks[0].bbox
    assert 0.5 < x0 < x1 < 0.9
    assert 0.05 < y0 < y1 < 0.6


def test_pdf_without_text_layer_uses_none() -> None:
    page = (
        PDFLoader(_settings(render_dpi=72))
        .load(
            _pdf_bytes(with_text=False),
            "scan.pdf",
        )
        .pages[0]
    )

    assert page.text_blocks is None


def test_pdf_loader_uses_ocr_for_pages_without_digital_text(monkeypatch) -> None:
    class OCRTextPage:
        def extractDICT(self):
            return {
                "blocks": [
                    {
                        "type": 0,
                        "bbox": (20, 10, 100, 25),
                        "lines": [{"spans": [{"text": "Scanned evidence"}]}],
                    }
                ]
            }

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", lambda *args, **kwargs: OCRTextPage())

    page = PDFLoader(_settings(render_dpi=72)).load(
        _pdf_bytes(with_text=False),
        "scan.pdf",
    ).pages[0]

    assert page.text_source == "ocr"
    assert page.text_blocks
    assert page.text_blocks[0].text == "Scanned evidence"
    assert page.ocr_error is None


def test_image_loader_uses_ocr_and_reports_missing_tesseract(monkeypatch) -> None:
    def missing_tesseract(*args, **kwargs):
        raise RuntimeError("No tessdata specified and Tesseract is not installed")

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", missing_tesseract)
    page = ImageLoader(_settings()).load(
        _image_bytes(),
        "scan.png",
    ).pages[0]

    assert page.text_source == "none"
    assert page.text_blocks is None
    assert page.ocr_error == (
        "OCR is unavailable: install Tesseract OCR and the configured language data."
    )


def test_image_loader_adds_ocr_text_blocks_when_available(monkeypatch) -> None:
    class OCRTextPage:
        def extractDICT(self):
            return {
                "blocks": [
                    {
                        "type": 0,
                        "bbox": (1, 1, 7, 5),
                        "lines": [{"spans": [{"text": "Printed label"}]}],
                    }
                ]
            }

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", lambda *args, **kwargs: OCRTextPage())
    page = ImageLoader(_settings(render_dpi=72)).load(
        _image_bytes(),
        "scan.png",
    ).pages[0]

    assert page.text_source == "ocr"
    assert page.text_blocks
    assert page.text_blocks[0].text == "Printed label"


def test_digital_pdf_does_not_run_ocr(monkeypatch) -> None:
    def unexpected_ocr(*args, **kwargs):
        raise AssertionError("digital text should not trigger OCR")

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", unexpected_ocr)
    page = PDFLoader(_settings(render_dpi=72)).load(
        _pdf_bytes(),
        "digital.pdf",
    ).pages[0]

    assert page.text_source == "digital"
    assert page.text_blocks


@pytest.mark.parametrize(
    ("image_format", "filename", "mime"),
    [
        ("PNG", "form.png", "image/png"),
        ("JPEG", "photo.jpg", "image/jpeg"),
    ],
)
def test_image_loader_accepts_png_and_jpeg(image_format, filename, mime) -> None:
    document = load_document(
        _image_bytes(image_format),
        filename,
        declared_mime=mime,
        settings=_settings(),
    )

    assert document.source_kind == "image"
    assert len(document.pages) == 1
    assert document.pages[0].number == 1
    assert document.pages[0].text_blocks is None
    assert document.pages[0].image_mime == "image/png"


def test_image_loader_normalizes_exif_orientation() -> None:
    page = (
        ImageLoader(_settings())
        .load(
            _image_bytes("JPEG", (30, 10), exif_orientation=6),
            "oriented.jpeg",
        )
        .pages[0]
    )

    assert (page.width_px, page.height_px) == (10, 30)


def test_image_loader_downscales_to_configured_pixel_limit() -> None:
    page = (
        ImageLoader(_settings(max_image_pixels=100))
        .load(
            _image_bytes(size=(20, 20)),
            "large.png",
        )
        .pages[0]
    )

    assert page.width_px * page.height_px <= 100


def test_registry_rejects_empty_unsupported_and_mismatched_inputs() -> None:
    registry = LoaderRegistry(settings=_settings())
    png = _image_bytes()

    with pytest.raises(UnsupportedInputError, match="file is empty"):
        registry.load(b"", "empty.pdf")
    with pytest.raises(UnsupportedInputError, match="Supported formats are PDF"):
        registry.load(b"not a document", "document.bin")
    with pytest.raises(UnsupportedInputError, match="file extension"):
        registry.load(png, "misleading.jpg")
    with pytest.raises(UnsupportedInputError, match="MIME type"):
        registry.load(png, "form.png", declared_mime="image/jpeg")


def test_registry_rejects_uploads_over_configured_byte_limit() -> None:
    registry = LoaderRegistry(settings=_settings(max_upload_mb=1))

    with pytest.raises(UnsupportedInputError, match="file size"):
        registry.load(b"x" * (1024 * 1024 + 1), "large.pdf")


def test_corrupt_pdf_and_image_raise_document_load_errors() -> None:
    settings = _settings(render_dpi=72)

    with pytest.raises(DocumentLoadError, match="PDF file could not be read"):
        PDFLoader(settings).load(b"%PDF-1.7\ninvalid", "corrupt.pdf")

    with pytest.raises(DocumentLoadError, match="image file could not be read"):
        ImageLoader(settings).load(b"\x89PNG\r\n\x1a\ninvalid", "corrupt.png")


def test_pdf_render_obeys_configured_pixel_limit() -> None:
    loader = PDFLoader(_settings(render_dpi=72, max_image_pixels=1_000))

    with pytest.raises(UnsupportedInputError, match="configured pixel limit"):
        loader.load(_pdf_bytes(), "large-page.pdf")


def test_registry_requires_a_unique_matching_loader() -> None:
    class AmbiguousLoader:
        def supports(self, mime: str, filename: str) -> bool:
            return True

        def load(self, data: bytes, filename: str):
            raise AssertionError("ambiguous loaders must not be called")

    registry = LoaderRegistry(
        loaders=(AmbiguousLoader(), AmbiguousLoader()),
        settings=_settings(),
    )

    with pytest.raises(UnsupportedInputError, match="No unique loader"):
        registry.load(_image_bytes(), "form.png")
