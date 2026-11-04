// Copies the browser ESM builds of marked and DOMPurify into static/js/vendor/ so the
// app never loads them from a CDN (REQ-55, UI-04, SEC-01). Build-only: Node is not a
// runtime dependency, the server only ever serves the copied files.
import { copyFile, mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const vendorDir = join(projectRoot, "static", "js", "vendor");

const assets = [
  { from: "node_modules/marked/lib/marked.esm.js", to: "marked.esm.js" },
  { from: "node_modules/dompurify/dist/purify.es.mjs", to: "purify.es.mjs" },
];

await mkdir(vendorDir, { recursive: true });

for (const asset of assets) {
  await copyFile(join(projectRoot, asset.from), join(vendorDir, asset.to));
  console.log(`vendored ${asset.to}`);
}
