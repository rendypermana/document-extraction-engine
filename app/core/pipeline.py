"""Dependency-injected offline-capable document extraction pipeline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

from app.core.errors import ProviderAuthError, ProviderError, ProviderInvalidResponseError
from app.core.interfaces import (
    DocumentAggregator,
    Loader,
    MarkdownRenderer,
    PageValidator,
    PromptBuilder,
    Provider,
    ResponseParser,
)
from app.core.schemas import (
    DomainProfile,
    Finding,
    GenerationResponse,
    Issue,
    LoadedDocument,
    ModelPageOutput,
    Page,
    PageExtraction,
    PageMetrics,
    PageProgress,
    PipelineOutput,
    RunProgress,
)


class ExtractionPipeline:
    """Run load, per-page extraction, validation, aggregation, and rendering."""

    def __init__(
        self,
        loader: Loader,
        provider: Provider,
        prompt_builder: PromptBuilder,
        parser: ResponseParser,
        validator: PageValidator,
        aggregator: DocumentAggregator,
        renderer: MarkdownRenderer,
    ) -> None:
        self._loader = loader
        self._provider = provider
        self._prompt_builder = prompt_builder
        self._parser = parser
        self._validator = validator
        self._aggregator = aggregator
        self._renderer = renderer

    async def run(
        self,
        data: bytes,
        filename: str,
        instructions: str,
        *,
        declared_mime: str | None = None,
        domain: DomainProfile | None = None,
        on_progress: Callable[[RunProgress], None] | None = None,
    ) -> PipelineOutput:
        document = self._load_document(data, filename, declared_mime)
        return await self.run_loaded(
            document,
            instructions,
            domain=domain,
            on_progress=on_progress,
        )

    async def run_loaded(
        self,
        document: LoadedDocument,
        instructions: str,
        *,
        domain: DomainProfile | None = None,
        on_progress: Callable[[RunProgress], None] | None = None,
    ) -> PipelineOutput:
        page_progress = [
            PageProgress(page=page.number, status="pending", cached=False)
            for page in document.pages
        ]
        self._emit_progress(on_progress, "extracting", page_progress)
        page_results: list[PageExtraction] = []
        for index, page in enumerate(document.pages):
            page_progress[index] = PageProgress(
                page=page.number,
                status="processing",
                cached=False,
            )
            self._emit_progress(on_progress, "extracting", page_progress)
            page_result = await self._extract_page(
                page,
                instructions,
                domain,
                page_total=len(document.pages),
            )
            page_results.append(page_result)
            page_progress[index] = PageProgress(
                page=page.number,
                status="failed" if page_result.status == "failed" else "done",
                cached=page_result.metrics.cached,
            )
            self._emit_progress(on_progress, "extracting", page_progress)

        self._emit_progress(on_progress, "aggregating", page_progress)
        extraction = self._aggregator.aggregate(page_results)
        self._emit_progress(on_progress, "validating", page_progress)
        self._emit_progress(on_progress, "rendering", page_progress)
        result = self._renderer.render(extraction)
        errors = [page.error for page in extraction.pages if page.error is not None]
        warnings = [
            Issue(
                code=finding.code,
                scope="page" if finding.page is not None else "run",
                page=finding.page,
                item_id=finding.item_id,
                message=finding.message,
            )
            for finding in extraction.findings
            if finding.severity == "warning"
        ]
        return PipelineOutput(
            document=extraction,
            result=result,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _emit_progress(
        callback: Callable[[RunProgress], None] | None,
        stage: Literal["loading", "extracting", "aggregating", "validating", "rendering"],
        pages: list[PageProgress],
    ) -> None:
        if callback is None:
            return
        callback(
            RunProgress(
                stage=stage,
                pages_total=len(pages),
                pages_done=sum(page.status == "done" for page in pages),
                pages_failed=sum(page.status == "failed" for page in pages),
                pages=list(pages),
            )
        )

    def _load_document(
        self,
        data: bytes,
        filename: str,
        declared_mime: str | None,
    ) -> LoadedDocument:
        return self._loader.load(data, filename, declared_mime)

    async def _extract_page(
        self,
        page: Page,
        instructions: str,
        domain: DomainProfile | None,
        *,
        page_total: int,
    ) -> PageExtraction:
        if not self._provider.capabilities.vision and not page.text_blocks:
            message = (
                "This page has no readable text layer, and the configured provider does "
                "not support image processing."
            )
            if page.ocr_error:
                message = f"{message} {page.ocr_error}"
            return PageExtraction(
                page=page.number,
                status="failed",
                items=[],
                page_notes=None,
                error=Issue(
                    code="page_unreadable",
                    scope="page",
                    page=page.number,
                    message=message,
                ),
                findings=self._ocr_findings(page),
                metrics=PageMetrics(
                    latency_s=0,
                    attempts=0,
                    retries=0,
                    repaired=False,
                    cached=False,
                ),
            )

        request = self._prompt_builder.build(
            page,
            instructions,
            domain,
            page_total=page_total,
            capabilities=self._provider.capabilities,
        )
        responses: list[GenerationResponse] = []
        repaired = False

        try:
            response = await self._provider.generate(request)
            responses.append(response)
            try:
                output = self._parse_page(response.text, page.number)
            except ProviderInvalidResponseError as initial_error:
                repair_request = self._prompt_builder.build_repair(
                    request,
                    invalid_response=response.text,
                    validation_message=str(initial_error),
                )
                response = await self._provider.generate(repair_request)
                responses.append(response)
                repaired = True
                try:
                    output = self._parse_page(response.text, page.number)
                except ProviderInvalidResponseError as error:
                    raise ProviderInvalidResponseError(
                        error.message,
                        attempts=0,
                        retries=0,
                        latency_s=0,
                    ) from error

            metrics = self._metrics(responses, repaired)
            page_result = self._validator.validate(page, output, metrics)
            return page_result.model_copy(
                update={"findings": self._ocr_findings(page)}
            )
        except ProviderAuthError:
            raise
        except ProviderError as error:
            metrics = self._metrics(responses, repaired).model_copy(
                update={
                    "attempts": sum(response.attempts for response in responses) + error.attempts,
                    "retries": sum(response.retries for response in responses) + error.retries,
                    "latency_s": sum(response.latency_s for response in responses)
                    + error.latency_s,
                }
            )
            return PageExtraction(
                page=page.number,
                status="failed",
                items=[],
                page_notes=None,
                error=Issue(
                    code=error.code,
                    scope="page",
                    page=page.number,
                    message=error.message,
                ),
                findings=self._ocr_findings(page),
                metrics=metrics,
            )

    @staticmethod
    def _ocr_findings(page: Page) -> list[Finding]:
        if not page.ocr_error:
            return []
        return [
            Finding(
                code="ocr_unavailable",
                severity="warning",
                message=page.ocr_error,
                page=page.number,
            )
        ]

    def _parse_page(self, response_text: str, expected_page: int) -> ModelPageOutput:
        output = self._parser.parse(response_text)
        if output.page != expected_page:
            raise ProviderInvalidResponseError(
                "The page number in the model response does not match the requested page."
            )
        return output

    @staticmethod
    def _metrics(
        responses: list[GenerationResponse],
        repaired: bool,
    ) -> PageMetrics:
        usage_values = [response.usage for response in responses]
        input_tokens = (
            sum(usage.input_tokens for usage in usage_values if usage is not None)
            if usage_values
            and all(usage is not None and usage.input_tokens is not None for usage in usage_values)
            else None
        )
        output_tokens = (
            sum(usage.output_tokens for usage in usage_values if usage is not None)
            if usage_values
            and all(usage is not None and usage.output_tokens is not None for usage in usage_values)
            else None
        )
        return PageMetrics(
            latency_s=sum(response.latency_s for response in responses),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            attempts=sum(response.attempts for response in responses),
            retries=sum(response.retries for response in responses),
            repaired=repaired,
            cached=any(response.cached for response in responses),
        )
