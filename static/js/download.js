// Downloads the Markdown result the page already holds (REQ-45). The Blob path is
// what docs/API.md §5 step 5 prescribes for the UI, so no extra request is made.
import { markdownDownloadName } from "./api.js";

export function downloadMarkdown(markdownText, sourceName) {
  if (typeof markdownText !== "string" || markdownText.trim() === "") {
    return false;
  }
  const blob = new Blob([markdownText], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = markdownDownloadName(sourceName);
  anchor.rel = "noopener";
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  // Revoking immediately can cancel the download in some browsers; one tick is
  // enough for the click to be handled.
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 0);
  return true;
}
