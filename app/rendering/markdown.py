"""Render validated extraction items into Markdown with structured references."""

from __future__ import annotations

from collections import Counter

from app.core.schemas import (
    ChartContent,
    DocumentExtraction,
    FormFieldContent,
    Item,
    Reference,
    RunResult,
    RunSummary,
    Status,
    TableContent,
)


class MarkdownRenderer:
    """Render a document extraction without trusting model-provided Markdown."""

    def render(self, document: DocumentExtraction) -> RunResult:
        lines = ["# Extraction results", ""]
        references: list[Reference] = []
        item_counts: Counter[Status] = Counter()

        for item in document.items:
            item_counts[item.status] += 1
            item_reference_ids = self._references_for_item(item, references)
            suffix = self._status_label(item.status)
            markers = " ".join(f"[{reference_id}]" for reference_id in item_reference_ids)
            if markers:
                suffix = f"{suffix} {markers}".strip()
            self._render_item(lines, item, suffix)

        if not document.items:
            lines.append("No items to display.")

        lines.extend(["", "## Sources", ""])
        if references:
            for reference in references:
                excerpt = self._escape_inline(reference.excerpt)
                verified = self._verification_label(
                    reference.verified,
                    reference.verification_source,
                )
                lines.append(f"- [{reference.id}] Page {reference.page} — {verified}: “{excerpt}”")
        else:
            lines.append("No source references.")

        return RunResult(
            markdown="\n".join(lines).rstrip() + "\n",
            references=references,
            summary=RunSummary(
                items_total=len(document.items),
                items_by_status={status: item_counts.get(status, 0) for status in Status},
            ),
        )

    def _references_for_item(self, item: Item, references: list[Reference]) -> list[str]:
        reference_ids = []
        for evidence in item.evidence:
            reference_id = f"S{len(references) + 1}"
            references.append(
                Reference(
                    id=reference_id,
                    item_id=item.id,
                    page=evidence.page,
                    bbox=evidence.bbox,
                    excerpt=evidence.excerpt,
                    verified=evidence.verified,
                    verification_source=evidence.verification_source,
                    item_status=item.status,
                    is_estimate=item.is_estimate,
                )
            )
            reference_ids.append(reference_id)
        return reference_ids

    def _render_item(self, lines: list[str], item: Item, suffix: str) -> None:
        if item.type == "prose":
            content = item.content
            title = content.heading if hasattr(content, "heading") else None
            if title:
                lines.extend([f"## {self._escape_inline(title)}", ""])
            lines.extend([self._escape_block(content.text), suffix, ""])
            return

        if item.type == "table":
            content = item.content
            assert isinstance(content, TableContent)
            if content.caption:
                lines.extend([f"## {self._escape_inline(content.caption)}", ""])
            path_separator = " \u203a "
            max_cells = max((len(row.cells) for row in content.rows), default=0)
            extra_columns = range(1, max_cells - len(content.columns) + 1)
            columns = [
                "Row",
                *(
                    self._escape_inline(path_separator.join(column.path))
                    for column in content.columns
                ),
                *(f"Additional column {index}" for index in extra_columns),
            ]
            lines.append("| " + " | ".join(columns) + " |")
            lines.append("| " + " | ".join("---" for _ in columns) + " |")
            for row in content.rows:
                values = [
                    self._escape_inline(path_separator.join(row.path)),
                    *(self._cell_text(cell.value, cell.status, cell.note) for cell in row.cells),
                ]
                if len(values) < len(columns):
                    values.extend("(no data)" for _ in range(len(columns) - len(values)))
                lines.append("| " + " | ".join(values) + " |")
            if content.footnotes:
                lines.extend(
                    ["", *(f"- {self._escape_inline(note)}" for note in content.footnotes)]
                )
            lines.extend(["", suffix, ""])
            return

        if item.type == "chart":
            content = item.content
            assert isinstance(content, ChartContent)
            lines.append(f"## {self._escape_inline(content.title or 'Chart')}")
            lines.append("")
            for series in content.series:
                if series.name:
                    lines.append(f"**{self._escape_inline(series.name)}**")
                for point in series.points:
                    label = self._escape_inline(point.label or point.x or "Value")
                    unit = point.unit or (content.y_axis.unit if content.y_axis else None)
                    value = self._escape_inline(point.value or self._status_label(point.status))
                    estimate = " (estimated)" if point.is_estimate else ""
                    unit_text = f" {self._escape_inline(unit)}" if unit else ""
                    status = (
                        f" {self._status_label(point.status)}" if point.status != Status.ok else ""
                    )
                    lines.append(f"- {label}: {value}{unit_text}{estimate}{status}")
            lines.extend(["", suffix, ""])
            return

        content = item.content
        assert isinstance(content, FormFieldContent)
        if content.field_type in {"checkbox", "radio"}:
            value = (
                "[x] checked"
                if content.checked is True
                else ("[ ] empty" if content.checked is False else "[?] unclear")
            )
        elif content.value is None:
            value = self._status_label(item.status)
        else:
            value = self._escape_inline(content.value)
        unit = f" {self._escape_inline(content.unit)}" if content.unit else ""
        lines.extend(
            [
                f"**{self._escape_inline(content.label)}:** {value}{unit}",
                suffix,
                "",
            ]
        )

    @staticmethod
    def _status_label(status: Status) -> str:
        labels = {
            Status.ok: "",
            Status.uncertain: "[UNCERTAIN]",
            Status.unreadable: "[UNREADABLE]",
            Status.missing: "[MISSING]",
        }
        return labels[status]

    @staticmethod
    def _verification_label(
        verified: bool | None,
        verification_source: str | None,
    ) -> str:
        if verified is True:
            if verification_source == "ocr_text":
                return "matched OCR text (OCR may contain errors)"
            return "verified"
        if verified is False:
            if verification_source == "ocr_text":
                return "not found in OCR text"
            return "not found in text layer"
        return "not automatically verifiable"

    @classmethod
    def _cell_text(cls, value: str | None, status: Status, note: str | None) -> str:
        if value is None:
            rendered = cls._status_label(status) or "(no data)"
        else:
            rendered = cls._escape_inline(value)
            if status != Status.ok:
                rendered += f" {cls._status_label(status)}"
        if note:
            rendered += f" — {cls._escape_inline(note)}"
        return rendered

    @staticmethod
    def _escape_inline(value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("*", "\\*")
            .replace("_", "\\_")
            .replace("{", "\\{")
            .replace("}", "\\}")
            .replace("|", "\\|")
            .replace("[", "\\[")
            .replace("]", "\\]")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .replace("#", "\\#")
            .replace("+", "\\+")
            .replace("-", "\\-")
            .replace(".", "\\.")
            .replace("!", "\\!")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @classmethod
    def _escape_block(cls, value: str) -> str:
        return "\n".join(cls._escape_inline(line) for line in value.splitlines())
