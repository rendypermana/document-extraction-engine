import puppeteer from "puppeteer-core";
import { writeFile, unlink } from "node:fs/promises";

const browser = await puppeteer.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
  args: ["--no-sandbox"],
});
const page = await browser.newPage();
page.on("pageerror", (e) => console.log(`[pageerror] ${e.message}`));
page.on("console", (m) => {
  if (m.type() === "error") console.log(`[console:error] ${m.text()}`);
});

await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle2" });
await new Promise((r) => setTimeout(r, 800));

console.log(
  "before upload:",
  JSON.stringify(
    await page.evaluate(() => ({
      runDisabled: document.getElementById("run-button").disabled,
      title: document.getElementById("run-button").title,
    })),
  ),
);

await writeFile("diag-sample.pdf", Buffer.from("%PDF-1.4\n%x\n%%EOF\n"));
await (await page.$("#file-input")).uploadFile("diag-sample.pdf");
await new Promise((r) => setTimeout(r, 500));

console.log(
  "after upload:",
  JSON.stringify(
    await page.evaluate(() => {
      const file = document.getElementById("file-input").files?.[0];
      return {
        fileName: file?.name ?? null,
        fileType: file?.type ?? null,
        fileSize: file?.size ?? null,
        fileState: document.getElementById("file-state").textContent.trim(),
        runDisabled: document.getElementById("run-button").disabled,
        title: document.getElementById("run-button").title,
        progressStage: document.getElementById("progress-stage").textContent.trim(),
        instructionsLen: document.getElementById("instructions").value.length,
      };
    }),
    null,
    2,
  ),
);

await page.click("#run-button");
await new Promise((r) => setTimeout(r, 7000));

console.log(
  "after run:",
  JSON.stringify(
    await page.evaluate(() => ({
      runState: document.getElementById("run-state").textContent.trim(),
      errors: document.getElementById("errors-list").textContent.trim(),
      progressCount: document.getElementById("progress-count").textContent.trim(),
      stage: document.getElementById("progress-stage").textContent.trim(),
    })),
    null,
    2,
  ),
);

await browser.close();
await unlink("diag-sample.pdf");
