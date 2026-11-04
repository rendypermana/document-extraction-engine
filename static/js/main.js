// Wiring for the seven core UI functions: upload, editable instructions, run and
// progress, rendered Markdown, source references, visible errors, and download
// (REQ-39 to REQ-45). All state lives in one module-level snapshot; every update
// replaces it and re-renders the affected regions.
import {
  ApiError,
  checkFileLocally,
  createRun,
  fetchDomains,
  fetchProviders,
  fetchRun,
} from "./api.js";
import { downloadMarkdown } from "./download.js";
import { decorateReferenceMarkers, renderReferences } from "./references.js";
import { formatBytes, formatDuration, renderMarkdown } from "./render.js";
import { createInitialState, isTerminal, validateBeforeRun } from "./state.js";
import { RUN_STATE_LABEL, STAGE_LABEL, STATUS_LABEL, UI } from "./ui.js";

const el = (id) => {
  const node = document.getElementById(id);
  if (!node) {
    throw new Error(`Elemen UI wajib tidak ditemukan: #${id}`);
  }
  return node;
};

const dom = {
  dropzone: el("dropzone"),
  fileInput: el("file-input"),
  fileState: el("file-state"),
  fileHint: el("file-hint"),
  fileError: el("file-error"),
  provider: el("provider-select"),
  providerHelp: el("provider-help"),
  domain: el("domain-select"),
  domainHelp: el("domain-help"),
  instructions: el("instructions"),
  instructionsCount: el("instructions-count"),
  instructionsError: el("instructions-error"),
  optCache: el("opt-cache"),
  optAggregate: el("opt-aggregate"),
  runButton: el("run-button"),
  resetButton: el("reset-button"),
  downloadButton: el("download-button"),
  runState: el("run-state"),
  progressFill: el("progress-fill"),
  progressBar: el("progressbar"),
  progressCount: el("progress-count"),
  progressStage: el("progress-stage"),
  pageList: el("page-list"),
  messagesRegion: el("messages-region"),
  errorsBlock: el("errors-block"),
  errorsList: el("errors-list"),
  warningsBlock: el("warnings-block"),
  warningsList: el("warnings-list"),
  markdownPane: el("markdown-pane"),
  referencesList: el("references-list"),
  referencesSummary: el("references-summary"),
  metadataList: el("metadata-list"),
  liveRegion: el("live-region"),
};

let state = createInitialState();
let stopPolling = false;

function announce(message) {
  dom.liveRegion.textContent = message;
}

function setHidden(node, hidden) {
  node.classList.toggle(UI.layout.hidden, hidden);
  if (hidden) {
    node.classList.remove(UI.layout.visible);
  } else {
    node.classList.add(UI.layout.visible);
  }
}

function showNotice(node, message) {
  node.textContent = message;
  node.classList.remove(UI.notice.hidden);
  node.classList.add(UI.notice.visible);
}

function hideNotice(node) {
  node.textContent = "";
  node.classList.remove(UI.notice.visible);
  node.classList.add(UI.notice.hidden);
}

// ---------------------------------------------------------------- upload

function applyFile(file) {
  const problem = checkFileLocally(file);
  state = { ...state, file: problem ? null : file, fileError: problem?.message ?? null };

  if (problem) {
    dom.fileState.textContent = "Berkas ditolak";
    dom.fileHint.textContent = file ? file.name : "Tarik berkas ke sini atau pilih dari perangkat";
    dom.fileInput.setAttribute("aria-invalid", "true");
    showNotice(dom.fileError, `${problem.code.toUpperCase()}: ${problem.message}`);
    announce(`Berkas ditolak: ${problem.message}`);
  } else {
    dom.fileState.textContent = file ? "Berkas siap" : "Belum ada berkas";
    dom.fileHint.textContent = file
      ? `${file.name} \u00B7 ${formatBytes(file.size)}`
      : "Tarik berkas ke sini atau pilih dari perangkat";
    dom.fileInput.removeAttribute("aria-invalid");
    hideNotice(dom.fileError);
    if (file) {
      announce(`Berkas dipilih: ${file.name}`);
    }
  }
  updateRunButton();
}

