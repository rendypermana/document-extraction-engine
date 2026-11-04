import puppeteer from "puppeteer-core";

const browser = await puppeteer.launch({
  executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  headless: true,
  args: ["--no-sandbox"],
});
const page = await browser.newPage();
page.on("pageerror", (e) => console.log(`[pageerror] ${e.message}`));
await page.goto("http://127.0.0.1:8000/", { waitUntil: "networkidle2" });

const probe = await page.evaluate(async () => {
  const api = await import("/js/api.js");
  const out = {};
  try {
    const providers = await api.fetchProviders();
    out.providers = providers.providers.length;
  } catch (error) {
    out.providersError = `${error.name}: ${error.message}`;
  }
  try {
    const created = await api.createRun({
      file: { name: "x.pdf", size: 100, type: "application/pdf" },
      instructions: "test",
      providerId: "fake",
      domainId: "research_paper",
      useCache: true,
      aggregate: true,
    });
    out.created = created;
  } catch (error) {
    out.createError = `${error.name}: ${error.message}\n${error.stack}`;
  }
  return out;
});
console.log(JSON.stringify(probe, null, 2));

if (probe.created?.run_id) {
  const polled = await page.evaluate(async (runId) => {
    const api = await import("/js/api.js");
    try {
      const payload = await api.fetchRun(runId);
      return { status: payload.status, hasProgress: Boolean(payload.progress) };
    } catch (error) {
      return { error: `${error.name}: ${error.message}\n${error.stack}` };
    }
  }, probe.created.run_id);
  console.log("fetchRun:", JSON.stringify(polled, null, 2));
}

await browser.close();
