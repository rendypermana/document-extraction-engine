"""Deterministic evidence and semantic validation for extracted page items."""

from __future__ import annotations

from math import isfinite

from app.core.schemas import (
    ChartItem,
    Evidence,
    Finding,
    FormFieldItem,
    Item,
    ItemType,
    ModelPageOutput,
    Page,
    PageExtraction,
    PageMetrics,
    Status,
    TableItem,
)

BBOX_EPSILON = 0.001


class PageEvidenceValidator:
    """Add evidence verification and soft findings without promoting status."""

    def validate(
        self,
        page: Page,
        output: ModelPageOutput,
        metrics: PageMetrics,
    ) -> PageExtraction:
        if output.page != page.number:
            raise ValueError(
                "The page number in the model response does not match the loaded page."
            )

        items: list[Item] = []
        for item_index, model_item in enumerate(output.items, start=1):
            item_id = f"p{page.number}-i{item_index}"
            findings: list[Finding] = []
            status = model_item.status
            evidence_items: list[Evidence] = []

            if not model_item.evidence:
                status = self._lower_status(status)
                findings.append(
                    self._finding(
                        "item_without_evidence",
                        "The extracted item has no supporting evidence.",
                        page.number,
                        item_id,
                    )
                )

            for model_evidence in model_item.evidence:
                bbox = (
                    self._normalize_bbox(model_evidence.bbox)
                    if model_evidence.bbox is not None
                    else None
                )
                if model_evidence.bbox is not None and bbox is None:
                    status = self._lower_status(status)
                    findings.append(
                        self._finding(
                            "bbox_out_of_bounds",
                            "The evidence bounding box is outside the normalized page bounds.",
                            page.number,
                            item_id,
                        )
                    )

                if model_evidence.page != page.number:
                    verified: bool | None = False
                    status = self._lower_status(status)
                    findings.append(
                        self._finding(
                            "evidence_page_not_found",
                            "The evidence refers to a different page than the extracted item.",
                            page.number,
                            item_id,
                        )
                    )
                elif page.text_blocks is None or not page.text_blocks:
                    verified = None
                    findings.append(
                        self._finding(
                            "evidence_not_verifiable",
                            (
                                "This page has no text layer; the evidence cannot be "
                                "verified automatically."
                            ),
                            page.number,
                            item_id,
                        )
                    )
                else:
                    excerpt = self._normalize_text(model_evidence.excerpt)
                    verified = bool(
                        excerpt
                        and any(
                            excerpt in self._normalize_text(block.text)
                            for block in page.text_blocks
                        )
                    )
                    if not verified:
                        status = self._lower_status(status)
                        findings.append(
                            self._finding(
                                "evidence_not_found",
                                "The evidence excerpt was not found in the page text layer.",
                                page.number,
                                item_id,
                            )
                        )

                evidence_items.append(
                    Evidence(
                        page=model_evidence.page,
                        excerpt=model_evidence.excerpt,
                        bbox=bbox,
                        verified=verified,
                        match_score=1.0 if verified else (0.0 if verified is False else None),
                    )
                )

            content = model_item.content
            is_estimate = model_item.is_estimate
            if isinstance(model_item, TableItem):
                if any(len(row.cells) != len(content.columns) for row in content.rows):
                    status = self._lower_status(status)
                    findings.append(
                        self._finding(
                            "table_shape_mismatch",
                            "The number of cells in a table row does not match the "
                            "number of columns.",
                            page.number,
                            item_id,
                        )
                    )
                rows = []
                for row in content.rows:
                    cells = []
                    for cell in row.cells:
                        if cell.value is None and cell.status == Status.ok:
                            cell = cell.model_copy(update={"status": Status.uncertain})
                        if cell.status != Status.ok:
                            status = self._lower_status(status)
                            findings.append(
                                self._finding(
                                    "item_part_not_ok",
                                    "The table cell is not marked as confidently readable.",
                                    page.number,
                                    item_id,
                                )
                            )
                        cells.append(cell)
                    rows.append(row.model_copy(update={"cells": cells}))
                content = content.model_copy(update={"rows": rows})
            elif isinstance(model_item, ChartItem):
                point_estimated = any(
                    point.is_estimate for series in content.series for point in series.points
                )
                if point_estimated != model_item.is_estimate:
                    findings.append(
                        self._finding(
                            "chart_estimate_flag_mismatch",
                            "The item's estimate status was adjusted to match the chart points.",
                            page.number,
                            item_id,
                        )
                    )
                is_estimate = model_item.is_estimate or point_estimated
                for series in content.series:
                    if any(point.status != Status.ok for point in series.points):
                        status = self._lower_status(status)
                        findings.append(
                            self._finding(
                                "item_part_not_ok",
                                "The chart point is not marked as confidently readable.",
                                page.number,
                                item_id,
                            )
                        )
            elif isinstance(model_item, FormFieldItem):
                if (
                    content.field_type in {"checkbox", "radio"}
                    and content.checked is None
                    and status == Status.ok
                ):
                    status = self._lower_status(status)
                    findings.append(
                        self._finding(
                            "checkbox_state_unclear",
                            "The checkbox or radio button state is unclear.",
                            page.number,
                            item_id,
                        )
                    )

            items.append(
                Item(
                    id=item_id,
                    type=ItemType(model_item.type),
                    status=status,
                    is_estimate=is_estimate,
                    content=content,
                    evidence=evidence_items,
                    notes=model_item.notes,
                    findings=findings,
                    pages=[page.number],
                    merged_from=None,
                )
            )

        return PageExtraction(
            page=page.number,
            status="done",
            items=items,
            page_notes=output.page_notes,
            error=None,
            metrics=metrics,
        )

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.split()).casefold()

    @staticmethod
    def _lower_status(status: Status) -> Status:
        return Status.uncertain if status == Status.ok else status

    @staticmethod
    def _valid_bbox(bbox: tuple[float, float, float, float]) -> bool:
        x0, y0, x1, y1 = bbox
        return all(isfinite(value) for value in bbox) and 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1

    @classmethod
    def _normalize_bbox(
        cls,
        bbox: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float] | None:
        if not all(isfinite(value) for value in bbox):
            return None
        if any(value < -BBOX_EPSILON or value > 1 + BBOX_EPSILON for value in bbox):
            return None

        normalized = tuple(max(0.0, min(1.0, value)) for value in bbox)
        if not cls._valid_bbox(normalized):
            return None
        return normalized

    @staticmethod
    def _finding(code: str, message: str, page: int, item_id: str) -> Finding:
        return Finding(
            code=code,
            severity="warning",
            message=message,
            page=page,
            item_id=item_id,
        )
