"""FastAPI routes and composition for the extraction API."""

from __future__ import annotations

import asyncio
import logging
import re
import tempfile
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from starlette import status
from starlette.staticfiles import StaticFiles

from app.api.contracts import (
    DomainInfo,
    DomainList,
    ProviderInfo,
    ProviderList,
    RunCreated,
)
from app.api.run_store import RunStore
from app.config import Settings
from app.core.errors import (
    AppError,
    ConfigError,
    DocumentLoadError,
    ProviderAuthError,
    ProviderError,
    UnsupportedInputError,
)
from app.core.interfaces import DomainProfileLoader, Loader
from app.core.pipeline import ExtractionPipeline
from app.core.schemas import (
    DomainProfile,
    Issue,
    LoadedDocument,
    PageProgress,
    PipelineOutput,
    ProviderCapabilities,
    RunMetadata,
    RunProgress,
    RunState,
    RunStatus,
    UsageSummary,
    ValidationSummary,
)
from app.loaders.common import sniff_mime_type, validate_file_input

logger = logging.getLogger(__name__)
_SUPPORTED_PROVIDERS = ("gemini", "openrouter", "groq", "fake")
_PROVIDER_LABELS = {
    "gemini": "Gemini",
    "openrouter": "OpenRouter",
    "groq": "Groq",
    "fake": "Fake (integration testing)",
}
_OPTIONAL_UPLOAD = File(default=None)


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def _configured_model(settings: Settings, provider_id: str) -> str:
    if provider_id == "gemini":
        return settings.model_name
    if provider_id == "openrouter":
        return settings.openrouter_model.strip()
    if provider_id == "groq":
        return settings.groq_model.strip()
    return "fake-deterministic"


def _provider_configured(settings: Settings, provider_id: str) -> bool:
    if provider_id == "fake":
        return True
    model = _configured_model(settings, provider_id)
    if provider_id == "gemini":
        secret = settings.gemini_api_key
    elif provider_id == "openrouter":
        secret = settings.openrouter_api_key
    elif provider_id == "groq":
        secret = settings.groq_api_key
    else:
        return False
    return bool(secret and secret.get_secret_value().strip() and model)


def _provider_capabilities(settings: Settings, provider_id: str) -> ProviderCapabilities:
    if provider_id == "fake":
        return ProviderCapabilities(
            vision=True,
            structured_output=True,
            max_image_pixels=None,
            max_input_tokens=None,
            reports_usage=False,
        )
    if provider_id == "gemini":
        return ProviderCapabilities(
            vision=True,
            structured_output=True,
            max_image_pixels=None,
            max_input_tokens=None,
            reports_usage=True,
        )
    if provider_id == "openrouter":
        return ProviderCapabilities(
            vision=settings.openrouter_vision,
            structured_output=settings.openrouter_structured_output,
            max_image_pixels=None,
            max_input_tokens=None,
            reports_usage=True,
        )
    if provider_id == "groq":
        return ProviderCapabilities(
            vision=settings.groq_vision,
            structured_output=settings.groq_structured_output,
            max_image_pixels=None,
            max_input_tokens=None,
            reports_usage=True,
        )
    raise ValueError(f"Unknown provider ID: {provider_id}")


def _provider_info(settings: Settings) -> ProviderList:
    providers = []
    for provider_id in _SUPPORTED_PROVIDERS:
        configured = _provider_configured(settings, provider_id)
        providers.append(
            ProviderInfo(
                id=provider_id,
                label=_PROVIDER_LABELS[provider_id],
                model=_configured_model(settings, provider_id),
                available=configured,
                unavailable_reason=None if configured else "API key or model is not configured",
                capabilities=_provider_capabilities(settings, provider_id),
            )
        )
    return ProviderList(default=settings.provider, providers=providers)


def _safe_filename(filename: str) -> str:
    stem = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1].rsplit(".", maxsplit=1)[0]
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-_")
    return safe_stem or "document"


