"""Content-aware registry for supported document loaders."""

from __future__ import annotations

from collections.abc import Sequence

from app.config import Settings, get_settings
from app.core.errors import UnsupportedInputError
from app.core.interfaces import Loader
from app.core.schemas import LoadedDocument
from app.loaders.common import validate_file_input
from app.loaders.image import ImageLoader
from app.loaders.pdf import PDFLoader


class LoaderRegistry:
    """Select a loader only after checking content, name, size, and declared MIME."""

    def __init__(
        self,
        loaders: Sequence[Loader] | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._loaders = tuple(loaders or (PDFLoader(self._settings), ImageLoader(self._settings)))

    def load(
        self,
        data: bytes,
        filename: str,
        declared_mime: str | None = None,
    ) -> LoadedDocument:
        detected_mime = validate_file_input(
            data,
            filename,
            self._settings,
            declared_mime=declared_mime,
        )
        matching_loaders = [
            loader for loader in self._loaders if loader.supports(detected_mime, filename)
        ]
        if len(matching_loaders) != 1:
            raise UnsupportedInputError("No unique loader is registered for this file.")

        return matching_loaders[0].load(data, filename)


def load_document(
    data: bytes,
    filename: str,
    declared_mime: str | None = None,
    settings: Settings | None = None,
) -> LoadedDocument:
    """Convenience function to load a supported document with the default registry."""
    return LoaderRegistry(settings=settings).load(data, filename, declared_mime)
