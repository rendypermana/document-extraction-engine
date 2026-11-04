// HTTP adapter for the endpoints in docs/API.md.
//
// Right now every function is answered by the demo adapter in `demoAdapter`,
// because the backend does not exist yet. The exported surface is deliberately
// the same shape a `fetch` implementation will have, so switching to the real
// backend means replacing the bodies of these six functions and nothing else:
// no caller, no renderer, and no DOM code has to change.
import {
  DEMO_DOMAINS,
  DEMO_HTTP_ERRORS,
  DEMO_PROGRESS_STEPS,
  DEMO_PROVIDERS,
  DEMO_RUN,
} from "./fixtures.js";

const API_BASE = "/api";

// Amount of time the demo adapter spends in each progress step, in ms. These are
// wall-clock delays of the preview, not simulated extraction durations.
const STEP_DELAY_MS = 700;

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details ?? null;
  }
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

// Keeps a handle on the demo run so polling can advance it.
const demoRuns = new Map();

function demoHttpError(key) {
  const entry = DEMO_HTTP_ERRORS[key];
  return new ApiError(
    entry.status,
    entry.body.error.code,
    entry.body.error.message,
    entry.body.error.details,
  );
}

// File-type gating that mirrors the server-side checks named in docs/API.md §4.4.
// The real backend still has the final say; this only prevents an obviously
// unsupported upload from reaching it.
const ACCEPTED_TYPES = Object.freeze(["application/pdf", "image/png", "image/jpeg"]);
const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

export function checkFileLocally(file) {
  if (!file) {
    return null;
  }
  if (file.size === 0) {
    return { code: "empty_file", message: "Berkas kosong tidak dapat diproses." };
  }
  if (!ACCEPTED_TYPES.includes(file.type)) {
    const entry = DEMO_HTTP_ERRORS.unsupported_file_type.body.error;
    return { code: entry.code, message: entry.message };
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    const entry = DEMO_HTTP_ERRORS.file_too_large.body.error;
    return { code: entry.code, message: entry.message };
  }
  return null;
}

export async function fetchProviders() {
  await delay(120);
  return structuredClone(DEMO_PROVIDERS);
}

export async function fetchDomains() {
  await delay(120);
  return structuredClone(DEMO_DOMAINS);
}

export async function createRun(form) {
  await delay(300);

  // Same synchronous rejections a live server performs before a run exists.
  if (!form.file) {
    throw new ApiError(400, "missing_field", "Field wajib tidak ada: file.");
  }
  if (form.instructions.trim().length === 0) {
    throw new ApiError(400, "empty_instructions", "Instruksi ekstraksi kosong.");
  }
  if (form.file.size > MAX_UPLOAD_BYTES) {
    throw demoHttpError("file_too_large");
  }
  if (!ACCEPTED_TYPES.includes(form.file.type)) {
    throw demoHttpError("unsupported_file_type");
  }
  const provider = DEMO_PROVIDERS.providers.find((item) => item.id === form.providerId);
  if (!provider) {
    throw new ApiError(400, "unknown_provider", "Provider tidak dikenal.");
  }
  if (!provider.available) {
    throw new ApiError(
      400,
      "provider_unavailable",
      provider.unavailable_reason ?? "Provider tidak dikonfigurasi.",
    );
  }

  const runId = `demo-${Date.now().toString(36)}`;
  demoRuns.set(runId, {
    step: 0,
    polls: 0,
    pages: form.pages ?? DEMO_FILE.pages,
  });

  return {
    run_id: runId,
    status: "queued",
    status_url: `${API_BASE}/runs/${runId}`,
  };
}

export async function fetchRun(runId) {
  const state = demoRuns.get(runId);
  if (!state) {
    throw new ApiError(404, "run_not_found", "Run tidak ditemukan atau sudah kedaluwarsa.");
  }

  await delay(STEP_DELAY_MS);
  state.polls += 1;

  const createdAt = DEMO_RUN.created_at;

  if (state.polls === 1) {
    return {
      run_id: runId,
      status: "queued",
      created_at: createdAt,
      progress: {
        stage: "loading",
        pages_total: state.pages,
        pages_done: 0,
        pages_failed: 0,
        pages: [],
      },
      result: null,
      errors: [],
      warnings: [],
    };
  }

  const stepIndex = state.polls - 2;
  if (stepIndex < DEMO_PROGRESS_STEPS.length) {
    return {
      run_id: runId,
      status: "running",
      created_at: createdAt,
      progress: { ...DEMO_PROGRESS_STEPS[stepIndex] },
      result: null,
      errors: [],
      warnings: [],
    };
  }

  demoRuns.delete(runId);
  return {
    ...structuredClone(DEMO_RUN),
    run_id: runId,
    created_at: createdAt,
  };
}

// The UI downloads from data it already holds (docs/API.md §5 step 5). The server
// endpoint exists for curl and evaluation scripts, so no client call is made here.
export function markdownDownloadName(sourceName) {
  const base = String(sourceName ?? "hasil")
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${base || "hasil"}.md`;
}
