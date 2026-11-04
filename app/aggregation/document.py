"""Conservative document aggregation with deterministic item identifiers."""

from app.core.schemas import DocumentExtraction, Finding, PageExtraction


class DocumentAggregator:
    """Preserve page output order and do not merge cross-page tables by default."""

    def aggregate(self, pages: list[PageExtraction]) -> DocumentExtraction:
        document_items = []
        document_findings: list[Finding] = []
        page_summaries = []

        for page in pages:
            for item in page.items:
                document_items.append(
                    item.model_copy(
                        update={"id": f"item-{len(document_items) + 1:04d}"},
                    )
                )
                document_findings.extend(item.findings)
            page_summaries.append(page.model_copy(update={"items": []}))

        return DocumentExtraction(
            items=document_items,
            pages=page_summaries,
            findings=document_findings,
        )
