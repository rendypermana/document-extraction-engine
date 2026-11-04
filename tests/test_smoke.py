import app
import app.aggregation
import app.api
import app.core
import app.extraction
import app.loaders
import app.providers
import app.rendering
import app.validation


def test_packages_are_importable() -> None:
    """Kerangka package M1.1 harus dapat diimpor tanpa efek samping."""
    assert app.__doc__ is not None
