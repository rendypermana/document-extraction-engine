"""Pydantic contracts shared by loaders, providers, the pipeline, and the API."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """Shared model configuration for forward-compatible input parsing."""

    model_config = ConfigDict(extra="ignore")


class Status(StrEnum):
    """Extraction confidence/status for an item or its parts."""

    ok = "ok"
    uncertain = "uncertain"
    unreadable = "unreadable"
    missing = "missing"


class ItemType(StrEnum):
    """Supported model output item types."""

    prose = "prose"
    table = "table"
    chart = "chart"
    form_field = "form_field"


BBox: TypeAlias = tuple[float, float, float, float]


class ModelEvidence(ContractModel):
    page: int = Field(ge=1)
    excerpt: str
    bbox: BBox | None = None


class _ModelItemBase(ContractModel):
    status: Status
    is_estimate: bool = False
    evidence: list[ModelEvidence] = Field(default_factory=list)
    notes: str | None = None


class ProseContent(ContractModel):
    heading: str | None = None
    text: str


class ProseItem(_ModelItemBase):
    type: Literal["prose"]
    content: ProseContent


class ColumnDef(ContractModel):
    path: list[str] = Field(min_length=1)


class Cell(ContractModel):
    value: str | None
    status: Status = Status.ok
    note: str | None = None


class TableRow(ContractModel):
    path: list[str] = Field(default_factory=list)
    cells: list[Cell]


class TableContent(ContractModel):
    caption: str | None = None
    columns: list[ColumnDef]
    rows: list[TableRow]
    footnotes: list[str] = Field(default_factory=list)
    continues_from_previous: bool = False
    continues_on_next: bool = False


class TableItem(_ModelItemBase):
    type: Literal["table"]
    content: TableContent


class Axis(ContractModel):
    label: str | None = None
    unit: str | None = None


class ChartPoint(ContractModel):
    label: str | None = None
    x: str | None = None
    value: str | None
    unit: str | None = None
    is_estimate: bool
    status: Status = Status.ok
    note: str | None = None


class Series(ContractModel):
    name: str | None = None
    points: list[ChartPoint]


class ChartContent(ContractModel):
    title: str | None = None
    chart_type: Literal["bar", "line", "pie", "scatter", "area", "other"]
    x_axis: Axis | None = None
    y_axis: Axis | None = None
    legend: list[str] = Field(default_factory=list)
    series: list[Series]


class ChartItem(_ModelItemBase):
    type: Literal["chart"]
    content: ChartContent


class FormFieldContent(ContractModel):
    label: str
    field_type: Literal["text", "checkbox", "radio", "amount", "date", "other"]
    value: str | None = None
    checked: bool | None = None
    line_ref: str | None = None
    unit: str | None = None


class FormFieldItem(_ModelItemBase):
    type: Literal["form_field"]
    content: FormFieldContent


ModelItem: TypeAlias = Annotated[
    ProseItem | TableItem | ChartItem | FormFieldItem,
    Field(discriminator="type"),
]


class ModelPageOutput(ContractModel):
    """One page's structured output from a model; backend fields are ignored."""

    page: int = Field(ge=1)
    items: list[ModelItem]
    page_notes: str | None = None


class Evidence(ModelEvidence):
    verified: bool | None = None
    match_score: float | None = Field(default=None, ge=0, le=1)


class Finding(ContractModel):
    code: str
    severity: Literal["info", "warning"]
    message: str
    page: int | None = Field(default=None, ge=1)
    item_id: str | None = None


class Issue(ContractModel):
    code: str
    scope: Literal["run", "page"]
    page: int | None = Field(default=None, ge=1)
    item_id: str | None = None
    message: str


class Item(ContractModel):
    id: str
    type: ItemType
    status: Status
    is_estimate: bool
    content: ProseContent | TableContent | ChartContent | FormFieldContent
    evidence: list[Evidence]
    notes: str | None
    findings: list[Finding] = Field(default_factory=list)
    pages: list[Annotated[int, Field(ge=1)]] = Field(min_length=1)
    merged_from: list[str] | None = None


