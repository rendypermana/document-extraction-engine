import assert from "node:assert/strict";
import test from "node:test";

import {
  ApiError,
  checkFileLocally,
  createRun,
  fetchDomains,
  fetchProviders,
  fetchRun,
} from "../static/js/api.js";

function mockFetch(t, implementation) {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = implementation;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
}

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

test("catalog requests use the live API endpoints", async (t) => {
  const requested = [];
  mockFetch(t, async (url) => {
    requested.push(String(url));
    return jsonResponse({ providers: [], domains: [] });
  });

  await fetchProviders();
  await fetchDomains();

  assert.deepEqual(requested, ["/api/providers", "/api/domains"]);
});

test("createRun sends the multipart fields expected by the API", async (t) => {
  let captured;
  mockFetch(t, async (url, options) => {
    captured = { url: String(url), options };
    return jsonResponse({ run_id: "run-1", status: "queued" }, 202);
  });
  const file = Object.assign(new Blob(["%PDF-1.4"]), { name: "sample.pdf" });

  const result = await createRun({
    file,
    instructions: "Extract headings",
    providerId: "fake",
    domainId: "generic",
  });

  assert.deepEqual(result, { run_id: "run-1", status: "queued" });
  assert.equal(captured.url, "/api/extract");
  assert.equal(captured.options.method, "POST");
  assert.equal(captured.options.body.get("instructions"), "Extract headings");
  assert.equal(captured.options.body.get("provider"), "fake");
  assert.equal(captured.options.body.get("domain"), "generic");
  assert.equal(captured.options.body.has("use_cache"), false);
  assert.equal(captured.options.body.has("aggregate"), false);
  assert.equal(captured.options.body.get("file").size, file.size);
  assert.equal(captured.options.headers, undefined);
});

test("fetchRun encodes run ids and propagates the API error contract", async (t) => {
  let requested;
  mockFetch(t, async (url) => {
    requested = String(url);
    return jsonResponse(
      { error: { code: "run_not_found", message: "Run not found." } },
      404,
    );
  });

  await assert.rejects(fetchRun("run/with space"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 404);
    assert.equal(error.code, "run_not_found");
    assert.equal(error.message, "Run not found.");
    return true;
  });
  assert.equal(requested, "/api/runs/run%2Fwith%20space");
});

test("network failures become visible API errors", async (t) => {
  mockFetch(t, async () => {
    throw new TypeError("private transport detail");
  });

  await assert.rejects(fetchProviders(), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.code, "network_error");
    assert.equal(error.message.includes("private transport detail"), false);
    return true;
  });
});

test("local file checks allow supported types and reject empty or unsupported files", () => {
  assert.equal(checkFileLocally({ name: "scan.png", type: "", size: 12 }), null);
  assert.equal(
    checkFileLocally({ name: "scan.png", type: "application/zip", size: 12 })?.code,
    "unsupported_file_type",
  );
  assert.equal(
    checkFileLocally({ name: "empty.pdf", type: "application/pdf", size: 0 })?.code,
    "empty_file",
  );
});
