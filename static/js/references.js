// Source reference panel (REQ-43, REQ-47, UI-02).
//
// Every reference states page, verbatim excerpt and verification state in words.
// Three states stay distinct because docs/API.md §4.5 requires it:
//   verified: true  -> quote found in the text layer
//   verified: false -> quote not found; item is downgraded to `uncertain`
//   verified: null  -> cannot be verified automatically (image without text layer)
// A reference is never rendered as if it were verified when it is not.
import { STATUS_LABEL, UI, VERIFIED_LABEL } from "./ui.js";

function verificationBadge(reference, inverted) {
  const badge = document.createElement("span");
  if (reference.verified === true) {
    badge.className = `${UI.badge.base} ${inverted ? UI.badge.inverted : UI.badge.normal}`;
    badge.textContent = VERIFIED_LABEL.verified;
  } else if (reference.verified === false) {
    badge.className = `${UI.badge.base} ${UI.badge.invertedDashed}`;
    badge.textContent = VERIFIED_LABEL.notFound;
  } else {
    badge.className = `${UI.badge.base} ${UI.badge.normal}`;
    badge.textContent = VERIFIED_LABEL.notVerifiable;
  }
  return badge;
}

function statusBadge(status, inverted) {
  const badge = document.createElement("span");
  badge.className = `${UI.badge.base} ${inverted ? UI.badge.inverted : UI.badge.normal}`;
  badge.textContent = STATUS_LABEL[status] ?? STATUS_LABEL.unknown;
  return badge;
}

function formatBbox(bbox) {
  if (!Array.isArray(bbox) || bbox.length !== 4) {
    return "bbox: tidak tersedia";
  }
  return `bbox: ${bbox.map((value) => Number(value).toFixed(2)).join(", ")}`;
}

function buildReference(reference, isActive) {
  const item = document.createElement("li");
  item.id = `ref-${reference.id}`;
  item.className = isActive ? UI.reference.itemTarget : UI.reference.item;
  item.dataset.referenceId = reference.id;
  item.dataset.itemId = reference.item_id ?? "";

  const header = document.createElement("div");
  header.className = UI.reference.header;

  const idBadge = document.createElement("span");
  idBadge.className = isActive ? UI.reference.idTarget : UI.reference.id;
  idBadge.textContent = reference.id;

  header.append(idBadge, statusBadge(reference.item_status, isActive));
  header.append(verificationBadge(reference, isActive));

  if (reference.is_estimate) {
    const estimate = document.createElement("span");
    estimate.className = `${UI.badge.base} ${isActive ? UI.badge.inverted : UI.badge.normal}`;
    estimate.textContent = "ESTIMASI";
    header.append(estimate);
  }

  const excerpt = document.createElement("blockquote");
  excerpt.className = UI.reference.excerpt;
  // The excerpt is model output: textContent, never innerHTML.
  excerpt.textContent = `\u201C${reference.excerpt}\u201D`;

  const meta = document.createElement("p");
  meta.className = UI.reference.meta;
  meta.textContent = `Halaman ${reference.page} \u00B7 ${formatBbox(reference.bbox)} \u00B7 item ${reference.item_id}`;

  const link = document.createElement("a");
  link.className = UI.reference.link;
  link.href = `#ref-${reference.id}`;
  link.textContent = `Tautan ${reference.id}`;
  link.setAttribute("aria-label", `Tautan permanen ke referensi ${reference.id}`);

  meta.append(document.createTextNode(" \u00B7 "), link);
  item.append(header, excerpt, meta);
  return item;
}

export function renderReferences(list, summary, references, activeId) {
  list.replaceChildren();

  if (!Array.isArray(references) || references.length === 0) {
    const empty = document.createElement("li");
    empty.className = "border-[3px] border-dashed border-black p-4";
    const title = document.createElement("p");
    title.className = "font-mono text-xs font-black uppercase";
    title.textContent = "Tidak ada referensi";
    const body = document.createElement("p");
    body.className = "mt-2 text-sm font-semibold";
    body.textContent = "Referensi muncul setelah run selesai.";
    empty.append(title, body);
    list.append(empty);
    summary.textContent = "0 referensi";
    return;
  }

  const verified = references.filter((item) => item.verified === true).length;
  const unverified = references.filter((item) => item.verified === false).length;
  const unverifiable = references.filter((item) => item.verified === null).length;
  summary.textContent =
    `${references.length} referensi \u00B7 ${verified} terverifikasi` +
    ` \u00B7 ${unverified} tidak ditemukan \u00B7 ${unverifiable} tidak dapat diverifikasi`;

  for (const reference of references) {
    list.append(buildReference(reference, reference.id === activeId));
  }
}

// Clicking a [S1] marker inside the rendered Markdown selects the matching card.
// One listener on the container, not one per marker.
export function attachMarkdownReferenceLinks(container, onSelect) {
  container.addEventListener("click", (event) => {
    const target = event.target.closest("[data-ref]");
    if (!target) {
      return;
    }
    event.preventDefault();
    onSelect(target.dataset.ref);
  });
}

// Turns literal [S1] text produced by the model into selectable markers, but only
// for ids that actually exist in `references`. Text content is split and rebuilt
// from text nodes, so no HTML string is ever parsed here.
export function decorateReferenceMarkers(container, references) {
  if (!Array.isArray(references) || references.length === 0) {
    return;
  }
  const knownIds = new Set(references.map((reference) => reference.id));
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (node.parentElement?.closest("[data-ref]")) {
      continue;
    }
    if (/\[S\d+\]/.test(node.nodeValue ?? "")) {
      textNodes.push(node);
    }
  }

  for (const node of textNodes) {
    const text = node.nodeValue ?? "";
    const fragment = document.createDocumentFragment();
    const pattern = /\[(S\d+)\]/g;
    let cursor = 0;
    let match = pattern.exec(text);
    while (match !== null) {
      if (match.index > cursor) {
        fragment.append(document.createTextNode(text.slice(cursor, match.index)));
      }
      const id = match[1];
      if (knownIds.has(id)) {
        const marker = document.createElement("a");
        marker.href = `#ref-${id}`;
        marker.dataset.ref = id;
        marker.className =
          "border-2 border-black px-1 font-mono text-xs font-black no-underline hover:bg-black hover:text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-black";
        marker.textContent = id;
        marker.setAttribute("aria-label", `Lihat referensi ${id}`);
        fragment.append(marker);
      } else {
        fragment.append(document.createTextNode(match[0]));
      }
      cursor = pattern.lastIndex;
      match = pattern.exec(text);
    }
    if (cursor < text.length) {
      fragment.append(document.createTextNode(text.slice(cursor)));
    }
    node.parentNode?.replaceChild(fragment, node);
  }
}

