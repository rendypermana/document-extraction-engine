"""HTTP response contracts for the FastAPI application."""

from pydantic import BaseModel

from app.core.schemas import ProviderCapabilities, RunStatus


class ProviderInfo(BaseModel):
    id: str
    label: str
    model: str
    available: bool
    unavailable_reason: str | None
    capabilities: ProviderCapabilities


class ProviderList(BaseModel):
    default: str
    providers: list[ProviderInfo]


class DomainInfo(BaseModel):
    id: str
    name: str
    description: str
    default_instructions: str


class DomainList(BaseModel):
    domains: list[DomainInfo]


class RunCreated(BaseModel):
    run_id: str
    status: RunStatus
    status_url: str
