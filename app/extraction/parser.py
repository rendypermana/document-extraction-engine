"""Strict JSON parser for structured model page responses."""

from __future__ import annotations

import json
from json import JSONDecodeError

from pydantic import ValidationError

from app.core.errors import ProviderInvalidResponseError
from app.core.schemas import ModelPageOutput


class JsonResponseParser:
    """Parse one JSON object and validate it against the current Pydantic model."""

    def parse(self, response_text: str) -> ModelPageOutput:
        try:
            payload = json.loads(response_text)
            if not isinstance(payload, dict):
                raise ProviderInvalidResponseError("The model response must be a JSON object.")
            return ModelPageOutput.model_validate(payload)
        except JSONDecodeError as exc:
            raise ProviderInvalidResponseError(
                f"The model response is not valid JSON (line {exc.lineno}, column {exc.colno})."
            ) from exc
        except ValidationError as exc:
            locations = ", ".join(
                ".".join(str(part) for part in error["loc"])
                for error in exc.errors(include_input=False)
            )
            detail = f" Fields to check: {locations}." if locations else ""
            raise ProviderInvalidResponseError(
                f"The model response does not match the required schema.{detail}"
            ) from exc
