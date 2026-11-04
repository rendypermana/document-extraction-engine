// HTTP adapter for the API contract in docs/API.md.
const API_BASE = "/api";
const ACCEPTED_TYPES = Object.freeze(["application/pdf", "image/png", "image/jpeg"]);
const ACCEPTED_EXTENSIONS = Object.freeze([".pdf", ".png", ".jpg", ".jpeg"]);

export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new ApiError(
      0,
      "network_error",
      "Could not reach the backend. Check your connection and try again.",
    );
  }

  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError(
      response.status,
      "invalid_response",
      "The backend returned an unreadable response.",
    );
  }

  if (!response.ok) {
    const error = payload?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "http_error",
      error?.message ?? "The backend request failed.",
      error?.details ?? null,
    );
  }
  return payload;
}

export function checkFileLocally(file) {
  if (!file) {
    return null;
  }
  if (file.size === 0) {
    return { code: "empty_file", message: "The file is empty and cannot be processed." };
  }
  const extension = file.name?.match(/\.[^.]+$/)?.[0]?.toLowerCase() ?? "";
  if (
    (file.type && !ACCEPTED_TYPES.includes(file.type)) ||
    (!file.type && !ACCEPTED_EXTENSIONS.includes(extension))
  ) {
    return {
      code: "unsupported_file_type",
      message: "Unsupported file type. Use PDF, PNG, or JPG.",
    };
  }
  return null;
}

export function fetchProviders() {
  return request("/providers");
}

export function fetchDomains() {
  return request("/domains");
}

export function createRun(form) {
  const body = new FormData();
  body.append("file", form.file);
  body.append("instructions", form.instructions);
  body.append("provider", form.providerId);
  body.append("domain", form.domainId);
  body.append("use_cache", String(form.useCache));
  body.append("aggregate", String(form.aggregate));
  return request("/extract", { method: "POST", body });
}

export function fetchRun(runId) {
  return request(`/runs/${encodeURIComponent(runId)}`);
}

export function markdownDownloadName(sourceName) {
  const base = String(sourceName ?? "result")
    .replace(/\.[^.]+$/, "")
    .replace(/[^a-zA-Z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `${base || "result"}.md`;
}