def _initial_progress(document: LoadedDocument) -> RunProgress:
    pages = [
        PageProgress(page=page.number, status="pending", cached=False) for page in document.pages
    ]
    return RunProgress(
        stage="loading",
        pages_total=len(pages),
        pages_done=0,
        pages_failed=0,
        pages=pages,
    )


def _failed_progress(progress: RunProgress) -> RunProgress:
    pages = [
        PageProgress(
            page=page.page,
            status="failed" if page.status == "processing" else page.status,
            cached=page.cached,
        )
        for page in progress.pages
    ]
    return RunProgress(
        stage=progress.stage,
        pages_total=progress.pages_total,
        pages_done=sum(page.status == "done" for page in pages),
        pages_failed=sum(page.status == "failed" for page in pages),
        pages=pages,
    )


def _metadata(
    *,
    provider_id: str,
    model: str,
    started_at: datetime,
    duration_s: float,
    progress: RunProgress,
    prompt_version: str,
    retries: int = 0,
) -> RunMetadata:
    return RunMetadata(
        provider=provider_id,
        model=model,
        prompt_version=prompt_version,
        started_at=started_at,
        duration_s=max(0.0, duration_s),
        usage=UsageSummary(
            input_tokens=None,
            output_tokens=None,
            available=False,
        ),
        retries=retries,
        cache_hits=0,
        pages_total=progress.pages_total,
        pages_processed=progress.pages_done,
        validation=ValidationSummary(
            schema_ok=False,
            all_pages_processed=(
                progress.pages_total > 0
                and progress.pages_done == progress.pages_total
                and progress.pages_failed == 0
            ),
            items_without_evidence=0,
            evidence_unverifiable=0,
            markdown_format_ok=False,
        ),
    )


def _completed_metadata(
    *,
    provider_id: str,
    model: str,
    started_at: datetime,
    duration_s: float,
    progress: RunProgress,
    output: PipelineOutput,
    prompt_version: str,
) -> RunMetadata:
    pages = output.document.pages
    known_input = [
        page.metrics.input_tokens for page in pages if page.metrics.input_tokens is not None
    ]
    known_output = [
        page.metrics.output_tokens for page in pages if page.metrics.output_tokens is not None
    ]
    input_tokens = sum(known_input) if len(known_input) == len(pages) and pages else None
    output_tokens = sum(known_output) if len(known_output) == len(pages) and pages else None
    findings = output.document.findings
    return RunMetadata(
        provider=provider_id,
        model=model,
        prompt_version=prompt_version,
        started_at=started_at,
        duration_s=max(0.0, duration_s),
        usage=UsageSummary(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            available=input_tokens is not None or output_tokens is not None,
        ),
        retries=sum(page.metrics.retries for page in pages),
        cache_hits=sum(page.metrics.cached for page in pages),
        pages_total=progress.pages_total,
        pages_processed=progress.pages_done,
        validation=ValidationSummary(
            schema_ok=not any(issue.code == "provider_invalid_response" for issue in output.errors),
            all_pages_processed=(
                progress.pages_total > 0
                and progress.pages_done == progress.pages_total
                and progress.pages_failed == 0
            ),
            items_without_evidence=sum(
                finding.code == "item_without_evidence" for finding in findings
            ),
            evidence_unverifiable=sum(
                reference.verified is None for reference in output.result.references
            ),
            markdown_format_ok=output.result.markdown.startswith("# Extraction results"),
        ),
    )


