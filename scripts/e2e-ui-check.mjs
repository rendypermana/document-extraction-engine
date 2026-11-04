// Temporary end-to-end check of the UI preview in a real browser.
// Not part of the build and not shipped: it exists to prove the page works against
// the running container, and is deleted afterwards.
import puppeteer from "puppeteer-core";

const URL = process.env.PREVIEW_URL ?? "http://127.0.0.1:8000/";
const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const results = [];
function check(name, pass, detail) {
  results.push({ name, pass, detail: detail ?? "" });
  console.log(`${pass ? "PASS" : "FAIL"}  ${name}${detail ? ` — ${detail}` : ""}`);
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});

const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 1000 });

const consoleErrors = [];
const failedRequests = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(`pageerror: ${error.message}`));
page.on("requestfailed", (request) => failedRequests.push(request.url()));

await page.goto(URL, { waitUntil: "networkidle2" });

// 1. The demo notice is present and visible without scrolling.
const bannerText = await page.$eval("#demo-notice-title", (node) => node.textContent.trim());
const bannerBox = await (await page.$("#demo-notice-title")).boundingBox();
check("banner data contoh tampil", bannerText.length > 0 && bannerBox !== null, bannerText);

// 2. Providers and domains come from the adapter, not from the HTML.
const providerOptions = await page.$$eval("#provider-select option", (nodes) =>
  nodes.map((node) => node.value),
);
const domainOptions = await page.$$eval("#domain-select option", (nodes) =>
  nodes.map((node) => node.value),
);
check("provider terisi", providerOptions.length === 2, providerOptions.join(","));
check("domain terisi", domainOptions.length === 2, domainOptions.join(","));

// 3. The domain default fills the textarea on load.
const instructions = await page.$eval("#instructions", (node) => node.value);
check("instruksi bawaan terisi", instructions.length > 20, `${instructions.length} char`);

// 4. Run is blocked with no file, and explains why.
const disabledNoFile = await page.$eval("#run-button", (node) => node.disabled);
const reasonNoFile = await page.$eval("#run-button", (node) => node.title);
check("run terkunci tanpa berkas", disabledNoFile === true, reasonNoFile);


// 5. Upload a synthetic PDF through the real input element.
const fs = await import("node:fs/promises");
const tmpPdf = "e2e-sample.pdf";
await fs.writeFile(tmpPdf, Buffer.from("%PDF-1.4\n% preview fixture\n%%EOF\n"));
const input = await page.$("#file-input");
await input.uploadFile(tmpPdf);
await page.waitForFunction(
  () => document.getElementById("file-state").textContent.includes("siap"),
  { timeout: 5000 },
);
const fileState = await page.$eval("#file-state", (node) => node.textContent.trim());
const fileHint = await page.$eval("#file-hint", (node) => node.textContent.trim());
check("berkas diterima", fileState === "Berkas siap", fileHint);
check(
  "run aktif setelah berkas dipilih",
  !(await page.$eval("#run-button", (node) => node.disabled)),
);

// 6. Run the demo extraction and wait for a terminal state.
await page.click("#run-button");
await page.waitForFunction(
  () => {
    const text = document.getElementById("run-state").textContent.trim();
    return text.startsWith("Selesai") || text === "Gagal";
  },
  { timeout: 30000 },
);
const runState = await page.$eval("#run-state", (node) => node.textContent.trim());
check("status terminal tercapai", runState === "Selesai dengan peringatan", runState);

// 7. Markdown renders as HTML and contains no script.
const markdownHtml = await page.$eval("#markdown-pane", (node) => node.innerHTML);
check(
  "markdown ter-render",
  Boolean(await page.$("#markdown-pane table")) && Boolean(await page.$("#markdown-pane h1")),
);
check("tidak ada script di hasil", !/<script/i.test(markdownHtml));