// ---------------------------------------------------------------- selectors

function currentProvider() {
  return state.providers.find((item) => item.id === dom.provider.value) ?? null;
}

function renderProviderHelp() {
  const provider = currentProvider();
  if (!provider) {
    dom.providerHelp.textContent = "";
    return;
  }
  const parts = [provider.model];
  if (!provider.capabilities.vision) {
    parts.push("tanpa vision");
  }
  if (!provider.available) {
    parts.push(`tidak tersedia \u2014 ${provider.unavailable_reason ?? "belum dikonfigurasi"}`);
  }
  dom.providerHelp.textContent = parts.join(" \u00B7 ");
  dom.providerHelp.classList.toggle("line-through", !provider.available);
  if (provider.available) {
    dom.provider.removeAttribute("aria-invalid");
  } else {
    dom.provider.setAttribute("aria-invalid", "true");
  }
}

function renderDomainHelp() {
  const domain = state.domains.find((item) => item.id === dom.domain.value);
  dom.domainHelp.textContent = domain?.description ?? "";
}

// ---------------------------------------------------------------- instructions

function syncInstructions() {
  const value = dom.instructions.value;
  state = { ...state, instructions: value };
  dom.instructionsCount.textContent = String(value.length);
  if (value.length > 2000) {
    showNotice(
      dom.instructionsError,
      "INSTRUCTIONS_TOO_LONG: melebihi batas 2000 karakter.",
    );
    dom.instructions.setAttribute("aria-invalid", "true");
  } else {
    hideNotice(dom.instructionsError);
    dom.instructions.removeAttribute("aria-invalid");
  }
  updateRunButton();
}

function applyDomainDefault(domainId, overwrite) {
  const domain = state.domains.find((item) => item.id === domainId);
  if (!domain) {
    return;
  }
  // docs/PROMPTS.md: `default_instructions` only fills the textarea. It never
  // reaches the prompt behind the user's back, so an existing draft is preserved
  // unless the user picked another domain explicitly.
  if (!overwrite && dom.instructions.value.trim() !== "") {
    return;
  }
  dom.instructions.value = domain.default_instructions;
  syncInstructions();
}

// ---------------------------------------------------------------- run button

function blockingReason() {
  const provider = currentProvider();
  if (provider && !provider.available) {
    return `Provider ${provider.label} tidak tersedia: ${provider.unavailable_reason ?? "belum dikonfigurasi"}.`;
  }
  return validateBeforeRun(state);
}

function updateRunButton() {
  const reason = blockingReason();
  const busy = state.busy;
  dom.runButton.disabled = busy || reason !== null;
  dom.runButton.textContent = busy ? "Memproses\u2026" : "Jalankan ekstraksi";
  if (reason) {
    dom.runButton.title = reason;
    dom.progressStage.textContent = reason;
  } else {
    dom.runButton.removeAttribute("title");
    dom.progressStage.textContent = state.progress ? stageLabel(state.progress.stage) : "menunggu";
  }
  dom.downloadButton.disabled = !hasResult();
}

function hasResult() {
  return Boolean(state.run?.result?.markdown);
}

// ---------------------------------------------------------------- rendering

function stageLabel(stage) {
  return STAGE_LABEL[stage] ?? stage ?? "menunggu";
}

function renderRunState() {
  dom.runState.textContent = RUN_STATE_LABEL[state.runState] ?? state.runState;
}

