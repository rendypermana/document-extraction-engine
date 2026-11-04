"""PNG/JPG loader using Pillow with orientation and pixel-limit handling."""

from __future__ import annotations

import warnings
from io import BytesIO
from math import sqrt

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import Settings, get_settings
from app.core.errors import DocumentLoadError
from app.core.schemas import LoadedDocument, Page
from app.loaders.common import validate_file_input

_SUPPORTED_IMAGE_FORMATS = {
    "image/png": "PNG",
    "image/jpeg": "JPEG",
}


class ImageLoader:
    """Normalize supported images into a single logical document page."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def supports(self, mime: str, filename: str) -> bool:
        extension = filename.lower().rsplit(".", maxsplit=1)
        if len(extension) != 2:
            return False
        suffix = f".{extension[-1]}"
        return (mime == "image/png" and suffix == ".png") or (
            mime == "image/jpeg" and suffix in {".jpg", ".jpeg"}
        )

    def load(
        self,
        data: bytes,
        filename: str,
        declared_mime: str | None = None,
    ) -> LoadedDocument:
        mime = validate_file_input(
            data,
            filename,
            self._settings,
            declared_mime=declared_mime,
        )
        expected_format = _SUPPORTED_IMAGE_FORMATS.get(mime)
        if expected_format is None:
            raise DocumentLoadError("The selected image format is not supported.")

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as source:
                    if source.format != expected_format:
                        raise DocumentLoadError(
                            "The file signature does not match the image format."
                        )
                    source.verify()

                with Image.open(BytesIO(data)) as source:
                    oriented = ImageOps.exif_transpose(source)
                    if oriented.width * oriented.height > self._settings.max_image_pixels:
                        scale = sqrt(
                            self._settings.max_image_pixels / (oriented.width * oriented.height)
                        )
                        target = (
                            max(1, int(oriented.width * scale)),
                            max(1, int(oriented.height * scale)),
                        )
                        oriented.thumbnail(target, Image.Resampling.LANCZOS)

                    has_alpha = "A" in oriented.getbands() or "transparency" in oriented.info
                    normalized = oriented.convert("RGBA" if has_alpha else "RGB")
                    output = BytesIO()
                    normalized.save(output, format="PNG")
        except DocumentLoadError:
            raise
        except (
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
            OSError,
            SyntaxError,
            UnidentifiedImageError,
            ValueError,
        ) as exc:
            raise DocumentLoadError("The image file could not be read.") from exc

        image_bytes = output.getvalue()
        return LoadedDocument(
            filename=filename,
            source_kind="image",
            pages=[
                Page(
                    number=1,
                    width_px=normalized.width,
                    height_px=normalized.height,
                    image=image_bytes,
                    image_mime="image/png",
                    text_blocks=None,
                )
            ],
        )
