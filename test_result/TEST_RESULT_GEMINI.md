# Gemini Evaluation Report

**Test date:** November 5, 2026  
**Input:** [`2608.16753v1.pdf`](../test_file/2608.16753v1.pdf)  
**Provider/model:** Gemini — `gemini-3.5-flash`  
**Domain:** Research paper  
**Vision / structured output:** Enabled / Enabled  
**Runs:** `b1f38877-5ea1-4f78-a89f-35b97e31d588` and `c1b2c6d7-0aee-45ed-8abc-28111d50b2da`

## Executive Summary

Two live runs were submitted through the application with different extraction instructions. **Neither run extracted a page:** both processed 0/13 pages and ended with `completed_with_warnings`. All 13 page requests in each run failed with Gemini rate-limit errors. Each run recorded 39 retries and took about 3 minutes.

The application reported valid schema and Markdown structure, but `all_pages_processed=false`; these structural checks do not mean the model extracted any content. Both runs returned zero items and zero source references, so extraction accuracy could not be scored. Manually checked facts in the PDF source are listed below, but there are no model answers to compare against them.

Only the specified PDF was present in `test_file/`; no PNG/JPG sample was available. Therefore, the required live evaluation of both file samples was not completed. Even though Gemini was configured with vision, the failed runs provide no evidence about image extraction, figures, tables, forms, or checkboxes.

## Input and Configuration

| Property | Value |
|---|---|
| PDF size | 3,702,471 bytes |
| PDF pages | 13 |
| Local text layer | Present on all 13 pages |
| Embedded image objects | One on page 7 |
| Figure captions | Figures 1–4, on pages 4, 5, 7, and 9 |
| Table captions | None found in the source-text inspection |
| PNG/JPG sample | Not present in `test_file/` |
| Model vision | Enabled |
| Structured output | Enabled |
| Provider selection | `gemini` explicitly selected for both runs; `.env` default was not changed |

### Instruction 1 — Full-content extraction

> Extract all readable content from every page of this research paper: prose, equations, tables, figures, captions, and references. Preserve the source language, wording, symbols, values, and units. Keep table headers and rows explicit. For charts, include titles, axes, series, labels, units, and values; mark visually estimated values as estimates. Add a concise verbatim supporting excerpt and page number for each extracted item. Mark missing, unreadable, or uncertain content explicitly and do not guess. Do not omit any page.

### Instruction 2 — Focused argument

> Create a focused, evidence-backed extraction of this paper's central question, assumptions, key claims about AI and mathematical research goals, recommendations to the mathematical community, and conclusion. Read across every page. Add a concise verbatim supporting excerpt and exact page number for each extracted claim. Preserve important source wording and mark uncertain or missing content rather than guessing. This run uses the Gemini vision-capable provider, but only report visual figure or chart content when you can identify it clearly; label estimated chart values explicitly. Do not invent tables, values, fields, or checkbox states.

## Operational Results

| Run | Run ID | Status | Pages processed | Failed page requests | Duration | Items | References | Retries | Errors |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Full-content extraction | `b1f38877-5ea1-4f78-a89f-35b97e31d588` | `completed_with_warnings` | 0/13 | 13 | 189.04 s | 0 | 0 | 39 | 13 |
| Focused argument | `c1b2c6d7-0aee-45ed-8abc-28111d50b2da` | `completed_with_warnings` | 0/13 | 13 | 187.30 s | 0 | 0 | 39 | 13 |

| Validation metric | Full-content extraction | Focused argument |
|---|---:|---:|
| `schema_ok` | true | true |
| `markdown_format_ok` | true | true |
| `all_pages_processed` | false | false |
| `items_without_evidence` | 0 | 0 |
| Page errors | 13 | 13 |
| Error type | `provider_rate_limit` on all pages | `provider_rate_limit` on all pages |
| Token usage available | No | No |

The application retried failed requests three times per page, for 39 retries per run. No token usage or provider billing cost was available in the run metadata. A zero item count and unavailable usage are reported as observed; no extraction quality or cost value is inferred from them.

## Quality Metrics and Manual Source Checks

The selected metrics distinguish whether the application processed the document from whether extracted facts are correct:

- **Page coverage** = successfully processed pages ÷ total pages. This tests the explicit all-pages requirement. Both runs scored **0/13 (0%)**.
- **Successful extraction volume** = items and references returned. Both runs returned **0 items and 0 references**. This demonstrates extraction failure, not a 0% factual accuracy score.
- **Evidence match rate** = verified source references ÷ all returned references. It is **not applicable** because no references were returned.
- **Manual source-answer checks** compare model-extracted answers with original PDF text, independently of model confidence. The source facts below were confirmed manually, but no model answers were produced, so none can be scored as correct or incorrect.
- **Operational performance** is measured with duration, page failures, retry count, and reported token usage. Duration and retries are available; tokens and monetary cost are not.

