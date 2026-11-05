# Document Extraction Engine

A local, model-agnostic application that extracts structured information from PDF documents and PNG/JPG images. It turns user instructions and document pages into evidence-backed Markdown, while making uncertainty and processing failures visible.

## Features

- Accepts PDF, PNG, and JPG uploads.
- Processes PDF documents page by page.
- Supports configurable extraction instructions and domain profiles, including general documents, research papers, and tax forms.
- Connects to Gemini, Groq, or OpenRouter through provider adapters; a fake provider is available for offline integration testing.
- Requests structured JSON from the model, validates the response, checks available evidence, and renders Markdown in application code.
- Displays source references, page progress, warnings, and page-level failures.
- Provides a browser interface and a FastAPI API from the same application.

## How It Works

1. The user uploads a document and selects extraction instructions, a domain, and an available provider.
2. A loader validates the file and turns it into pages with text-layer content and rendered images.
3. The extraction pipeline builds a schema-guided request for each page and sends it to the configured provider.
4. The response is parsed and validated. Evidence is checked against the text layer when one is available.
5. The application assembles page results and renders Markdown with source references and uncertainty markers.

The model does not generate the final Markdown directly. The application validates structured output and renders the result.

## Requirements

- Docker and Docker Compose for the recommended setup.
- A provider API key and a model configured in `.env` for live extraction.

The `fake` provider can be used without an API key to exercise the application flow. It is not an AI model and does not measure extraction accuracy.

## Quick Start

Create a local environment file from the example if needed:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `.env` and configure the provider, model, and API key. For example:

```env
PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
GROQ_VISION=false
GROQ_STRUCTURED_OUTPUT=true
```

Then build and start the application:

```powershell
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). The API health check is available at [http://localhost:8000/api/health](http://localhost:8000/api/health).

To apply `.env` changes, recreate the service:

```powershell
docker compose up -d
```

To stop the application:

```powershell
docker compose down
```

## Available Providers

The application currently supports these providers:

- **Gemini** (`gemini`)
- **Groq** (`groq`)
- **OpenRouter** (`openrouter`)
- **Fake** (`fake`) — deterministic integration testing only; it is not an AI model.

Live provider availability depends on the corresponding API key and model being configured. `PROVIDER` in `.env` sets the default provider. The UI can also select another configured, available provider for an individual run.

### Provider Configuration

Provider-specific keys and model IDs are configured in `.env`; do not commit that file or paste API keys into source code, logs, screenshots, or chat.

| Provider | Required settings | Notes |
|---|---|---|
| Gemini | `GEMINI_API_KEY`, `MODEL_NAME` | Supports image input and structured output, subject to model access and quota. |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL` | `GROQ_VISION` and `GROQ_STRUCTURED_OUTPUT` must match the selected model's capabilities. |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | `OPENROUTER_VISION` and `OPENROUTER_STRUCTURED_OUTPUT` must match the selected model and endpoint. |
| Fake | None | Deterministic local integration provider; not suitable for evaluating model quality. |

Set the capability flags to match the selected model. Check the provider's current documentation and account dashboard for model availability, supported features, quotas, and pricing.

### Vision and Text-Only Models

When a provider is configured without vision, the application sends the page's extracted text rather than its rendered image. Local OCR can provide text for scanned pages, but text-only models still cannot interpret visual-only content such as charts. Choose a vision-capable model for documents where visual structure matters.

The loaders run local Tesseract OCR on image uploads and PDF pages that have no digital text layer. The Docker image includes Tesseract and English/Indonesian language data; local installs need Tesseract and the selected language data installed separately. Set `OCR_ENABLED=false` to disable OCR, or set `OCR_LANGUAGE` to installed Tesseract language codes joined with `+` (for example `ind+eng`; the application default is `eng`). OCR text and normalized page coordinates are supplied to the model for evidence matching, but matching an OCR excerpt is labeled as an OCR-text match because OCR can misread the original image. The page image is still sent to vision-capable models, and OCR does not replace visual analysis for charts or layout.

### Image Enhancement Pipeline