function renderProgress() {
  const progress = state.progress;
  if (!progress) {
    dom.progressCount.textContent = "0 / 0";
    dom.progressFill.style.width = "0%";
    dom.progressBar.setAttribute("aria-valuenow", "0");
    dom.pageList.replaceChildren();
    return;
  }

  const total = progress.pages_total ?? 0;
  const done = progress.pages_done ?? 0;
  const failed = progress.pages_failed ?? 0;
  dom.progressCount.textContent = `${done} / ${total}${failed > 0 ? ` \u00B7 ${failed} gagal` : ""}`;

  // The bar reports processed pages only. It is never advanced by a timer, so it
  // cannot show progress the backend has not reported.
  const percent = total > 0 ? Math.round((done / total) * 100) : 0;
  dom.progressFill.style.width = `${percent}%`;
  dom.progressBar.setAttribute("aria-valuenow", String(percent));
  dom.progressBar.setAttribute("aria-valuetext", `${done} dari ${total} halaman diproses`);
  dom.progressStage.textContent = stageLabel(progress.stage);

  dom.pageList.replaceChildren();
  for (const page of progress.pages ?? []) {
    const chip = document.createElement("li");
    chip.className = `${UI.pageChip.base} ${UI.pageChip[page.status] ?? UI.pageChip.pending}`;
    chip.textContent = page.cached ? `H${page.page}*` : `H${page.page}`;
    chip.title = `Halaman ${page.page}: ${page.status}${page.cached ? " (dari cache)" : ""}`;
    dom.pageList.append(chip);
  }
}

function buildMessage(entry, tone) {
  const item = document.createElement("li");
  item.className = tone === "error" ? UI.message.error : UI.message.warning;

  const head = document.createElement("p");
  head.className = tone === "error" ? UI.message.errorHead : UI.message.warningHead;
  const scope = entry.scope === "run" ? "seluruh run" : `halaman ${entry.page ?? "\u2013"}`;
  head.textContent = `${entry.code} \u00B7 ${scope}`;

  const body = document.createElement("p");
  body.className = tone === "error" ? UI.message.errorBody : UI.message.warningBody;
  body.textContent = entry.message;

  item.append(head, body);
  return item;
}

function renderMessages() {
  const hasErrors = state.errors.length > 0;
  const hasWarnings = state.warnings.length > 0;

  dom.errorsList.replaceChildren(...state.errors.map((entry) => buildMessage(entry, "error")));
  dom.warningsList.replaceChildren(
    ...state.warnings.map((entry) => buildMessage(entry, "warning")),
  );
  setHidden(dom.errorsBlock, !hasErrors);
  setHidden(dom.warningsBlock, !hasWarnings);
  setHidden(dom.messagesRegion, !hasErrors && !hasWarnings);
  dom.messagesRegion.classList.toggle(UI.layout.visible, hasErrors || hasWarnings);
}

function renderResult() {
  const result = state.run?.result ?? null;
  if (!result) {
    return;
  }
  const rendered = renderMarkdown(dom.markdownPane, result.markdown);
  if (rendered) {
    decorateReferenceMarkers(dom.markdownPane, result.references);
  }
  renderReferences(
    dom.referencesList,
    dom.referencesSummary,
    result.references,
    state.activeReferenceId,
  );
}

function metadataEntry(term, value) {
  const dt = document.createElement("dt");
  dt.className = UI.metadata.term;
  dt.textContent = term;
  const dd = document.createElement("dd");
  dd.className = UI.metadata.detail;
  dd.textContent = value;
  return [dt, dd];
}

function renderMetadata() {
  const metadata = state.run?.metadata ?? null;
  dom.metadataList.replaceChildren();
  if (!metadata) {
    const [dt, dd] = metadataEntry("Metadata", "Belum tersedia");
    dom.metadataList.append(dt, dd);
    return;
  }

  const usage = metadata.usage;
  // REQ-31: a provider that reports no usage must read "tidak tersedia", never 0.
  const usageText =
    usage && usage.available
      ? `${usage.input_tokens} masuk / ${usage.output_tokens} keluar`
      : "tidak tersedia";

  const validation = metadata.validation ?? {};
  const rows = [
    ["Provider", metadata.provider ?? "tidak tersedia"],
    ["Model", metadata.model ?? "tidak tersedia"],
    ["Durasi", formatDuration(metadata.duration_s)],
    ["Usage", usageText],
    ["Retry", String(metadata.retries ?? 0)],
    ["Cache hit", String(metadata.cache_hits ?? 0)],
    [
      "Halaman",
      `${metadata.pages_processed ?? 0} / ${metadata.pages_total ?? 0} diproses`,
    ],
    ["Skema valid", validation.schema_ok === true ? "ya" : "tidak"],
    ["Semua halaman", validation.all_pages_processed === true ? "ya" : "tidak"],
    ["Tanpa evidence", String(validation.items_without_evidence ?? 0)],
    ["Evidence tak terverifikasi", String(validation.evidence_unverifiable ?? 0)],
    ["Markdown valid", validation.markdown_format_ok === true ? "ya" : "tidak"],
  ];

  for (const [term, value] of rows) {
    const [dt, dd] = metadataEntry(term, value);
    dom.metadataList.append(dt, dd);
  }
}

