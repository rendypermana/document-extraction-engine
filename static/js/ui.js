// Single source for every Tailwind class string that is applied at runtime.
// Classes are complete literals so the Tailwind scanner can discover them; a
// runtime-built name like `text-${status}` would silently vanish from the build.
export const UI = Object.freeze({
  layout: Object.freeze({
    visible: "flex",
    hidden: "hidden",
  }),
  badge: Object.freeze({
    base: "inline-flex shrink-0 items-center border-2 border-black px-2 py-1 font-mono text-xs font-black uppercase tracking-[0.1em]",
    normal: "bg-white text-black",
    inverted: "bg-black text-white",
    invertedDashed: "border-dashed bg-black text-white",
  }),
  pageChip: Object.freeze({
    base: "inline-flex min-w-11 items-center justify-center border-2 border-black px-2 py-1 font-mono text-xs font-black uppercase",
    pending: "bg-white text-black",
    processing: "border-dashed bg-white text-black",
    done: "bg-black text-white",
    failed: "border-dashed bg-white text-black line-through",
  }),
  reference: Object.freeze({
    item: "border-[3px] border-black p-4",
    itemTarget: "border-[3px] border-black bg-black p-4 text-white",
    header: "flex flex-wrap items-center gap-2",
    id: "border-2 border-black bg-black px-2 py-1 font-mono text-xs font-black uppercase text-white",
    idTarget: "border-2 border-white bg-white px-2 py-1 font-mono text-xs font-black uppercase text-black",
    excerpt: "mt-3 border-l-4 border-current pl-3 font-mono text-sm leading-relaxed",
    meta: "mt-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs font-semibold uppercase",
    link: "underline decoration-2 underline-offset-4",
    button: "min-h-11 border-[3px] border-black bg-white px-3 py-2 font-mono text-xs font-black uppercase text-black shadow-brutal-sm transition-[transform,box-shadow] duration-150 hover:bg-black hover:text-white hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-black motion-reduce:transition-none motion-reduce:transform-none",
    buttonTarget:
      "min-h-11 border-[3px] border-white bg-white px-3 py-2 font-mono text-xs font-black uppercase text-black shadow-brutal-sm transition-[transform,box-shadow] duration-150 hover:bg-black hover:text-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white motion-reduce:transition-none motion-reduce:transform-none",
  }),
  message: Object.freeze({
    error: "border-[3px] border-black bg-black p-3 text-white",
    errorHead: "font-mono text-xs font-black uppercase tracking-[0.15em] text-white",
    errorBody: "mt-1 text-sm font-semibold text-white",
    warning: "border-[3px] border-black border-dashed bg-white p-3 text-black",
    warningHead: "font-mono text-xs font-black uppercase tracking-[0.15em] text-black",
    warningBody: "mt-1 text-sm font-semibold text-black",
    evidence: "mt-4 border-t-2 border-dashed border-black pt-3",
    evidenceTitle: "font-mono text-xs font-black uppercase tracking-[0.1em]",
    evidenceList: "mt-3 flex flex-col gap-3",
    evidenceLink: "font-mono text-xs font-black uppercase underline decoration-2 underline-offset-4",
    evidenceExcerpt: "mt-2 border-l-4 border-black pl-3 font-mono text-sm leading-relaxed",
  }),
  metadata: Object.freeze({
    term: "bg-white px-3 py-2 font-mono text-xs font-black uppercase tracking-[0.1em] text-black",
    detail: "bg-white px-3 py-2 font-mono text-sm font-semibold text-black",
  }),
  notice: Object.freeze({
    // Single tokens only: DOMTokenList rejects strings that contain spaces.
    hidden: "hidden",
    visible: "block",
  }),
  dropzone: Object.freeze({
    idle: "hover:bg-black",
    active: "bg-black text-white",
  }),
  inline: Object.freeze({
    invertedText: "text-white",
    normalText: "text-black",
  }),
});

// Status vocabulary is data, not styling. Never relabel these words.
export const STATUS_LABEL = Object.freeze({
  ok: "OK",
  uncertain: "UNCERTAIN",
  unreadable: "UNREADABLE",
  missing: "MISSING",
  failed: "FAILED",
  unknown: "UNKNOWN",
});

export const RUN_STATE_LABEL = Object.freeze({
  idle: "Ready",
  queued: "Queued",
  running: "Processing",
  completed: "Completed",
  completed_with_warnings: "Completed with warnings",
  failed: "Failed",
});

export const STAGE_LABEL = Object.freeze({
  loading: "loading document",
  extracting: "extracting pages",
  aggregating: "aggregating results",
  validating: "validating",
  rendering: "rendering Markdown",
});

export const VERIFIED_LABEL = Object.freeze({
  verified: "VERIFIED",
  notFound: "NOT FOUND",
  notVerifiable: "NOT VERIFIABLE",
});
