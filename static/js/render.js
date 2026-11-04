// The only path from model text to the DOM: marked parses, DOMPurify sanitizes,
// and the result is assigned to an element. Never insert unsanitized HTML
// (REQ-42, REQ-53, SEC-01, SEC-02).
//
// Both libraries are served from static/js/vendor, copied there at build time, so
// the page makes no third-party request (REQ-55, UI-04).
import { Marked } from "./vendor/marked.esm.js";
import DOMPurify from "./vendor/purify.es.mjs";

const marked = new Marked({
  gfm: true,
  breaks: false,
  headerIds: false,
  mangle: false,
});

// Explicit allowlist instead of DOMPurify defaults: the output is Markdown, so it
// never needs styles, images with remote sources, or form controls.
const SANITIZE_CONFIG = Object.freeze({
  ALLOWED_TAGS: [
    "p", "br", "hr", "strong", "em", "del", "code", "pre", "blockquote",
    "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "table", "thead", "tbody", "tr", "th", "td", "a", "span",
  ],
  ALLOWED_ATTR: ["href", "title", "colspan", "rowspan", "scope"],
  ALLOW_DATA_ATTR: false,
  FORBID_TAGS: ["style", "script", "iframe", "object", "embed", "form", "input", "img"],
  FORBID_ATTR: ["style", "srcset", "onerror", "onload"],
  // Relative links are meaningless inside a rendered result pane.
  ALLOW_UNKNOWN_PROTOCOLS: false,
});

export function renderMarkdown(container, markdownText) {
  if (typeof markdownText !== "string" || markdownText.trim() === "") {
    container.replaceChildren();
    return false;
  }
  const parsed = marked.parse(markdownText);
  container.innerHTML = DOMPurify.sanitize(parsed, SANITIZE_CONFIG);
  return true;
}

export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  const rounded = exponent === 0 ? String(Math.round(value)) : value.toFixed(1);
  return `${rounded} ${units[exponent]}`;
}

export function formatDuration(seconds) {
  if (!Number.isFinite(seconds)) {
    return "unavailable";
  }
  if (seconds < 60) {
    return `${seconds.toFixed(1)} seconds`;
  }
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  return `${minutes} min ${rest} sec`;
}