PNG and JPG uploads are normalized before both local OCR and vision-model
inference. The image loader applies the following steps:

1. Validate the file signature and apply its EXIF orientation.
2. Downscale images that exceed the configured `MAX_IMAGE_PIXELS` safety limit.
3. Upscale small document images whose shortest edge is between 256 and 899
   pixels. The scale is limited to 2x and a 1,200-pixel shortest-edge target,
   using Lanczos resampling.
4. Detect effectively grayscale images using their average color saturation. For
   low-saturation documents, convert luminance to grayscale and apply automatic
   contrast stretching. Color documents retain their RGB information.
5. Apply an unsharp mask to strengthen thin printed characters, box borders, and
   checkbox marks. Transparent input is composited onto white first.
6. Encode the normalized result as PNG, then use that same enhanced image for
   Tesseract OCR and for providers configured with vision support.

This preprocessing improves readability for compressed phone images and faint
scans, but it cannot reconstruct characters that are absent from the original
pixels. Evidence marked `UNCERTAIN` must therefore still be checked against the
source document.

## OpenRouter Evaluation

A live sample evaluation was run with OpenRouter using `google/gemini-3-flash-preview` and the research-paper domain. The test input was the 13-page PDF at [`test_file/2608.16753v1.pdf`](test_file/2608.16753v1.pdf). The requested path `test_file/2608-16753v1.pdf` is not the current filename in the repository; the existing PDF filename uses a period after `2608`. The extracted Markdown sample is available at [`test_result/2608-16753v1.md`](test_result/2608-16753v1.md).

The Markdown sample demonstrates an end-to-end extraction rather than only a provider response: it contains structured sections such as the abstract, study objectives, methods, questions, results, figure captions, and references. Extracted claims cite source markers (for example, `[S1]`), and uncertain passages are explicitly marked. This makes the sample useful for reviewing readability, structure, source linking, and uncertainty handling against the original PDF.

Two different instructions were evaluated without changing application code:

| Instruction | Pages processed | Duration | Items | Evidence references verified | Warnings |
|---|---:|---:|---:|---:|---:|
| Full-content extraction | 13/13 | 243.62 s | 84 | 76/89 (85.4%) | 13 |
| Focused argument extraction | 13/13 | 106.71 s | 65 | 52/69 (75.4%) | 19 |

Both runs passed schema and Markdown checks and processed every page, but ended with `completed_with_warnings`. The warnings included evidence excerpts that could not be matched automatically to the PDF text layer; the focused run also had two items without evidence. Eight manually checked facts per run matched the source and cited the expected pages (8/8 in each run). This is a small spot-check, not a document-wide accuracy or completeness score. See the [detailed OpenRouter test report](test_result/TEST_RESULT_OPENROUTER.md) for run IDs, instructions, methodology, metrics, and limitations.

This PDF contains prose and conceptual figures, but no numeric charts, tables,
forms, or checkboxes were available in that sample. Image input was evaluated
separately in the tax-form run below. The design trade-off favors auditable,
evidence-linked output: strict text-layer matching can flag a valid excerpt as
unverified when line wrapping or image-only content differs from extracted text.

### Additional OpenRouter Research-Paper PDF Result

Another end-to-end PDF run demonstrates that OpenRouter with
`google/gemini-3-flash-preview` can answer the `research_paper` extraction task
on a multi-page scientific paper. The generated result covers 18 source pages
and includes the study objectives, research questions, methods, participant and
equipment details, main findings, eye-tracking analysis, structured tables,
conclusions, and 72 page-linked source references.

The complete generated Markdown is available at
[`test_result/1-s2-0.md`](test_result/1-s2-0.md).

This artifact provides a directly reviewable example that the configured
OpenRouter model can process a research-paper PDF through the complete pipeline,
not merely return a successful provider response. Some complex or continued
table cells remain marked `UNCERTAIN`, so the output demonstrates working
extraction rather than perfect document-wide accuracy and should be checked
against the source PDF before operational use.

### OpenRouter Tax-Form Image Evaluation

