"""Application composition root for Uvicorn and Docker."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI

from app.aggregation.document import DocumentAggregator
from app.api.app import create_app
from app.config import Settings, get_settings
from app.core.interfaces import Provider
from app.core.pipeline import ExtractionPipeline
from app.core.resilience import ResilientProvider
from app.domains.registry import DomainProfileRegistry
from app.extraction.parser import JsonResponseParser
from app.extraction.prompt_builder import PROMPT_VERSION, PromptBuilder
from app.loaders.registry import LoaderRegistry
from app.providers.registry import create_provider
from app.rendering.markdown import MarkdownRenderer
from app.validation.page import PageEvidenceValidator


def create_application(
    settings: Settings | None = None,
    *,
    provider_factory: Callable[[Settings], Provider] | None = None,
) -> FastAPI:
    """Assemble concrete adapters and pass their interfaces into the API."""
    app_settings = settings or get_settings()
    domains = DomainProfileRegistry()
    loaders = LoaderRegistry(settings=app_settings)
    selected_provider_factory = provider_factory or create_provider

    def pipeline_factory(provider_id: str) -> ExtractionPipeline:
        selected_settings = app_settings.model_copy(update={"provider": provider_id})
        provider = ResilientProvider(
            selected_provider_factory(selected_settings),
            app_settings,
        )
        return ExtractionPipeline(
            loader=loaders,
            provider=provider,
            prompt_builder=PromptBuilder(),
            parser=JsonResponseParser(),
            validator=PageEvidenceValidator(),
            aggregator=DocumentAggregator(),
            renderer=MarkdownRenderer(),
        )

    return create_app(
        settings=app_settings,
        pipeline_factory=pipeline_factory,
        domains=domains,
        loaders=loaders,
        prompt_version=PROMPT_VERSION,
    )


app = create_application()