| Manually checked source fact | Source page | Source check | Model-answer check |
|---|---:|---|---|
| Title: “MATHEMATICS IN THE AGE OF AI” | 1 | Present in PDF text layer | Not scorable; no extracted item |
| Author: Terence Tao | 1 | Present in PDF text layer | Not scorable; no extracted item |
| Abstract says the essay is based on a public lecture at the 2026 International Congress of Mathematicians | 1 | Present in PDF text layer | Not scorable; no extracted item |
| Question 2.1 is labeled “Community Response Question” | 2 | Present in PDF text layer | Not scorable; no extracted item |
| Figure 1 caption says a mathematical goal historically served as a proxy for others | 4 | Present in PDF text layer | Not scorable; no extracted item |

The manual inspection verifies that the ground-truth answers exist in the source; it does not validate Gemini extraction. The output supplies no evidence with which to calculate precision, recall, or answer accuracy.

## Required-Scope Assessment

| Requirement | Result for this Gemini evaluation |
|---|---|
| PDF input and all pages | The PDF loaded as 13 pages, but 0/13 pages were processed successfully. **Not met.** |
| PNG/JPG input and both sample files | No image sample was present in `test_file/`; no live image run was possible. **Not evaluated.** |
| Prose | No prose was returned. **Not demonstrated by these live runs.** |
| Tables and explicit hierarchy | No table output was returned. The inspected PDF text has no table captions. **Not demonstrated.** |
| Charts, labels, values, units, and estimates | No chart output was returned. The paper has conceptual figures, not a numerical chart suitable for validating chart-value extraction. **Not demonstrated.** |
| Form fields and checkboxes | No output or form sample was available. **Not evaluated.** |
| Two instructions without code changes | Two distinct instructions were submitted through the same application and model configuration. **The instruction workflow was exercised**, but neither run produced extraction output. |
| Page references and supporting excerpts | No references or excerpts were returned. **Not met by these runs.** |
| Missing or uncertain values | No model output was available to assess uncertainty handling. **Not evaluated.** |
| Reliability and provider failure reporting | All 13 page failures per run were reported as `provider_rate_limit`. Schema/Markdown checks were true, while `all_pages_processed` was false. **Failure reporting observed; extraction reliability not achieved.** |
| Model independence | The Gemini adapter was exercised through the application's shared extraction pipeline. This run provides no comparative model-quality result. |
| Operational measurements | Duration, failed pages, and retries were available. Token usage and billing cost were unavailable. |

## Architecture and Design Trade-offs

- Provider adapters implement the shared provider interface and are selected through configuration/registry. A new provider requires an adapter, registry/configuration wiring, capability declarations, and adapter tests.
- Domain profiles allow extraction instructions and hints to be extended independently of provider adapters.
- File loaders use a shared contract and registry; a new format can be added by normalizing it into the application's page representation and adding loader tests.
- Provider capabilities such as vision and structured output are explicit. Gemini reported both enabled for this test, but capability flags do not override account quotas or guarantee a successful generation request.
- Provider logic is separated from parsing, evidence validation, aggregation, and Markdown rendering. This separation lets the application record provider failures independently from result validation.
- The renderer and schema checks can produce a structurally valid empty result even when every page failed. Therefore, the `completed_with_warnings` status and `all_pages_processed` field must be considered together; passing Markdown/schema checks alone is not evidence of successful extraction.
- The system favors structured output and auditable source references. In this evaluation that trade-off could not be assessed for quality because no provider response succeeded.
- At the time of these runs, page-cache and cross-page table-merging options were accepted but inert. The UI controls have since been removed, and the API now rejects legacy requests that enable either option.

## Failures, Limitations, and Conclusion

The observed failure was consistent across both instructions: Gemini rate-limited every page request, even after three retries per page. The application returned page-level errors rather than presenting the document as fully processed. This consumed about 189 seconds per run without producing any items. The test did not determine whether the rate limit was due to request rate, account quota, billing, or model availability; the provider response exposed only a rate-limit error.

This evaluation cannot be used to claim Gemini `gemini-3.5-flash` extraction accuracy. It demonstrates that the live integration was configured and its rate-limit failures were surfaced, but **the requested PDF extraction did not succeed**. Retry after confirming the Gemini account's quota and access, then rerun both instructions and verify all 13 pages before drawing quality conclusions. A PNG/JPG sample is also required for live image-input evaluation.