function renderSummaryIfPresent() {
  const summary = state.run?.result?.summary;
  if (!summary) {
    return;
  }
  const parts = Object.entries(summary.items_by_status ?? {}).map(
    ([status, count]) => `${STATUS_LABEL[status] ?? status} ${count}`,
  );
  if (parts.length > 0) {
    dom.referencesSummary.textContent =
      `${summary.items_total} item \u00B7 ${parts.join(" \u00B7 ")}`;
  }
}

// ---------------------------------------------------------------- run lifecycle

function resetRunView() {
  state = {
    ...state,
    run: null,
    runState: "idle",
    progress: null,
    errors: [],
    warnings: [],
    activeReferenceId: null,
  };
  dom.markdownPane.replaceChildren();
  const title = document.createElement("p");
  title.className = "font-mono text-sm font-bold uppercase";
  title.textContent = "Belum ada hasil";
  const body = document.createElement("p");
  body.className = "mt-2 text-sm font-semibold";
  body.textContent = "Pilih berkas, isi instruksi, lalu jalankan ekstraksi.";
  dom.markdownPane.append(title, body);
  renderReferences(dom.referencesList, dom.referencesSummary, [], null);
  renderMetadata();
  renderRunState();
  renderProgress();
  renderMessages();
}

function applyRunResponse(payload) {
  const status = payload.status ?? "running";
  state = {
    ...state,
    run: payload,
    runState: status,
    progress: payload.progress ?? state.progress,
    errors: payload.errors ?? state.errors,
    warnings: payload.warnings ?? state.warnings,
    busy: !isTerminal(status),
  };

  renderRunState();
  renderProgress();
  renderMessages();

  if (isTerminal(status)) {
    renderResult();
    renderMetadata();
    if (payload.result?.summary) {
      renderSummaryIfPresent();
    }
    announce(
      status === "failed"
        ? "Run gagal. Lihat daftar error."
        : "Run selesai. Markdown dan referensi tersedia.",
    );
  }
  updateRunButton();
}

async function startRun() {
  const reason = blockingReason();
  if (reason) {
    showNotice(dom.fileError, reason);
    announce(reason);
    return;
  }

  stopPolling = true;
  resetRunView();
  state = { ...state, busy: true };
  updateRunButton();
  announce("Run dimulai. Menunggu status dari backend.");

  try {
    const created = await createRun({
      file: state.file,
      instructions: state.instructions,
      providerId: dom.provider.value,
      domainId: dom.domain.value,
      useCache: dom.optCache.checked,
      aggregate: dom.optAggregate.checked,
    });
    applyRunResponse({
      run_id: created.run_id,
      status: created.status,
      created_at: new Date().toISOString(),
      progress: null,
      result: null,
      errors: [],
      warnings: [],
    });
    await pollUntilTerminal(created.run_id);
  } catch (error) {
    handleApiError(error);
  }
}

async function pollUntilTerminal(runId) {
  stopPolling = false;
  while (!stopPolling) {
    try {
      const payload = await fetchRun(runId);
      applyRunResponse(payload);
      if (isTerminal(payload.status)) {
        return;
      }
    } catch (error) {
      handleApiError(error);
      return;
    }
  }
}

function handleApiError(error) {
  stopPolling = true;
  const known = error instanceof ApiError;
  const entry = {
    code: known ? error.code : "internal_error",
    scope: "run",
    page: null,
    message: known
      ? error.message
      : "Tidak dapat menghubungi backend. Periksa koneksi lalu coba lagi.",
  };
  state = {
    ...state,
    busy: false,
    runState: "failed",
    errors: [...state.errors, entry],
  };
  renderRunState();
  renderMessages();
  updateRunButton();
  announce(`Error: ${entry.message}`);
}