A subsequent live image evaluation demonstrates that OpenRouter with
`google/gemini-3-flash-preview` can extract structured information from a
low-resolution Indonesian corporate income-tax form image. The tax-form domain
and vision input were used for this run. The image-enhancement pipeline enlarged
the sample from 448x685 to 896x1,370 pixels and applied grayscale contrast
stretching and sharpening before OCR and model inference. The result includes the
document title
(`SPT TAHUNAN PAJAK PENGHASILAN WAJIB PAJAK BADAN`), form number `1771`, tax
year, taxpayer identity, business type, accounting period, checkbox states,
taxable-income amounts, tax credits, tax payable, and payment date.

The complete evidence-linked output is available at
[`test_result/WhatsApp-Image-2026-11-05-at-11-04-55-AM.md`](test_result/WhatsApp-Image-2026-11-05-at-11-04-55-AM.md).

This sample proves that the configured OpenRouter vision model can return useful
structured tax-document extraction from a JPG image through the end-to-end
application pipeline. It is not a claim of perfect OCR accuracy: several values
and checkbox states remain marked `UNCERTAIN` when their evidence cannot be
matched reliably against OCR text. The source image is low resolution, so results
should still be reviewed against the original document before operational use.

## Groq Evaluation

A live Groq evaluation used the configured model `openai/gpt-oss-120b` on the same 13-page research-paper sample, [`test_file/2608.16753v1.pdf`](test_file/2608.16753v1.pdf). Groq was selected for each run through the API; the application's `.env` default provider was not changed. The model was configured with structured output enabled and vision disabled.

**Account tier note:** These Groq runs used free-tier access. The observed rate-limit failures should therefore be interpreted in the context of free-tier quotas, which can vary by account and change over time. The HTTP 413 responses were also observed; this evaluation does not establish that they were caused by the account tier.

Two extraction instructions were tested without changing application code: one requested exhaustive text-layer extraction, and the other focused on the paper's central question, claims, recommendations, and conclusion. Both runs returned structured Markdown, but neither completed the document. Each processed **1 of 13 pages** and recorded **12 page errors**. Six errors in the full-content run and nine in the focused run were HTTP 413 capability errors; the remaining six and three errors, respectively, were Groq rate limits.

| Instruction | Pages completed | Duration | Items | Evidence verified | Page errors |
|---|---:|---:|---:|---:|---:|
| Full-content extraction | 1/13 | 23.57 s | 2 | 2/2 (100%) | 12 |
| Focused argument | 1/13 | 13.59 s | 3 | 2/3 (66.7%) | 12 |

Both runs had valid schema and Markdown according to application metadata, but ended with `completed_with_warnings` and `all_pages_processed=false`. The first run returned the paper title and author, both supported by verified page-1 excerpts. The focused run returned three claims from page 1. All three claims were manually checked against the PDF and were substantively supported; two excerpts matched the text layer automatically, while the third was marked `evidence_not_found`. That mismatch illustrates the trade-off of strict text-block matching: line wrapping or hyphenation can cause a valid passage to be flagged for manual review.

These results show that Groq produced a small, evidence-backed extraction from the first page, but they do **not** establish PDF-wide accuracy or completeness. The short run durations are not comparable as full-document throughput because 12 pages failed in each run. Input/output token counts and provider billing cost were unavailable in the run metadata.

The supplied sample directory contained no PNG/JPG image, and this Groq configuration does not support vision. Visual-only content therefore could not be tested. The partial runs also provide no reliable coverage evidence for tables, numeric charts, form fields, or checkboxes.

The detailed prompts, run IDs, source checks, error breakdown, metrics, and scope assessment are available in the [Groq test report](test_result/TEST_RESULT_GROQ.md).

## Gemini Evaluation

A live evaluation used Gemini `gemini-3.5-flash` with vision and structured output enabled on [`test_file/2608.16753v1.pdf`](test_file/2608.16753v1.pdf). Two different extraction instructions were submitted through the application without changing code: one requested all readable content, and the other focused on the paper's main argument and recommendations.

**Account tier note:** These Gemini runs used free-tier access. The observed rate-limit failures should be interpreted in the context of free-tier quotas and request limits, which can vary by account and change over time; the test does not establish that the model or application would behave the same under paid-tier limits.

