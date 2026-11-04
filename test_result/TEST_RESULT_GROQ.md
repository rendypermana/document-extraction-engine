# Groq Evaluation Report

**Test date:** November 4, 2026  
**Sample:** [`2608.16753v1.pdf`](../test_file/2608.16753v1.pdf)  
**Provider/model:** Groq — `openai/gpt-oss-120b`  
**Domain:** Research paper  
**Vision:** Disabled  
**Structured output:** Enabled  
**PDF pages:** 13

## Executive Summary

Two runs were submitted through the application API with different extraction instructions. Each extracted only page 1 of 13 and ended with `completed_with_warnings`. Each run recorded 12 page failures: HTTP 413 capability errors and Groq rate limits. Therefore, **full-PDF processing was not achieved**, and neither result should be treated as a complete document extraction.

The first run produced two items from page 1—the title and author—and both had verified evidence. The second run produced three claims from page 1; two evidence excerpts were automatically verified and one was marked `evidence_not_found`. All three claims from the successfully processed page were manually checked against the source and were substantively supported. This small check does not demonstrate document-wide completeness.

The `test_file/` directory contained only this PDF. No PNG/JPG sample was available, so live evaluation of image inputs was not possible. The Groq model was also configured without vision.

## Configuration and Method

The local API was healthy and reported Groq as available. Both runs explicitly selected `provider=groq`; the default provider configured in `.env` was unchanged. The active settings were:

| Setting | Value |
|---|---|
| `GROQ_MODEL` | `openai/gpt-oss-120b` |
| `GROQ_VISION` | `false` |
| `GROQ_STRUCTURED_OUTPUT` | `true` |
| Domain | `research_paper` |
| Input | 3,702,471-byte PDF, 13 pages |
| Pages with a local text layer | 13/13 |

Each run submitted the entire PDF as one document. The application pipeline processes pages sequentially. No application code changed between the two runs.

### Instruction 1 — Full-content extraction

> Extract all readable text-layer content from every page of this research paper. Include the title, authors, abstract, section headings, prose, mathematical statements and equations, examples, table captions and complete table headers/rows/footnotes, figure captions and visible textual labels where available in the text layer, conclusions, acknowledgments, and references. Preserve the source wording, quantities, units, and hierarchy. Give each extracted fact a concise supporting verbatim excerpt and the exact source page. Mark missing, unreadable, or uncertain material rather than guessing. Do not claim to read visual-only content because this run uses a text-only model. Do not omit any page.

### Instruction 2 — Focused argument

> Across this research paper, extract only its central research question, the author's main claims about mathematical research goals and AI, the proposed recommendations, and the conclusion. Include a short verbatim supporting excerpt and exact page reference for each item. Use only text available in the PDF text layer; do not infer visual-only figure content. Mark uncertainty explicitly and do not guess. Keep the output concise, and process every page before deciding whether it contains relevant evidence.

## Operational Results

| Run | Run ID | Status | Pages completed | Failed pages | Duration | Items | Verified evidence | Warnings | Retries |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| Full-content extraction | `a22e0689-12b9-4bb4-ab54-f23228104158` | `completed_with_warnings` | 1/13 | 12 | 23.57 s | 2 | 2/2 (100%) | 0 | 0 |
| Focused argument | `b4538787-d2a1-4cae-9785-f36784ce039e` | `completed_with_warnings` | 1/13 | 12 | 13.59 s | 3 | 2/3 (66.7%) | 1 | 1 |

| Validation metric | Full-content extraction | Focused argument |
|---|---:|---:|
| `schema_ok` | true | true |
| `markdown_format_ok` | true | true |
| `all_pages_processed` | false | false |
| `items_without_evidence` | 0 | 0 |
| Pages with provider errors | 12 | 12 |

**Provider error breakdown:**

| Error code | Full-content extraction | Focused argument |
|---|---:|---:|
| `provider_capability` — Groq HTTP 413 | 6 | 9 |
| `provider_rate_limit` | 6 | 3 |

The first run had no item-level warnings but still had 12 page errors. The second run had one `evidence_not_found` warning for an item on page 1. Input/output token counts and monetary cost were unavailable in both runs' metadata; they are not reported as zero or estimated from page counts.

## Quality Metrics and Manual Checks

The selected metrics distinguish **processing completeness** from **accuracy of the examples that were actually extracted**:

- **Page coverage** = successfully completed pages ÷ total pages. This directly measures whether the PDF was fully processed: both runs achieved **1/13 (7.7%)**.
- **Automatic evidence match rate** = references matching the PDF text layer ÷ all references from completed pages. Results were **2/2 (100%)** for the first run and **2/3 (66.7%)** for the second. This measures excerpt matching, not the truth of every extracted claim.
- **Manually checked source answers** compare output facts against the original PDF pages. This checks factual support independently of model confidence.
- **Operational performance** is measured using duration, successful/failed pages, retries, errors, and reported token usage. Duration was available, but token counts and cost were not.