function resetAll() {
  stopPolling = true;
  dom.fileInput.value = "";
  dom.instructions.value = "";
  applyFile(null);
  syncInstructions();
  applyDomainDefault(dom.domain.value, true);
  state = { ...state, busy: false, errors: [], warnings: [] };
  resetRunView();
  announce("Formulir diatur ulang.");
}

function selectReference(id) {
  state = { ...state, activeReferenceId: state.activeReferenceId === id ? null : id };
  renderResult();
  const card = document.getElementById(`ref-${id}`);
  if (card) {
    card.scrollIntoView({ block: "nearest", behavior: "smooth" });
    card.setAttribute("tabindex", "-1");
    card.focus({ preventScroll: true });
  }
}



// ---------------------------------------------------------------- bootstrap

function populateSelect(select, entries, labelKey) {
  select.replaceChildren();
  for (const entry of entries) {
    const option = document.createElement("option");
    option.value = entry.id;
    option.textContent = entry[labelKey] ?? entry.id;
    if (entry.available === false) {
      option.textContent = `${option.textContent} \u2014 tidak tersedia`;
    }
    select.append(option);
  }
}

async function bootstrap() {
  resetRunView();

  try {
    const [providersPayload, domainsPayload] = await Promise.all([
      fetchProviders(),
      fetchDomains(),
    ]);

    state = {
      ...state,
      providers: providersPayload.providers,
      defaultProvider: providersPayload.default,
      domains: domainsPayload.domains,
    };

    populateSelect(dom.provider, providersPayload.providers, "label");
    if (providersPayload.default) {
      dom.provider.value = providersPayload.default;
    }
    populateSelect(dom.domain, domainsPayload.domains, "name");
    if (domainsPayload.domains.length > 0) {
      dom.domain.value = domainsPayload.domains[0].id;
    }

    renderProviderHelp();
    renderDomainHelp();
    applyDomainDefault(dom.domain.value, true);
  } catch (error) {
    handleApiError(error);
  }

  updateRunButton();
}

// ---------------------------------------------------------------- events

dom.fileInput.addEventListener("change", () => {
  applyFile(dom.fileInput.files?.[0] ?? null);
});

for (const eventName of ["dragenter", "dragover"]) {
  dom.dropzone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dom.dropzone.classList.add(UI.dropzone.active);
  });
}

for (const eventName of ["dragleave", "dragend"]) {
  dom.dropzone.addEventListener(eventName, () => {
    dom.dropzone.classList.remove(UI.dropzone.active);
  });
}

dom.dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dom.dropzone.classList.remove(UI.dropzone.active);
  const file = event.dataTransfer?.files?.[0] ?? null;
  if (file) {
    applyFile(file);
  }
});

dom.provider.addEventListener("change", () => {
  renderProviderHelp();
  updateRunButton();
});

dom.domain.addEventListener("change", () => {
  renderDomainHelp();
  applyDomainDefault(dom.domain.value, true);
});

dom.instructions.addEventListener("input", syncInstructions);

dom.optCache.addEventListener("change", () => {
  state = { ...state, useCache: dom.optCache.checked };
});

dom.optAggregate.addEventListener("change", () => {
  state = { ...state, aggregate: dom.optAggregate.checked };
});

dom.runButton.addEventListener("click", () => {
  startRun();
});

dom.resetButton.addEventListener("click", () => {
  resetAll();
});

dom.downloadButton.addEventListener("click", () => {
  const done = downloadMarkdown(state.run?.result?.markdown, state.file?.name);
  announce(done ? "Markdown diunduh." : "Tidak ada Markdown untuk diunduh.");
});

function selectReferenceFromEvent(event) {
  const marker = event.target.closest("[data-ref]");
  if (marker) {
    event.preventDefault();
    selectReference(marker.dataset.ref);
    return;
  }
  const link = event.target.closest("a[href^='#ref-']");
  if (link) {
    event.preventDefault();
    selectReference(link.getAttribute("href").slice("#ref-".length));
  }
}

dom.markdownPane.addEventListener("click", selectReferenceFromEvent);
dom.referencesList.addEventListener("click", selectReferenceFromEvent);

bootstrap();
