# OpenRouter Extraction Evaluation

**Test date:** 2026-11-04  
**Input:** [`2608.16753v1.pdf`](../test_file/2608.16753v1.pdf)  
**Provider/model:** OpenRouter — `google/gemini-3-flash-preview`  
**Domain:** Research paper  
**Vision / structured output:** Enabled / Enabled  
**Runs:** `aa93d8a0-d82c-4336-9819-c4d97ab3b718` and `69abc3b5-db79-4d4c-9797-c31984f6829c`

## Executive Summary

Both real-provider runs processed all **13 of 13 PDF pages** without a failed page. Both returned `completed_with_warnings`: the output passed schema and Markdown checks, but some evidence excerpts did not match the PDF text layer, and the second run also had two items without evidence.

Two different extraction instructions were used without changing application code. Eight manually checked source facts, including the paper title, author, central question, and four figure captions, were present in both outputs and cited to the correct source pages. This small check is not a full-document accuracy score.

Only the specified PDF was present in `test_file/`. No PNG/JPG sample was available, so this run does not satisfy the requirement to evaluate both supplied files. The paper contains prose and conceptual figures, but no table captions, numerical charts, form fields, or checkboxes to evaluate.

Automated application checks recorded during the recent code verification passed: **131 Python tests**, **5 UI tests**, Ruff checks, and the CSS build. These checks cover implementation behavior but do not replace a live-model evaluation of a missing image sample.

## Input and Run Configuration

| Property | Value |
|---|---|
| PDF size | 3,702,471 bytes |
| PDF pages | 13 |
| Locally extracted text | Present on all pages |
| Embedded image objects | One on page 7 |
| PDF figure captions | Figures 1–4, on pages 4, 5, 7, and 9 |
| Table captions | None found |
| Image/form sample | Not present in `test_file/` |
| Provider selection | OpenRouter selected for each run; the application's default provider remained unchanged |

### Instruction 1 — Full-page extraction

> Extract all readable content from every page of this research paper: prose, equations, tables, figures, captions, and references. Preserve the source language, wording, symbols, values, and units. Keep table headers and rows explicit. For charts, include titles, axes, series, labels, units, and values; mark visually estimated values as estimates. Add a concise verbatim supporting excerpt and page number for each extracted item. Mark missing, unreadable, or uncertain content explicitly and do not guess. Do not omit any page.

### Instruction 2 — Focused argument extraction

> Create a focused, evidence-backed extraction of the paper's central argument. Across all pages, identify its main question, assumptions, key claims, supporting examples, proposed community response, and conclusion. Preserve the author's meaning and original wording for important statements. Extract the full text and hierarchy of each figure caption and any table; describe visible diagram labels and relationships without inventing values. Attach a short verbatim excerpt and source page to every item. Flag uncertain, missing, or unreadable information; do not infer. Include relevant material from the references only when it supports a claim discussed in the paper.

## Operational Results

| Run | Status | Pages processed | Failed pages | Duration | Input / output tokens | Retries | Items | References | Warnings |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Full-page extraction | `completed_with_warnings` | 13/13 | 0 | 243.62 s | 149,648 / 25,942 | 2 | 84 | 89 | 13 |
| Focused argument | `completed_with_warnings` | 13/13 | 0 | 106.71 s | 149,843 / 21,411 | 0 | 65 | 69 | 19 |

Both runs reported `schema_ok=true`, `all_pages_processed=true`, and `markdown_format_ok=true`. The first run had 13 `evidence_not_found` warnings. The second had 17 `evidence_not_found` and 2 `item_without_evidence` warnings.

| Evidence measure | Full-page extraction | Focused argument |
|---|---:|---:|
| References verified against the PDF text layer | 76/89 (85.4%) | 52/69 (75.4%) |
| References not found in the text layer | 13/89 (14.6%) | 17/69 (24.6%) |
| Items without evidence | 0/84 | 2/65 |
| Pages with an extraction failure | 0/13 | 0/13 |

The application does not report provider billing or monetary cost in run metadata; cost is therefore **not measured** here.

## Manually Checked Source Answers

The following eight facts were checked against the PDF text and figure captions. Both runs contained each fact and the corresponding source references pointed to the expected page.