### Manually checked source answers

| Run | Extracted fact/claim | Source | Manual result |
|---|---|---:|---|
| Full-content extraction | Title: “MATHEMATICS IN THE AGE OF AI” | Page 1 | Correct; excerpt automatically verified |
| Full-content extraction | Author: “TERENCE TAO” | Page 1 | Correct; excerpt automatically verified |
| Focused argument | Research question about the goals and values of mathematical research | Page 1 | Meaning supported by the abstract; reference automatically verified |
| Focused argument | Claim that AI tools will be capable of research-level mathematical tasks | Page 1 | Supported by the abstract; reference automatically verified |
| Focused argument | Claim that mathematical values and practices are being tested | Page 1 | Content and page manually confirmed; excerpt did not match automatically |

The manual check was **2/2** facts in the first run and **3/3** claims returned by the second run. These figures apply only to items produced from page 1. The first run did not return the abstract, the question on page 2, or figure captions from later pages; the second run likewise never reached those pages. The manual check is therefore not a document-wide accuracy or recall score.

## Required-Scope Assessment

| Requirement | Result for this Groq evaluation |
|---|---|
| PDF input and all pages | The 13-page PDF loaded, but only 1/13 pages completed in each run. **Not met.** |
| PNG/JPG input and both sample files | No image sample was present in `test_file/`; no live vision run was performed. Application loader support is not evidence of live extraction. **Not evaluated.** |
| Prose | The title, author, and three abstract claims were returned from page 1. **Partially demonstrated.** |
| Tables and table hierarchy | No table output could be assessed from these partial runs. **Not demonstrated.** |
| Charts, labels, values, units, and estimates | No numeric chart was successfully tested; visual diagrams were not processed by this text-only model. **Not demonstrated.** |
| Form fields and checkboxes | No such content was successfully processed in this sample. **Not demonstrated.** |
| Two instructions without code changes | Two different instructions were submitted through the API using the same file and domain. **Demonstrated as an instruction workflow**, but each run covered only one page. |
| Page references and source excerpts | All returned items refer to page 1; two of three excerpts in the focused run were automatically verified. **Partially met.** |
| Uncertainty and unsupported evidence | The second run marked one excerpt `evidence_not_found`; the item was marked uncertain. **Observed.** |
| Schema/Markdown validation and provider failures | Schema and Markdown were valid while page errors were recorded separately. **Works for partial runs**, but `all_pages_processed=false`. |
| Provider independence and extensibility | The application architecture provides a shared provider contract and provider registry. See the design summary below. **Supported by application structure; not an extraction-quality metric.** |

## Modularity, Reliability, and Design Trade-offs

- Providers implement a shared `Provider` contract, and provider selection is wired through configuration and a registry. To add a provider, implement an adapter that maps the shared request to the provider API, register it, connect credential/model/capability settings, and add adapter tests.
- Extraction domains are stored as profiles; a new domain can add instructions and hints without changing provider adapters.
- Loaders implement a shared contract and are selected through a content-aware registry. A new format can be added with a loader that normalizes input into pages, registers the loader, and tests MIME/content detection and failure cases.
- Model capabilities such as vision and structured output are represented separately from the extraction contract. In this test, `vision=false` means image-only content cannot be analyzed; the model receives text from the PDF text layer.
- The parser, evidence validator, aggregator, and renderer are separate from provider adapters. Evidence validation compares excerpts with PDF text blocks; line wrapping or hyphenation can cause a false negative, as with one excerpt in the second run that was supported during manual inspection but failed automatic verification.
- The design favors structured output, auditable references, and explicit uncertainty. This improves transparency, but an automatic warning does not always mean a claim is false. Conversely, valid schema and Markdown do not prove that every page succeeded or that the content is complete.
- The application maps HTTP 413 to `provider_capability` and quota restrictions to `provider_rate_limit`. Since Groq returned both error types, the partial runs were not represented as full successes.
- Page caching and cross-page table aggregation options are not implemented; enabling or disabling them would not change these run results.

## Limitations and Conclusion

This evaluation shows that Groq `openai/gpt-oss-120b` can return a few evidence-backed items from the first page, but **did not extract the full PDF** in either attempt. HTTP 413 responses and rate limits prevented processing 12 pages. The short durations should not be interpreted as full-document extraction performance because coverage was only 1/13 pages.

The model has no vision capability in this configuration, so content available only as pixels—including visual portions of diagrams—was not covered. The PDF did not test forms or checkboxes, and no PNG/JPG sample was available. Tables and charts also cannot be assessed from runs that failed before most pages were processed. Repeat the evaluation after addressing the HTTP 413 and Groq account limits, and confirm that all pages complete before making claims of full-document extraction.
