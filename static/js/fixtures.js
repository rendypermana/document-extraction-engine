// Sample payloads that match the wire format in docs/API.md §4, used only while
// the backend does not exist. Nothing here is a real extraction result: every
// number, quote and page reference below is invented for layout preview, and the
// UI states that in a persistent banner. Do not copy these values into an
// evaluation report or a README result table.
export const DEMO_PROVIDERS = Object.freeze({
  default: "fake",
  providers: [
    {
      id: "fake",
      label: "Fake (pengujian integrasi)",
      model: "fake-deterministic",
      available: true,
      unavailable_reason: null,
      capabilities: {
        vision: true,
        structured_output: true,
        max_image_pixels: null,
        max_input_tokens: null,
        reports_usage: false,
      },
    },
    {
      id: "gemini",
      label: "Gemini",
      model: "gemini-2.0-flash",
      available: false,
      unavailable_reason: "Kunci API belum dikonfigurasi.",
      capabilities: {
        vision: true,
        structured_output: true,
        max_image_pixels: null,
        max_input_tokens: null,
        reports_usage: true,
      },
    },
  ],
});

export const DEMO_DOMAINS = Object.freeze({
  domains: [
    {
      id: "research_paper",
      name: "Makalah riset",
      description: "Ekstraksi metode, hasil, tabel, dan chart.",
      default_instructions:
        "Ekstrak rumusan masalah, metode, tabel hasil utama beserta hierarki header, dan nilai chart. Tandai setiap nilai yang hanya terbaca secara visual sebagai estimasi.",
    },
    {
      id: "tax_form",
      name: "Form pajak",
      description: "Ekstraksi field dan checkbox form.",
      default_instructions:
        "Ekstrak seluruh field beserta nilainya, dan nyatakan setiap checkbox sebagai tercentang, kosong, atau tidak jelas. Jangan mengisi field yang tidak terbaca.",
    },
  ],
});

const DEMO_MARKDOWN = `# Hasil ekstraksi

Dokumen: **laporan-tahunan-2025.pdf** · 6 halaman · domain *Makalah riset* [S1]

## Ringkasan

Pendapatan bersih dilaporkan sebesar **Rp 42,7 miliar**, naik dari Rp 38,1 miliar pada periode sebelumnya [S1]. Pertumbuhan ini disebut berasal dari segmen layanan, bukan dari segmen produk [S2].

## Tabel 1 — Hasil per segmen

| Segmen | Pendapatan (miliar Rp) | Pertumbuhan |
|---|---|---|
| Layanan | 26,4 | +18,2% |
| Produk | 12,1 | +4,0% |
| Lisensi | 4,2 | *tidak terbaca* |

Sumber: Tabel 1, halaman 2 [S2]. Baris *Lisensi* ditandai tidak terbaca karena sel terpotong pada pemindaian.

## Grafik 1 — Pangsa pendapatan

- Layanan: 61,8% (estimasi) [S3]
- Produk: 28,3% (estimasi) [S3]
- Lisensi: 9,9% (estimasi) [S3]

Nilai grafik dibaca secara visual dan ditandai **estimasi**; angka pada tabel adalah sumber utama.

## Field form

- Nomor dokumen: \`TA-2025-0117\` — status OK [S4]
- Tanggal tanda tangan: kosong — status MISSING [S4]
- Persetujuan direksi: **tercentang** [S5]

## Catatan keterbatasan

> Halaman 4 gagal diproses sehingga isinya tidak masuk ke ringkasan. Nilai yang ditandai *uncertain* tidak boleh diperlakukan sebagai angka final [S6].
`;

