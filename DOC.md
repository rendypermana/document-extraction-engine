# Document Extraction Engine

A local, model-agnostic application that extracts structured information from PDF documents and PNG/JPG images. It turns user instructions and document pages into evidence-backed Markdown, while making uncertainty and processing failures visible.

> **Documentation transition:** `DOC.md` is a proposed replacement for `README.md`. The existing `README.md` is intentionally retained.

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

## Provider Configuration

`PROVIDER` in `.env` sets the default provider. The UI can also select another configured, available provider for an individual run. Provider-specific keys and model IDs are configured in `.env`; do not commit that file or paste API keys into source code, logs, screenshots, or chat.

| Provider | Required settings | Notes |
|---|---|---|
| Gemini | `GEMINI_API_KEY`, `MODEL_NAME` | Supports image input and structured output, subject to model access and quota. |
| Groq | `GROQ_API_KEY`, `GROQ_MODEL` | `GROQ_VISION` and `GROQ_STRUCTURED_OUTPUT` must match the selected model's capabilities. |
| OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` | `OPENROUTER_VISION` and `OPENROUTER_STRUCTURED_OUTPUT` must match the selected model and endpoint. |
| Fake | None | Deterministic local integration provider; not suitable for evaluating model quality. |

Set the capability flags to match the selected model. Check the provider's current documentation and account dashboard for model availability, supported features, quotas, and pricing.

### Vision and Text-Only Models

When a provider is configured without vision, the application sends the page's extracted text rather than its rendered image. Text-only models therefore cannot reliably extract scanned pages without a text layer or interpret visual-only content such as charts. Choose a vision-capable model for those documents.

## OpenRouter Evaluation

A live sample evaluation was run with OpenRouter using `google/gemini-3-flash-preview` and the research-paper domain. The test input was the 13-page PDF at [`test_file/2608.16753v1.pdf`](test_file/2608.16753v1.pdf). The requested path `test_file/2608-16753v1.pdf` is not the current filename in the repository; the existing PDF filename uses a period after `2608`. The extracted Markdown sample is available at [`test_result/2608-16753v1.md`](test_result/2608-16753v1.md).

The Markdown sample demonstrates an end-to-end extraction rather than only a provider response: it contains structured sections such as the abstract, study objectives, methods, questions, results, figure captions, and references. Extracted claims cite source markers (for example, `[S1]`), and uncertain passages are explicitly marked. This makes the sample useful for reviewing readability, structure, source linking, and uncertainty handling against the original PDF.

Two different instructions were evaluated without changing application code:

| Instruction | Pages processed | Duration | Items | Evidence references verified | Warnings |
|---|---:|---:|---:|---:|---:|
| Full-content extraction | 13/13 | 243.62 s | 84 | 76/89 (85.4%) | 13 |
| Focused argument extraction | 13/13 | 106.71 s | 65 | 52/69 (75.4%) | 19 |

Both runs passed schema and Markdown checks and processed every page, but ended with `completed_with_warnings`. The warnings included evidence excerpts that could not be matched automatically to the PDF text layer; the focused run also had two items without evidence. Eight manually checked facts per run matched the source and cited the expected pages (8/8 in each run). This is a small spot-check, not a document-wide accuracy or completeness score. See the [detailed OpenRouter test report](test_result/TEST_RESULT_OPENROUTER.md) for run IDs, instructions, methodology, metrics, and limitations.

This PDF contains prose and conceptual figures, but no numeric charts, tables, forms, or checkboxes were available to test. No PNG/JPG sample was present, so the image-input requirement remains unevaluated with a live model. The design trade-off favors auditable, evidence-linked output: strict text-layer matching can flag a valid excerpt as unverified when line wrapping or image-only content differs from extracted text. The application also accepts page-cache and cross-page table-merge options that are not implemented and do not affect results.

## Groq Evaluation

A live Groq evaluation used the configured model `openai/gpt-oss-120b` on the same 13-page research-paper sample, [`test_file/2608.16753v1.pdf`](test_file/2608.16753v1.pdf). Groq was selected for each run through the API; the application's `.env` default provider was not changed. The model was configured with structured output enabled and vision disabled.

Two extraction instructions were tested without changing application code: one requested exhaustive text-layer extraction, and the other focused on the paper's central question, claims, recommendations, and conclusion. Both runs returned structured Markdown, but neither completed the document. Each processed **1 of 13 pages** and recorded **12 page errors**. Six errors in the full-content run and nine in the focused run were HTTP 413 capability errors; the remaining six and three errors, respectively, were Groq rate limits.

| Instruction | Pages completed | Duration | Items | Evidence verified | Page errors |
|---|---:|---:|---:|---:|---:|
| Full-content extraction | 1/13 | 23.57 s | 2 | 2/2 (100%) | 12 |
| Focused argument | 1/13 | 13.59 s | 3 | 2/3 (66.7%) | 12 |

Both runs had valid schema and Markdown according to application metadata, but ended with `completed_with_warnings` and `all_pages_processed=false`. The first run returned the paper title and author, both supported by verified page-1 excerpts. The focused run returned three claims from page 1. All three claims were manually checked against the PDF and were substantively supported; two excerpts matched the text layer automatically, while the third was marked `evidence_not_found`. That mismatch illustrates the trade-off of strict text-block matching: line wrapping or hyphenation can cause a valid passage to be flagged for manual review.

These results show that Groq produced a small, evidence-backed extraction from the first page, but they do **not** establish PDF-wide accuracy or completeness. The short run durations are not comparable as full-document throughput because 12 pages failed in each run. Input/output token counts and provider billing cost were unavailable in the run metadata.

The supplied sample directory contained no PNG/JPG image, and this Groq configuration does not support vision. Visual-only content therefore could not be tested. The partial runs also provide no reliable coverage evidence for tables, numeric charts, form fields, or checkboxes. The cache and cross-page table-merge options are accepted by the application but are not implemented, so they do not alter these results.

The detailed prompts, run IDs, source checks, error breakdown, metrics, and scope assessment are available in the [Groq test report](test_result/TEST_RESULT_GROQ.md).

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
- The UI options **Use page cache** and **Merge tables across pages** are accepted by the API but are not implemented yet; checking or unchecking them currently does not change extraction results.
- A successful model response does not guarantee accurate extraction. Validate results against the source document, especially tables, charts, and ambiguous text.
- Provider access, supported models, quotas, rate limits, and pricing depend on the provider account and may change.
- The local API has no authentication. Do not expose it to untrusted networks.
- Required-sample evaluations and extraction-quality ground truth are separate from automated integration tests. Do not treat fake-provider tests as model-quality evidence.