class PageMetrics(ContractModel):
    latency_s: float | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    attempts: int = Field(ge=0)
    retries: int = Field(ge=0)
    repaired: bool
    cached: bool


class PageExtraction(ContractModel):
    page: int = Field(ge=1)
    status: Literal["done", "failed"]
    items: list[Item]
    page_notes: str | None
    error: Issue | None
    metrics: PageMetrics


class DocumentExtraction(ContractModel):
    items: list[Item]
    pages: list[PageExtraction]
    findings: list[Finding]


class TextBlock(ContractModel):
    id: str
    text: str
    bbox: BBox


class Page(ContractModel):
    number: int = Field(ge=1)
    width_px: int = Field(ge=1)
    height_px: int = Field(ge=1)
    image: bytes
    image_mime: str
    text_blocks: list[TextBlock] | None


class LoadedDocument(ContractModel):
    filename: str
    source_kind: Literal["pdf", "image"]
    pages: list[Page] = Field(min_length=1)


class ProviderCapabilities(ContractModel):
    vision: bool
    structured_output: bool
    max_image_pixels: int | None = Field(default=None, ge=1)
    max_input_tokens: int | None = Field(default=None, ge=1)
    reports_usage: bool


class ImagePart(ContractModel):
    data: bytes
    mime: str = Field(min_length=1)


class GenerationRequest(ContractModel):
    system_prompt: str
    user_prompt: str
    images: list[ImagePart] = Field(default_factory=list)
    response_schema: dict[str, object] | None = None


class Usage(ContractModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class GenerationResponse(ContractModel):
    text: str
    usage: Usage | None = None
    model: str
    latency_s: float = Field(ge=0)
    attempts: int = Field(default=1, ge=1)
    retries: int = Field(default=0, ge=0)
    cached: bool = False


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    completed_with_warnings = "completed_with_warnings"
    failed = "failed"


class PageProgress(ContractModel):
    page: int = Field(ge=1)
    status: Literal["pending", "processing", "done", "failed"]
    cached: bool = False


class RunProgress(ContractModel):
    stage: Literal["loading", "extracting", "aggregating", "validating", "rendering"]
    pages_total: int = Field(ge=0)
    pages_done: int = Field(ge=0)
    pages_failed: int = Field(ge=0)
    pages: list[PageProgress]


class ValidationSummary(ContractModel):
    schema_ok: bool
    all_pages_processed: bool
    items_without_evidence: int = Field(ge=0)
    evidence_unverifiable: int = Field(ge=0)
    markdown_format_ok: bool


class UsageSummary(ContractModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    available: bool


class RunMetadata(ContractModel):
    provider: str
    model: str
    prompt_version: str
    started_at: datetime
    duration_s: float = Field(ge=0)
    usage: UsageSummary
    retries: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    pages_total: int = Field(ge=0)
    pages_processed: int = Field(ge=0)
    validation: ValidationSummary


class Reference(ContractModel):
    id: str
    item_id: str
    page: int = Field(ge=1)
    bbox: BBox | None = None
    excerpt: str
    verified: bool | None
    item_status: Status
    is_estimate: bool


class RunSummary(ContractModel):
    items_total: int = Field(ge=0)
    items_by_status: dict[Status, int]


class RunResult(ContractModel):
    markdown: str
    references: list[Reference]
    summary: RunSummary


class PipelineOutput(ContractModel):
    document: DocumentExtraction
    result: RunResult
    errors: list[Issue]
    warnings: list[Issue]


class RunState(ContractModel):
    run_id: str
    status: RunStatus
    created_at: datetime
    finished_at: datetime | None = None
    progress: RunProgress
    result: RunResult | None
    metadata: RunMetadata | None
    errors: list[Issue]
    warnings: list[Issue]


class HTTPError(ContractModel):
    code: str
    message: str
    details: dict[str, object] | None = None


class HTTPErrorResponse(ContractModel):
    error: HTTPError


class RenderOptions(ContractModel):
    section_order: list[ItemType] | None = None


class DomainProfile(ContractModel):
    id: str = Field(pattern=r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
    name: str
    description: str
    default_instructions: str
    hints: str | None = None
    render: RenderOptions | None = None