Neither run successfully extracted any page. Both processed **0 of 13 pages**, returned zero items and zero source references, and ended with `completed_with_warnings`. All 13 page requests in each run failed with Gemini rate-limit errors, despite 39 retries per run. Each attempt took approximately three minutes:

| Instruction | Pages completed | Duration | Items | Page errors | Retries |
|---|---:|---:|---:|---:|---:|
| Full-content extraction | 0/13 | 189.04 s | 0 | 13 rate limits | 39 |
| Focused argument | 0/13 | 187.30 s | 0 | 13 rate limits | 39 |

Schema and Markdown checks reported true, but `all_pages_processed=false`. This is a useful reliability observation: a structurally valid empty result is not evidence that extraction succeeded. Since the model returned no facts or references, extraction accuracy and evidence-match rate could not be calculated. Several source facts were manually confirmed in the PDF, but there were no Gemini answers to score against them.

The configured Gemini capability includes vision, but these failed runs do not demonstrate image extraction. The only supplied sample was the PDF; no PNG/JPG image was present. Tables, numeric charts, form fields, and checkboxes were therefore not evaluated. Token usage and provider billing cost were also unavailable.

The observed provider failure was consistently reported as a rate limit; the test does not establish whether the underlying cause was request rate, account quota, billing, or model access. The detailed prompts, source checks, run IDs, metrics, and limitations are documented in the [Gemini test report](test_result/TEST_RESULT_GEMINI.md).

## API Overview

The API is served under `/api`:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/providers` | Provider availability and capabilities |
| `GET` | `/api/domains` | Available extraction profiles |
| `POST` | `/api/extract` | Upload a document and create an extraction run |
| `GET` | `/api/runs/{run_id}` | Poll run progress and retrieve results |
| `GET` | `/api/runs/{run_id}/markdown` | Download the Markdown result |

Requests use multipart form data for document uploads. Extraction runs are asynchronous: create a run, poll its status until it is complete, then retrieve or download the Markdown result. Invalid inputs and unavailable providers are reported as API errors; page-level provider failures are included in run results.

## Development and Tests

The application is implemented in Python with FastAPI. Automated tests use local fixtures and mocked providers; the default suite does not require a live API key.

```powershell
pytest
```

The UI and API use a single origin. For local development outside Docker, install dependencies from `requirements.txt` and start the application with:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Current Limitations

- Run state and results are stored in memory and are lost when the application restarts. There is no persistent database.
- Uploaded temporary files are removed after processing.
- Page caching and cross-page table merging are not implemented and their controls have been removed from the UI. For backward compatibility, the API accepts the legacy `use_cache` and `aggregate` fields, but requests that set either to `true` receive an `unsupported_option` error asking the user to reload the page. Static UI assets are served with `Cache-Control: no-cache` to reduce stale-page issues.
- A successful model response does not guarantee accurate extraction. Validate results against the source document, especially tables, charts, and ambiguous text.
- Provider access, supported models, quotas, rate limits, and pricing depend on the provider account and may change.
- The local API has no authentication. Do not expose it to untrusted networks.
- Required-sample evaluations and extraction-quality ground truth are separate from automated integration tests. Do not treat fake-provider tests as model-quality evidence.

## Next Improvements

- Add persistent storage for runs, results, metadata, and audit history.
- Add authentication, authorization, and deployment safeguards for multi-user or public environments.
- Process independent pages concurrently with configurable limits while preserving provider rate-limit protection.
- Implement page-level caching and reliable cross-page table merging.
- Add a document preview with clickable references and bounding-box highlighting.
- Support additional export formats such as structured JSON and CSV.
- Expand the evaluation dataset with PDF and image samples containing tables, numeric charts, forms, checkboxes, scans, and difficult OCR cases.
- Create manually reviewed ground truth and report extraction precision, recall, evidence-match quality, unsupported-output rate, latency, token usage, and cost.
- Add production monitoring for provider availability, retries, rate limits, latency, usage, and extraction failures.

