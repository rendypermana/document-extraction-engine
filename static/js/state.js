// Minimal application state. One object, replaced by assignment, so every render
// reads a consistent snapshot and no module keeps its own copy of the run.
export const RUN_STATUS_TERMINAL = Object.freeze([
  "completed",
  "completed_with_warnings",
  "failed",
]);

export function createInitialState() {
  return {
    mode: "demo",
    file: null,
    fileError: null,
    providers: [],
    defaultProvider: null,
    domains: [],
    domainId: null,
    instructions: "",
    instructionsError: null,
    useCache: true,
    aggregate: true,
    run: null,
    runState: "idle",
    progress: null,
    errors: [],
    warnings: [],
    activeReferenceId: null,
    busy: false,
  };
}

export function isTerminal(status) {
  return RUN_STATUS_TERMINAL.includes(status);
}

// A single place that decides whether the Run button may be pressed. Returning a
// reason lets the UI explain a disabled button instead of leaving it unexplained.
export function validateBeforeRun(state) {
  if (!state.file) {
    return "Pilih berkas PDF, PNG, atau JPG terlebih dahulu.";
  }
  if (state.instructions.trim().length === 0) {
    return "Instruksi ekstraksi tidak boleh kosong.";
  }
  if (state.instructions.length > 2000) {
    return "Instruksi melebihi batas 2000 karakter.";
  }
  return null;
}