| Manually checked fact | Source page | Full-page run | Focused run |
|---|---:|---|---|
| Title: “MATHEMATICS IN THE AGE OF AI” | 1 | Correct; reference to p. 1 | Correct; reference to p. 1 |
| Author: Terence Tao | 1 | Correct; reference to p. 1 | Correct; reference to p. 1 |
| Abstract identifies a public lecture at the 2026 International Congress of Mathematicians | 1 | Correct; reference to p. 1 | Correct; reference to p. 1 |
| Community Response Question 2.1 is included | 2 | Correct; reference to p. 2 | Correct; reference to p. 2 |
| Figure 1 caption about one mathematical goal serving as a proxy for others | 4 | Correct; reference to p. 4 | Correct; reference to p. 4 |
| Figure 2 caption about excessive optimization causing goals to diverge | 5 | Correct; reference to p. 5 | Correct; reference to p. 5 |
| Figure 3 caption identifies a page from a 1991 Bourgain paper | 7 | Correct; reference to p. 7 | Correct; reference to p. 7 |
| Figure 4 is identified as the problem-solving pipeline | 9 | Correct; reference to p. 9 | Correct; reference to p. 9 |

**Sample result:** 8/8 checked facts passed per run (16/16 repeated checks). This is a deliberately small, manually inspected sample, not a statistically representative accuracy estimate or a measure of recall/completeness.

## Required-Scope Assessment

| Requirement | Result for this evaluation |
|---|---|
| PDF input and all PDF pages | **Passed for this file:** 13 pages loaded and processed in both runs. |
| PNG/JPG input and both provided samples | **Not fully evaluated:** the application has PNG/JPG loader tests, but no image sample was present in `test_file/`; no live vision run on a supplied image was possible. |
| Prose and instructions | **Passed on the checked sample:** two distinct user instructions produced different item counts and both included the checked facts. |
| Tables and table hierarchy | **Not exercised:** the source paper has no table captions or table data identified in this inspection. |
| Charts and chart estimates | **Not exercised:** the paper has conceptual figures, not a numeric chart with values to verify. |
| Form fields and checkboxes | **Not applicable to this input:** no form or checkbox content is present. |
| Figures and source references | **Partially passed:** four captions/diagrams were represented and checked references pointed to the correct pages. One embedded image is on page 7. |
| Uncertainty and missing evidence | **Warnings surfaced:** nonmatching excerpts were marked and lowered in verification; the focused run also reported two items with no evidence. |
| Reliability and formatting | **Passed by run metadata:** schema, all-page processing, and Markdown checks were true; no page-level provider failures occurred. |
| Model independence | **OpenRouter live path exercised:** the selected provider used the shared application pipeline, with vision and structured output enabled. |
| Operational measurements | **Recorded:** duration, page coverage, token usage, retries, item/reference counts, and validation warnings are listed above. Monetary cost was unavailable. |

## Failures, Limitations, and Design Trade-offs

- Both runs completed with warnings, not clean `completed` status. A successful schema response does not imply that every supporting excerpt was verified.
- The evidence validator checks normalized excerpts against individual PDF text blocks. Line wrapping, image-only text, or differences between model excerpts and source text can produce false negatives. The 13 and 17 unmatched excerpts require review; they are not automatically proof that the extracted claim is false.
- Page 7 contains an embedded image. Text extracted from that visual region cannot necessarily be verified against the page's ordinary text layer.
- This academic essay is not a suitable test of tables, numeric charts, form fields, or checkboxes. Their absence must not be reported as successful extraction coverage.
- Only one sample was present. The required second PNG/JPG sample and its live-provider evaluation remain outstanding.
- The eight manually checked facts establish a small precision spot-check only. They do not measure exhaustive completeness, omitted content, table-cell accuracy, chart-value accuracy, or overall recall.
- The two runs consumed 299,491 input and 47,353 output tokens in total. The focused prompt was faster and emitted fewer items, but a smaller output is not evidence that it is more accurate or complete.
- At the time of these runs, page-cache and cross-page table-aggregation options were accepted but inert. The UI controls have since been removed, and the API now rejects legacy requests that enable either option. This paper has no tables, so table aggregation was not material to this result.
- The system favors structured, evidence-linked output and explicit uncertainty over silently accepting every model claim. This improves auditability but can mark legitimate content uncertain when source-text matching is strict.

## Conclusion

For the specified 13-page PDF, OpenRouter with `google/gemini-3-flash-preview` processed every page in both instruction variants and passed the application's schema and Markdown checks. The manually checked sample was correct with page references, while the evidence warnings and the missing second sample prevent a claim that the full required evaluation is complete.

To complete the brief, provide the missing PNG/JPG sample and evaluate it with a vision-enabled provider. Review unmatched evidence and manually check a broader set of source answers before making an overall accuracy claim.