def create_app(
    *,
    settings: Settings,
    pipeline_factory: Callable[[str], ExtractionPipeline],
    domains: DomainProfileLoader,
    loaders: Loader,
    prompt_version: str,
) -> FastAPI:
    """Create the API application from dependencies assembled by the composition root."""
    app_settings = settings
    store = RunStore(
        ttl_minutes=app_settings.run_ttl_minutes,
        max_stored_runs=app_settings.max_stored_runs,
        max_active_runs=app_settings.max_active_runs,
    )
    tasks: set[asyncio.Task[None]] = set()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    api = FastAPI(title="Document Extraction Engine", lifespan=lifespan)
    api.state.settings = app_settings
    api.state.run_store = store

    @api.middleware("http")
    async def disable_static_asset_caching(request: Request, call_next):
        response = await call_next(request)
        if not request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @api.exception_handler(ApiError)
    async def handle_api_error(_: Request, error: ApiError) -> JSONResponse:
        body = {"error": {"code": error.code, "message": error.message}}
        if error.details is not None:
            body["error"]["details"] = error.details
        return JSONResponse(status_code=error.status_code, content=body)

    @api.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request,
        __: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_request",
                    "message": "Invalid request.",
                }
            },
        )

    @api.exception_handler(FastAPIHTTPException)
    async def handle_framework_http_error(
        _: Request,
        error: FastAPIHTTPException,
    ) -> JSONResponse:
        code = "invalid_request" if error.status_code < 500 else "internal_error"
        message = "Invalid request." if error.status_code < 500 else "An internal error occurred."
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": code, "message": message}},
        )

    @api.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.error("Unhandled API error: %s", type(error).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An internal error occurred. Please try again.",
                }
            },
        )

    @api.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.get("/api/providers", response_model=ProviderList)
    async def providers() -> ProviderList:
        return _provider_info(app_settings)

    @api.get("/api/domains", response_model=DomainList)
    async def list_domains() -> DomainList:
        return DomainList(
            domains=[
                DomainInfo(
                    id=domain.id,
                    name=domain.name,
                    description=domain.description,
                    default_instructions=domain.default_instructions,
                )
                for domain in domains.list_profiles()
            ]
        )

    @api.post(
        "/api/extract",
        status_code=status.HTTP_202_ACCEPTED,
        response_model=RunCreated,
    )
    async def create_run(
        request: Request,
        file: UploadFile | None = _OPTIONAL_UPLOAD,
        instructions: str | None = Form(default=None),
        provider: str | None = Form(default=None),
        domain: str | None = Form(default=None),
        use_cache: bool = Form(default=False),
        aggregate: bool = Form(default=False),
    ) -> RunCreated:
        form = await request.form()
        if instructions is None and "instructions" in form:
            instructions = ""
        unsupported_options = [
            option
            for option, requested in (
                ("use_cache", use_cache),
                ("aggregate", aggregate),
            )
            if requested
        ]
        if unsupported_options:
            if file is not None:
                await file.close()
            raise ApiError(
                422,
                "unsupported_option",
                "The page is out of date. Reload it before starting a new extraction.",
                {"options": unsupported_options},
            )
        if file is None:
            raise ApiError(400, "missing_field", "The 'file' field is required.")
        if instructions is None:
            await file.close()
            raise ApiError(400, "missing_field", "The 'instructions' field is required.")
        if not instructions.strip():
            await file.close()
            raise ApiError(400, "empty_instructions", "Extraction instructions cannot be empty.")
        if len(instructions) > app_settings.max_instruction_chars:
            await file.close()
            raise ApiError(
                422,
                "instructions_too_long",
                "Extraction instructions exceed the maximum length.",
                {"max_chars": app_settings.max_instruction_chars},
            )

        selected_provider = provider or app_settings.provider
        if selected_provider not in _SUPPORTED_PROVIDERS:
            await file.close()
            raise ApiError(400, "unknown_provider", "The selected provider is not recognized.")
        if not _provider_configured(app_settings, selected_provider):
            await file.close()
            raise ApiError(
                400,
                "provider_unavailable",
                "The selected provider is not configured.",
            )
        try:
            selected_domain = domains.get_profile(domain or None)
        except ConfigError:
            await file.close()
            raise ApiError(
                400,
                "unknown_domain",
                "The selected domain profile is not recognized.",
            ) from None

        max_bytes = app_settings.max_upload_mb * 1024 * 1024
        data = await file.read(max_bytes + 1)
        filename = file.filename or ""
        declared_mime = file.content_type
        await file.close()
        if not data:
            raise ApiError(400, "empty_file", "The uploaded file is empty.")
        if len(data) > max_bytes:
            raise ApiError(
                413,
                "file_too_large",
                "The file exceeds the upload size limit.",
                {"max_upload_mb": app_settings.max_upload_mb},
            )
        if sniff_mime_type(data) is None:
            raise ApiError(
                415,
                "unsupported_file_type",
                "Unsupported file type. Use PDF, PNG, or JPG.",
            )
        try:
            validate_file_input(
                data,
                filename,
                app_settings,
                declared_mime=declared_mime,
            )
        except UnsupportedInputError:
            raise ApiError(
                415,
                "unsupported_file_type",
                "Unsupported file type or file content does not match the declared type.",
            ) from None

        try:
            loaded_document = loaders.load(data, filename, declared_mime)
        except DocumentLoadError:
            raise ApiError(422, "file_corrupt", "The file could not be read.") from None
        except UnsupportedInputError as error:
            raise ApiError(
                413,
                "file_too_large",
                "The file exceeds the configured processing limit.",
            ) from error

        try:
            pipeline = pipeline_factory(selected_provider)
        except ConfigError:
            raise ApiError(
                400, "provider_unavailable", "The selected provider is not configured."
            ) from None

        suffix = Path(filename).suffix.lower()
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="document-extraction-",
                suffix=suffix,
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(data)
        except OSError as error:
            if temporary_path is not None:
                _remove_temporary_upload(temporary_path)
            logger.error("Could not stage upload: %s", type(error).__name__)
            raise ApiError(
                500,
                "internal_error",
                "The temporary upload file could not be prepared.",
            ) from None
        if temporary_path is None:
            raise ApiError(
                500,
                "internal_error",
                "The temporary upload file could not be prepared.",
            )

        now = datetime.now(UTC)
        run_id = str(uuid4())
        initial = RunState(
            run_id=run_id,
            status=RunStatus.queued,
            created_at=now,
            progress=_initial_progress(loaded_document),
            result=None,
            metadata=None,
            errors=[],
            warnings=[],
        )
        if not store.create(initial, filename):
            _remove_temporary_upload(temporary_path)
            raise ApiError(
                429,
                "too_many_runs",
                "The maximum number of active runs has been reached.",
                {"max_active_runs": store.active_limit},
            )

        task = asyncio.create_task(
            _execute_run_and_cleanup(
                run_id,
                loaded_document,
                instructions,
                selected_domain,
                selected_provider,
                _configured_model(app_settings, selected_provider),
                pipeline,
                store,
                prompt_version,
                temporary_path,
            )
        )
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return RunCreated(
            run_id=run_id,
            status=RunStatus.queued,
            status_url=f"/api/runs/{run_id}",
        )

    @api.get("/api/runs/{run_id}", response_model=RunState)
    async def get_run(run_id: str) -> RunState:
        record = store.get(run_id)
        if record is None:
            raise ApiError(404, "run_not_found", "Run not found or has expired.")
        return record.state

    @api.get("/api/runs/{run_id}/markdown")
    async def download_markdown(run_id: str) -> Response:
        record = store.get(run_id)
        if record is None:
            raise ApiError(404, "run_not_found", "Run not found or has expired.")
        if (
            record.state.status
            not in {
                RunStatus.completed,
                RunStatus.completed_with_warnings,
            }
            or record.state.result is None
        ):
            raise ApiError(
                409,
                "run_not_ready",
                "The run is not complete or does not have a Markdown result yet.",
            )
        filename = f"{_safe_filename(record.filename)}.md"
        return Response(
            content=record.state.result.markdown,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    static_dir = Path(__file__).resolve().parents[2] / "static"
    api.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    return api


async def _execute_run_and_cleanup(
    run_id: str,
    document: LoadedDocument,
    instructions: str,
    domain: DomainProfile,
    provider_id: str,
    model: str,
    pipeline: ExtractionPipeline,
    store: RunStore,
    prompt_version: str,
    temporary_path: Path,
) -> None:
    try:
        await _execute_run(
            run_id,
            document,
            instructions,
            domain,
            provider_id,
            model,
            pipeline,
            store,
            prompt_version,
        )
    finally:
        _remove_temporary_upload(temporary_path)


def _remove_temporary_upload(temporary_path: Path) -> None:
    try:
        temporary_path.unlink(missing_ok=True)
    except OSError as error:
        logger.error("Could not remove temporary upload: %s", type(error).__name__)


async def _execute_run(
    run_id: str,
    document: LoadedDocument,
    instructions: str,
    domain: DomainProfile,
    provider_id: str,
    model: str,
    pipeline: ExtractionPipeline,
    store: RunStore,
    prompt_version: str,
) -> None:
    record = store.get(run_id)
    if record is None:
        return
    started_at = datetime.now(UTC)
    started_clock = time.perf_counter()
    store.update_progress(run_id, record.state.progress)
    record.state = record.state.model_copy(update={"status": RunStatus.running})

    def report_progress(progress: RunProgress) -> None:
        store.update_progress(run_id, progress)

    try:
        output = await pipeline.run_loaded(
            document,
            instructions,
            domain=domain,
            on_progress=report_progress,
        )
    except ProviderAuthError as error:
        _finish_failed_run(
            store,
            run_id,
            provider_id,
            model,
            started_at,
            started_clock,
            RunStatus.failed,
            Issue(code=error.code, scope="run", message=error.message),
            prompt_version,
            error.retries,
        )
        return
    except AppError as error:
        _finish_failed_run(
            store,
            run_id,
            provider_id,
            model,
            started_at,
            started_clock,
            RunStatus.failed,
            Issue(code=error.code, scope="run", message=error.message),
            prompt_version,
            error.retries if isinstance(error, ProviderError) else 0,
        )
        return
    except Exception as error:
        logger.error("Run %s failed with %s", run_id, type(error).__name__)
        _finish_failed_run(
            store,
            run_id,
            provider_id,
            model,
            started_at,
            started_clock,
            RunStatus.failed,
            Issue(
                code="internal_error",
                scope="run",
                message="An error occurred while processing the document.",
            ),
            prompt_version,
        )
        return

    record = store.get(run_id)
    if record is None:
        return
    progress = record.state.progress
    status_value = (
        RunStatus.completed_with_warnings
        if output.errors or output.warnings or progress.pages_failed
        else RunStatus.completed
    )
    duration = time.perf_counter() - started_clock
    store.finish(
        run_id,
        status=status_value,
        progress=progress,
        result=output.result,
        metadata=_completed_metadata(
            provider_id=provider_id,
            model=model,
            started_at=started_at,
            duration_s=duration,
            progress=progress,
            output=output,
            prompt_version=prompt_version,
        ),
        errors=output.errors,
        warnings=output.warnings,
    )


def _finish_failed_run(
    store: RunStore,
    run_id: str,
    provider_id: str,
    model: str,
    started_at: datetime,
    started_clock: float,
    status_value: RunStatus,
    error: Issue,
    prompt_version: str,
    retries: int = 0,
) -> None:
    record = store.get(run_id)
    if record is None:
        return
    progress = _failed_progress(record.state.progress)
    store.finish(
        run_id,
        status=status_value,
        progress=progress,
        result=None,
        metadata=_metadata(
            provider_id=provider_id,
            model=model,
            started_at=started_at,
            duration_s=time.perf_counter() - started_clock,
            progress=progress,
            prompt_version=prompt_version,
            retries=retries,
        ),
        errors=[error],
        warnings=[],
    )
