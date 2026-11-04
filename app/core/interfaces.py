"""Interfaces for interchangeable providers and document loaders."""

from __future__ import annotations

from typing import Protocol

from app.core.schemas import (
    DocumentExtraction,
    DomainProfile,
    GenerationRequest,
    GenerationResponse,
    LoadedDocument,
    ModelPageOutput,
    Page,
    PageExtraction,
    PageMetrics,
    ProviderCapabilities,
    RunResult,
)


class Provider(Protocol):
    """Model provider adapter contract."""

    name: str
    capabilities: ProviderCapabilities

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate structured model output for one request."""
        ...


class DomainProfileLoader(Protocol):
    """Load domain profiles from configuration without coupling core to YAML."""

    def list_profiles(self) -> list[DomainProfile]:
        """Return all configured profiles in a stable order."""
        ...

    def get_profile(self, profile_id: str | None = None) -> DomainProfile:
        """Return the requested profile or the generic default."""
        ...


class Loader(Protocol):
    """Document loader contract."""

    def supports(self, mime: str, filename: str) -> bool:
        """Return whether this loader can handle the supplied input."""
        ...

    def load(
        self,
        data: bytes,
        filename: str,
        declared_mime: str | None = None,
    ) -> LoadedDocument:
        """Load a document into normalized pages."""
        ...


class PromptBuilder(Protocol):
    """Build model requests without provider-specific behavior."""

    def build(
        self,
        page: Page,
        instructions: str,
        domain: DomainProfile | None = None,
        *,
        page_total: int,
        capabilities: ProviderCapabilities,
    ) -> GenerationRequest:
        """Create a generation request for a single document page."""
        ...

    def build_repair(
        self,
        request: GenerationRequest,
        invalid_response: str,
        validation_message: str,
    ) -> GenerationRequest:
        """Create the single allowed structural repair request."""
        ...


class ResponseParser(Protocol):
    """Parse provider text into the model-owned output schema."""

    def parse(self, response_text: str) -> ModelPageOutput:
        """Parse and validate structured model output."""
        ...


class PageValidator(Protocol):
    """Validate page evidence and semantic findings."""

    def validate(
        self,
        page: Page,
        output: ModelPageOutput,
        metrics: PageMetrics,
    ) -> PageExtraction:
        """Return validated page items and findings."""
        ...


class DocumentAggregator(Protocol):
    """Combine page extractions without invoking a provider."""

    def aggregate(self, pages: list[PageExtraction]) -> DocumentExtraction:
        """Return document-level items and findings."""
        ...


class MarkdownRenderer(Protocol):
    """Render validated document extraction as Markdown and references."""

    def render(self, document: DocumentExtraction) -> RunResult:
        """Render a document result."""
        ...
