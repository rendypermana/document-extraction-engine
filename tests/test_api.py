import asyncio
import tempfile
import time
from io import BytesIO
from pathlib import Path

import pymupdf
import pytest
from app.config import Settings
from app.core.errors import ProviderAuthError, ProviderRateLimitError
from app.core.schemas import GenerationRequest, GenerationResponse
from app.main import create_application
from app.providers.fake import FakeProvider
from fastapi.testclient import TestClient
from PIL import Image


def _pdf_bytes(*page_texts: str) -> bytes:
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page(width=240, height=160)
        page.insert_text((20, 35), text)
    return document.tobytes()


def _png_bytes() -> bytes:
    image = Image.new("RGB", (20, 20), color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "provider": "fake",
        "max_retries": 0,
        "ocr_enabled": False,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _client(
    *,
    settings: Settings | None = None,
    provider_factory=None,
) -> TestClient:
    return TestClient(
        create_application(
            settings or _settings(),
            provider_factory=provider_factory or (lambda _: FakeProvider()),
        )
    )


def _create_run(client: TestClient, file_bytes: bytes, filename: str = "sample.pdf"):
    mime = "image/png" if filename.endswith(".png") else "application/pdf"
    return client.post(
        "/api/extract",
        files={"file": (filename, file_bytes, mime)},
        data={"instructions": "Extract all visible content.", "provider": "fake"},
    )


def _wait_for_terminal(client: TestClient, run_id: str) -> dict:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        state = response.json()
        if state["status"] in {"completed", "completed_with_warnings", "failed"}:
            return state
        time.sleep(0.01)
    raise AssertionError("run did not reach a terminal state")


def test_health_provider_and_domain_routes_return_safe_catalogs() -> None:
    settings = _settings(
        provider="openrouter",
        openrouter_api_key="test-key-do-not-return",
        openrouter_model="provider/model",
        openrouter_vision=True,
        openrouter_structured_output=True,
    )
    with _client(settings=settings) as client:
        assert client.get("/api/health").json() == {"status": "ok"}

        provider_response = client.get("/api/providers")
        assert provider_response.status_code == 200
        providers = provider_response.json()
        openrouter = next(item for item in providers["providers"] if item["id"] == "openrouter")
        assert providers["default"] == "openrouter"
        assert openrouter["available"] is True
        assert openrouter["model"] == "provider/model"
        assert openrouter["capabilities"]["vision"] is True
        assert "test-key-do-not-return" not in provider_response.text
        gemini = next(item for item in providers["providers"] if item["id"] == "gemini")
        assert gemini["unavailable_reason"] == "API key or model is not configured"

        domains_response = client.get("/api/domains")
        assert domains_response.status_code == 200
        domains = domains_response.json()["domains"]
        assert {domain["id"] for domain in domains} >= {"generic", "research_paper", "tax_form"}
        openapi = client.get("/openapi.json").json()
        request_body = openapi["paths"]["/api/extract"]["post"]["requestBody"]
        assert "multipart/form-data" in request_body["content"]


def test_static_ui_is_served_from_the_same_application() -> None:
    with _client() as client:
        page = client.get("/")
        assert page.status_code == 200
        assert page.headers["cache-control"] == "no-cache"
        assert '<html lang="en">' in page.text
        assert "Run extraction" in page.text
        assert 'id="opt-cache"' not in page.text
        assert 'id="opt-aggregate"' not in page.text
        assert "Use page cache" not in page.text
        assert "Merge tables across pages" not in page.text

        script = client.get("/js/api.js")
        assert script.status_code == 200
        assert script.headers["cache-control"] == "no-cache"
        assert "FormData" in script.text


@pytest.mark.parametrize(
    ("filename", "content", "mime", "expected_pages"),
    [
        ("report.pdf", _pdf_bytes("First page", "Second page"), "application/pdf", 2),
        ("scan.png", _png_bytes(), "image/png", 1),
    ],
)
def test_extract_returns_accepted_and_polling_reaches_terminal(
    filename: str,
    content: bytes,
    mime: str,
    expected_pages: int,
) -> None:
    with _client() as client:
        response = client.post(
            "/api/extract",
            files={"file": (filename, content, mime)},
            data={"instructions": "Extract content.", "provider": "fake"},
        )
        assert response.status_code == 202
        accepted = response.json()
        assert accepted["status"] == "queued"
        assert accepted["status_url"] == f"/api/runs/{accepted['run_id']}"

        state = _wait_for_terminal(client, accepted["run_id"])
        assert state["status"] == "completed"
        assert state["progress"]["pages_total"] == expected_pages
        assert state["progress"]["pages_done"] == expected_pages
        assert state["metadata"]["provider"] == "fake"
        assert state["metadata"]["usage"]["available"] is False
        assert state["metadata"]["validation"]["all_pages_processed"] is True
        assert state["result"]["markdown"].startswith("# Extraction results")

        markdown = client.get(f"/api/runs/{accepted['run_id']}/markdown")
        assert markdown.status_code == 200
        assert markdown.headers["content-type"] == "text/markdown; charset=utf-8"
        expected_filename = "report.md" if filename.endswith(".pdf") else "scan.md"
        assert (
            markdown.headers["content-disposition"] == f'attachment; filename="{expected_filename}"'
        )
        assert markdown.text == state["result"]["markdown"]


@pytest.mark.parametrize(
    ("files", "data", "settings", "expected_status", "expected_code"),
    [
        ({}, {"instructions": "Extract."}, None, 400, "missing_field"),
        (
            {"file": ("sample.pdf", b"%PDF-1.7 data", "application/pdf")},
            {"instructions": ""},
            None,
            400,
            "empty_instructions",
        ),
        (
            {"file": ("empty.pdf", b"", "application/pdf")},
            {"instructions": "Extract."},
            None,
            400,
            "empty_file",
        ),
        (
            {"file": ("archive.zip", b"PK\x03\x04data", "application/zip")},
            {"instructions": "Extract."},
            None,
            415,
            "unsupported_file_type",
        ),
        (
            {"file": ("broken.pdf", b"%PDF-not-a-valid-document", "application/pdf")},
            {"instructions": "Extract."},
            None,
            422,
            "file_corrupt",
        ),
        (
            {"file": ("sample.pdf", _pdf_bytes("x"), "application/pdf")},
            {"instructions": "12345"},
            {"max_instruction_chars": 4},
            422,
            "instructions_too_long",
        ),
        (
            {"file": ("sample.pdf", _pdf_bytes("x"), "application/pdf")},
            {"instructions": "Extract.", "provider": "not-a-provider"},
            None,
            400,
            "unknown_provider",
        ),
        (
            {"file": ("sample.pdf", _pdf_bytes("x"), "application/pdf")},
            {"instructions": "Extract.", "provider": "gemini"},
            None,
            400,
            "provider_unavailable",
        ),
        (
            {"file": ("sample.pdf", _pdf_bytes("x"), "application/pdf")},
            {"instructions": "Extract.", "domain": "missing_domain"},
            None,
            400,
            "unknown_domain",
        ),
    ],
)
def test_extract_input_errors_use_the_api_error_shape(
    files: dict,
    data: dict,
    settings: dict[str, object] | None,
    expected_status: int,
    expected_code: str,
) -> None:
    app_settings = _settings(**settings) if settings else _settings()
    with _client(settings=app_settings) as client:
        response = client.post("/api/extract", files=files, data=data)
    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["message"]
    if expected_code == "provider_unavailable":
        assert response.json()["error"]["message"] == "The selected provider is not configured."


def test_framework_request_validation_message_is_indonesian() -> None:
    with _client() as client:
        response = client.post(
            "/api/extract",
            files={"file": ("sample.pdf", _pdf_bytes("x"), "application/pdf")},
            data={"instructions": "Extract.", "use_cache": "not-a-boolean"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "invalid_request",
        "message": "Invalid request.",
    }


@pytest.mark.parametrize("option", ["use_cache", "aggregate"])
def test_unimplemented_processing_options_are_rejected(option: str) -> None:
    with _client() as client:
        response = client.post(
            "/api/extract",
            files={"file": ("sample.pdf", _pdf_bytes("x"), "application/pdf")},
            data={"instructions": "Extract.", option: "true"},
        )

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "unsupported_option",
        "message": "The page is out of date. Reload it before starting a new extraction.",
        "details": {"options": [option]},
    }


def test_extract_enforces_upload_size_limit() -> None:
    settings = _settings(max_upload_mb=1)
    with _client(settings=settings) as client:
        response = client.post(
            "/api/extract",
            files={
                "file": (
                    "large.pdf",
                    _pdf_bytes("x") + b"x" * (1024 * 1024),
                    "application/pdf",
                )
            },
            data={"instructions": "Extract.", "provider": "fake"},
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_partial_provider_failure_is_reported_without_losing_other_pages() -> None:
    provider = FakeProvider(fail_on_calls={1: ProviderRateLimitError("Rate limit exceeded.")})
    with _client(provider_factory=lambda _: provider) as client:
        created = _create_run(client, _pdf_bytes("Page one", "Page two"))
        state = _wait_for_terminal(client, created.json()["run_id"])

    assert state["status"] == "completed_with_warnings"
    assert state["progress"]["pages_failed"] == 1
    assert state["progress"]["pages_done"] == 1
    assert state["errors"][0]["code"] == "provider_rate_limit"
    assert state["errors"][0]["page"] == 1
    assert state["metadata"]["validation"]["all_pages_processed"] is False


def test_provider_auth_failure_is_a_failed_terminal_run() -> None:
    provider = FakeProvider(fail_on_calls={1: ProviderAuthError("Provider rejected credentials.")})
    with _client(provider_factory=lambda _: provider) as client:
        created = _create_run(client, _pdf_bytes("Page one"))
        state = _wait_for_terminal(client, created.json()["run_id"])

    assert state["status"] == "failed"
    assert state["result"] is None
    assert state["errors"][0]["code"] == "provider_auth"
    assert state["progress"]["pages_failed"] == 1


def test_run_status_exposes_running_progress_and_download_rejects_pending_run() -> None:
    class SlowFakeProvider(FakeProvider):
        async def generate(self, request: GenerationRequest) -> GenerationResponse:
            await asyncio.sleep(0.15)
            return await super().generate(request)

    with _client(provider_factory=lambda _: SlowFakeProvider()) as client:
        created = _create_run(client, _pdf_bytes("Page one", "Page two"))
        run_id = created.json()["run_id"]
        pending_download = client.get(f"/api/runs/{run_id}/markdown")
        assert pending_download.status_code == 409
        assert pending_download.json()["error"]["code"] == "run_not_ready"

        running = client.get(f"/api/runs/{run_id}").json()
        assert running["status"] in {"queued", "running"}
        state = _wait_for_terminal(client, run_id)
        assert state["status"] == "completed"


def test_active_run_limit_returns_429() -> None:
    class SlowFakeProvider(FakeProvider):
        async def generate(self, request: GenerationRequest) -> GenerationResponse:
            await asyncio.sleep(0.2)
            return await super().generate(request)

    with _client(
        settings=_settings(max_active_runs=1),
        provider_factory=lambda _: SlowFakeProvider(),
    ) as client:
        first = _create_run(client, _pdf_bytes("First page"))
        assert first.status_code == 202
        second = _create_run(client, _pdf_bytes("Second page"))
        assert second.status_code == 429
        assert second.json()["error"]["code"] == "too_many_runs"


def test_download_filename_is_sanitized() -> None:
    with _client() as client:
        created = client.post(
            "/api/extract",
            files={"file": ("../../unsafe report.pdf", _pdf_bytes("Page"), "application/pdf")},
            data={"instructions": "Extract.", "provider": "fake"},
        )
        state = _wait_for_terminal(client, created.json()["run_id"])
        response = client.get(f"/api/runs/{state['run_id']}/markdown")
    assert response.headers["content-disposition"] == 'attachment; filename="unsafe-report.md"'


def test_temporary_upload_is_removed_after_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    with _client() as client:
        created = _create_run(client, _pdf_bytes("Page"))
        state = _wait_for_terminal(client, created.json()["run_id"])
    assert state["status"] == "completed"
    assert list(tmp_path.iterdir()) == []


def test_run_not_found_has_stable_error_shape() -> None:
    with _client() as client:
        response = client.get("/api/runs/not-a-run")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "run_not_found"