export const DEMO_RUN = Object.freeze({
  run_id: "00000000-0000-4000-8000-00000000demo",
  status: "completed_with_warnings",
  created_at: "2026-11-04T08:00:00Z",
  finished_at: "2026-11-04T08:02:41Z",
  result: {
    markdown: DEMO_MARKDOWN,
    references: [
      {
        id: "S1",
        item_id: "item-0001",
        page: 1,
        bbox: [0.11, 0.22, 0.86, 0.31],
        excerpt: "Pendapatan bersih sebesar Rp 42,7 miliar pada periode laporan.",
        verified: true,
        item_status: "ok",
        is_estimate: false,
      },
      {
        id: "S2",
        item_id: "item-0004",
        page: 2,
        bbox: [0.09, 0.34, 0.92, 0.71],
        excerpt: "Tabel 1. Pendapatan per segmen (dalam miliar rupiah).",
        verified: true,
        item_status: "ok",
        is_estimate: false,
      },
      {
        id: "S3",
        item_id: "item-0009",
        page: 3,
        bbox: null,
        excerpt: "Grafik 1. Pangsa pendapatan per segmen.",
        verified: false,
        item_status: "uncertain",
        is_estimate: true,
      },
      {
        id: "S4",
        item_id: "item-0013",
        page: 5,
        bbox: null,
        excerpt: "Nomor dokumen TA-2025-0117",
        verified: null,
        item_status: "ok",
        is_estimate: false,
      },
      {
        id: "S5",
        item_id: "item-0015",
        page: 5,
        bbox: [0.62, 0.78, 0.7, 0.82],
        excerpt: "Persetujuan direksi",
        verified: true,
        item_status: "ok",
        is_estimate: false,
      },
      {
        id: "S6",
        item_id: "item-0018",
        page: 6,
        bbox: null,
        excerpt: "Halaman 4 tidak dapat diproses.",
        verified: null,
        item_status: "unreadable",
        is_estimate: false,
      },
    ],
    summary: {
      items_total: 21,
      items_by_status: { ok: 16, uncertain: 3, unreadable: 1, missing: 1 },
    },
  },
  metadata: {
    provider: "fake",
    model: "fake-deterministic",
    started_at: "2026-11-04T08:00:02Z",
    duration_s: 159.0,
    usage: { input_tokens: null, output_tokens: null, available: false },
    retries: 1,
    cache_hits: 2,
    pages_total: 6,
    pages_processed: 5,
    validation: {
      schema_ok: true,
      all_pages_processed: false,
      items_without_evidence: 0,
      evidence_unverifiable: 2,
      markdown_format_ok: true,
    },
  },
  errors: [
    {
      code: "provider_invalid_response",
      scope: "page",
      page: 4,
      message: "Respons model tidak sesuai schema setelah satu percobaan perbaikan.",
    },
  ],
  warnings: [
    {
      code: "evidence_not_verifiable",
      scope: "page",
      page: 5,
      message: "Kutipan tidak dapat diverifikasi otomatis pada halaman ini.",
    },
    {
      code: "bbox_out_of_bounds",
      scope: "page",
      page: 3,
      message: "Region referensi berada di luar batas halaman; bbox dibuang.",
    },
  ],
});

// Page timeline used to preview a progress sequence. Each entry is a state the
// backend is contractually allowed to report (docs/API.md §4.5), not a
// fabricated percentage: the bar is always pages_done / pages_total.
export const DEMO_PROGRESS_STEPS = Object.freeze([
  { stage: "loading", pages_total: 6, pages_done: 0, pages_failed: 0, pages: [] },
  {
    stage: "extracting",
    pages_total: 6,
    pages_done: 1,
    pages_failed: 0,
    pages: [
      { page: 1, status: "done", cached: false },
      { page: 2, status: "processing", cached: false },
      { page: 3, status: "pending", cached: false },
      { page: 4, status: "pending", cached: false },
      { page: 5, status: "pending", cached: false },
      { page: 6, status: "pending", cached: false },
    ],
  },
  {
    stage: "extracting",
    pages_total: 6,
    pages_done: 3,
    pages_failed: 1,
    pages: [
      { page: 1, status: "done", cached: false },
      { page: 2, status: "done", cached: true },
      { page: 3, status: "done", cached: true },
      { page: 4, status: "failed", cached: false },
      { page: 5, status: "processing", cached: false },
      { page: 6, status: "pending", cached: false },
    ],
  },
  {
    stage: "extracting",
    pages_total: 6,
    pages_done: 5,
    pages_failed: 1,
    pages: [
      { page: 1, status: "done", cached: false },
      { page: 2, status: "done", cached: true },
      { page: 3, status: "done", cached: true },
      { page: 4, status: "failed", cached: false },
      { page: 5, status: "done", cached: false },
      { page: 6, status: "done", cached: true },
    ],
  },
  {
    stage: "validating",
    pages_total: 6,
    pages_done: 5,
    pages_failed: 1,
    pages: [
      { page: 1, status: "done", cached: false },
      { page: 2, status: "done", cached: true },
      { page: 3, status: "done", cached: true },
      { page: 4, status: "failed", cached: false },
      { page: 5, status: "done", cached: false },
      { page: 6, status: "done", cached: true },
    ],
  },
]);

// Real HTTP error bodies from docs/API.md §6, rendered through the same code path
// a live backend response would take.
export const DEMO_HTTP_ERRORS = Object.freeze({
  file_too_large: {
    status: 413,
    body: {
      error: {
        code: "file_too_large",
        message: "Ukuran berkas melebihi batas yang dikonfigurasi.",
        details: { max_mb: 20 },
      },
    },
  },
  unsupported_file_type: {
    status: 415,
    body: {
      error: {
        code: "unsupported_file_type",
        message: "Tipe file tidak didukung. Gunakan PDF, PNG, atau JPG.",
        details: {
          received: "application/zip",
          supported: ["application/pdf", "image/png", "image/jpeg"],
        },
      },
    },
  },
});


export const DEMO_FILE = Object.freeze({
  name: "laporan-tahunan-2025.pdf",
  size: 1482112,
  mime: "application/pdf",
  pages: 6,
});