// 8. References keep all three verification states, in words.
const referenceCount = await page.$$eval("#references-list li", (nodes) => nodes.length);
const referenceText = await page.$eval("#references-list", (node) => node.textContent);
check("referensi tampil", referenceCount === 6, `${referenceCount} kartu`);
check(
  "tiga status verifikasi dibedakan",
  referenceText.includes("TERVERIFIKASI") &&
    referenceText.includes("TIDAK DITEMUKAN") &&
    referenceText.includes("TIDAK DAPAT DIVERIFIKASI"),
);
check("status item uncertain dipertahankan", referenceText.includes("UNCERTAIN"));
check("estimasi ditandai", referenceText.includes("ESTIMASI"));

// 9. Errors and warnings are both visible.
const messages = await page.$eval("#messages-region", (node) => node.textContent);
check(
  "error dan peringatan terlihat",
  messages.includes("provider_invalid_response") &&
    messages.includes("evidence_not_verifiable"),
);

// 10. Metadata reports missing usage honestly, not as zero.
const metadata = await page.$eval("#metadata-list", (node) => node.textContent);
check("usage tidak tersedia ditandai", metadata.includes("tidak tersedia"));
check("validasi run tampil", metadata.includes("Semua halaman"));

// 11. The bar reflects reported pages, not elapsed time.
const progressCount = await page.$eval("#progress-count", (node) => node.textContent.trim());
const progressNow = await page.$eval("#progressbar", (node) =>
  node.getAttribute("aria-valuenow"),
);
check("progres dari laporan halaman", progressCount.startsWith("5 / 6"), progressCount);
check("aria-valuenow sesuai halaman", progressNow === "83", String(progressNow));


// 12. Download is enabled and produces a sanitized .md filename.
check("tombol unduh aktif", !(await page.$eval("#download-button", (node) => node.disabled)));
const downloadName = await page.evaluate(async () => {
  const module = await import("/js/api.js");
  return module.markdownDownloadName("laporan tahunan 2025 (final).pdf");
});
check("nama unduhan aman", downloadName === "laporan-tahunan-2025-final.md", downloadName);

// 13. Clicking a [S1] marker selects the matching reference card.
await page.click('#markdown-pane a[data-ref="S1"]');
await page.waitForFunction(
  () => document.getElementById("ref-S1")?.className.includes("bg-black"),
  { timeout: 3000 },
);
check("klik penanda memilih referensi", true, "S1 aktif");

// 14. Reset returns the form to its initial state.
await page.click("#reset-button");
await page.waitForFunction(
  () => document.getElementById("run-state").textContent.trim() === "Siap",
  { timeout: 3000 },
);
check(
  "atur ulang mengosongkan hasil",
  (await page.$eval("#references-list", (node) => node.textContent)).includes(
    "Tidak ada referensi",
  ),
);

// 15. No console errors, no failed requests, no third-party assets (REQ-55).
check("tanpa error konsol", consoleErrors.length === 0, consoleErrors.join(" | "));
check("tanpa request gagal", failedRequests.length === 0, failedRequests.join(" | "));
const thirdParty = await page.evaluate(() =>
  performance
    .getEntriesByType("resource")
    .map((entry) => entry.name)
    .filter((name) => !name.startsWith(location.origin)),
);
check("tanpa aset pihak ketiga", thirdParty.length === 0, thirdParty.join(" | "));

// 16. No horizontal overflow at a 390px mobile viewport.
await page.setViewport({ width: 390, height: 844 });
await new Promise((resolve) => setTimeout(resolve, 300));
const overflow = await page.evaluate(
  () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
);
check("tanpa overflow horizontal di mobile", overflow <= 1, `${overflow}px`);

await browser.close();
await fs.unlink(tmpPdf);

const failed = results.filter((item) => !item.pass);
console.log(`\n${results.length - failed.length}/${results.length} pemeriksaan lolos`);
process.exit(failed.length === 0 ? 0 : 1);
