# Checklist Implementasi Backend

Dokumen ini memecah pekerjaan backend menjadi tujuh step yang dikerjakan **satu per satu**. Setiap step memiliki hasil dan pemeriksaan tersendiri. Setelah satu step selesai, hentikan pekerjaan dan laporkan hasil kepada pengguna; lanjut hanya setelah pengguna memberi instruksi untuk step berikutnya.

## Aturan pelaksanaan

- [ ] Kerjakan hanya satu step per instruksi pengguna.
- [ ] Sebelum implementasi, baca kontrak/dokumen yang relevan dan periksa kondisi kode aktual.
- [ ] Jika ditemukan konflik kontrak atau keputusan penting yang belum ditetapkan, hentikan bagian yang bergantung padanya dan minta klarifikasi.
- [ ] Jalankan pemeriksaan dan tes yang relevan; laporkan perintah serta hasil sebenarnya.
- [ ] Jangan menandai checklist selesai tanpa bukti verifikasi.
- [ ] Setelah step selesai, ringkas file/perilaku yang berubah, verifikasi, dan blocker. Minta konfirmasi pengguna sebelum step selanjutnya.
- [ ] Jangan membuat database permanen. Penyimpanan run direncanakan sementara di memori; file unggahan bersifat sementara.

## Step 1 — Audit dan baseline

**Tujuan:** memahami kondisi repo sebelum memilih implementasi.

- [ ] Inventaris kode aplikasi, UI, tes, dependensi, Docker/Compose, dan konfigurasi environment yang tersedia.
- [ ] Cocokkan kondisi aktual dengan `docs/PLAN.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/SCHEMAS.md`, dan `docs/TESTING.md`.
- [ ] Catat komponen backend yang sudah ada, belum ada, belum terverifikasi, serta kontradiksi atau blocker.
- [ ] Periksa perintah baseline yang tersedia dan jalankan pemeriksaan ringan yang relevan.

**Selesai bila:** baseline dan blocker dilaporkan dengan bukti aktual; belum ada klaim bahwa fitur backend yang belum ada telah selesai.

## Step 2 — Fondasi backend dan kontrak inti

**Tujuan:** menyiapkan tipe dan batas antar komponen.

- [x] Implementasikan konfigurasi aplikasi dari environment dengan nilai default yang sesuai kontrak.
- [x] Implementasikan schema Pydantic untuk model, evidence, status, run, metadata, dan response API sesuai dokumen.
- [x] Implementasikan interface provider/loader dan hierarki error bertipe.
- [x] Tambahkan tes schema, konfigurasi, dan batas impor yang relevan.

**Selesai bila:** kontrak inti dapat diimpor dan tes terarah lulus tanpa memerlukan provider live atau API key.

## Step 3 — Loader dan validasi dokumen

**Tujuan:** menerima PDF, PNG, dan JPG dengan penanganan input yang jelas.

- [x] Implementasikan loader PDF per halaman, termasuk gambar halaman dan text layer bila tersedia.
- [x] Implementasikan loader gambar PNG/JPG.
- [x] Validasi tipe dari konten, file kosong/rusak, ukuran unggahan, dan batas dimensi sesuai kontrak.
- [x] Pastikan koordinat evidence dinormalisasi sesuai schema.
- [x] Tambahkan tes untuk format valid, input rusak/tidak didukung, dan kasus batas.

**Selesai bila:** input valid menghasilkan representasi dokumen yang sesuai schema dan input tidak valid menghasilkan error eksplisit yang teruji.

## Step 4 — Pipeline offline dengan fake provider

**Tujuan:** menjalankan alur ekstraksi tanpa API key.

- [x] Siapkan pemuatan profil domain YAML dan penyusunan prompt dari template berversi sesuai kontrak.
- [x] Implementasikan fake provider deterministik melalui interface provider.
- [x] Implementasikan parse/validasi keluaran terstruktur, termasuk batas satu kali perbaikan bila diperlukan.
- [x] Implementasikan pemeriksaan evidence/status dan agregasi dasar tanpa menggabungkan hasil yang meragukan.
- [x] Implementasikan renderer Markdown dan referensi sumber dari data tervalidasi.
- [x] Tambahkan tes unit dan integrasi untuk alur sukses serta kegagalan parsial.

**Selesai bila:** pipeline offline menghasilkan Markdown, referensi, status, dan temuan yang dapat diuji; kegagalan satu halaman tidak diam-diam menghapus hasil halaman lain.

## Step 5 — Resiliensi dan provider live

**Tujuan:** membuat pemanggilan provider terukur dan menangani kegagalan secara terbatas.

- [x] Terapkan batas concurrency, timeout, retry/backoff terbatas, dan klasifikasi error sementara/permanen.
- [x] Catat model, durasi, retry, usage bila tersedia, dan keadaan ketika usage tidak tersedia.
- [x] Implementasikan adapter Gemini, OpenRouter, dan Groq sesuai konfigurasi dan kapabilitas model.
- [x] Pastikan rahasia tidak muncul pada pesan error; adapter memakai pesan aman tanpa body error provider.
- [x] Tambahkan tes resiliensi menggunakan fake/stub tanpa biaya atau ketergantungan jaringan.
- [ ] Lengkapi smoke test live provider; OpenRouter berhasil diuji dengan Gemini 3 Flash Preview, Gemini sebelumnya mendapat HTTP 404, dan Groq belum diuji live. Tes otomatis tetap memakai mock HTTP lokal.

**Selesai bila:** tes deterministik resiliensi lulus, error provider tampil eksplisit, dan hasil smoke live dilaporkan apa adanya tanpa klaim yang belum dibuktikan.

## Step 6 — API dan run store sementara

**Tujuan:** menyediakan kontrak HTTP untuk UI dan klien.

- [x] Implementasikan endpoint health, providers, domains, extract, status run, dan unduhan Markdown sesuai `docs/API.md`.
- [x] Simpan status dan hasil run dalam memori dengan lifecycle/TTL sesuai kontrak; jangan menambah database permanen.
- [x] Jalankan proses ekstraksi secara asinkron dan sediakan progres polling.
- [x] Terapkan validasi request, bentuk error HTTP yang konsisten, dan penghapusan file sementara.
- [x] Tambahkan tes kontrak API untuk sukses, input invalid, run berjalan/terminal, dan kegagalan parsial.

**Selesai bila:** API dapat menjalankan fake end-to-end, mengembalikan progres dan hasil yang sesuai kontrak, serta seluruh tes API terarah lulus. Cache halaman dan penggabungan tabel lintas halaman belum diterapkan; keduanya tercatat sebagai Should/pekerjaan lanjutan.

## Step 7 — Integrasi UI dan Docker

**Tujuan:** menjalankan aplikasi lengkap melalui Docker dan memverifikasi alur pengguna.

- [x] Hubungkan UI ke endpoint API; hapus atau batasi data contoh agar tidak disalahartikan sebagai hasil nyata.
- [x] Pastikan UI menampilkan status/progres, Markdown tersanitasi, referensi, error, dan unduhan.
- [x] Sambungkan konfigurasi `.env` melalui Compose tanpa memasukkan rahasia ke image/repo.
- [x] Pastikan build menyertakan aset UI lokal dan container menjalankan API serta UI pada satu origin sesuai arsitektur.
- [x] Verifikasi build/start Compose, health endpoint, UI di browser, dan satu alur ekstraksi fake.
- [x] Dokumentasikan URL lokal, konfigurasi, batasan, serta kebutuhan rebuild/restart bila relevan.

**Selesai bila:** satu perintah Compose memulai aplikasi lengkap; UI/API dan alur fake terverifikasi; hasil Docker dan keterbatasan yang tersisa dilaporkan.

## Log penyelesaian

| Step | Status | Bukti verifikasi / blocker | Konfirmasi untuk lanjut |
|---|---|---|---|
| 1. Audit dan baseline | Selesai; baseline awal terhambat dan kendala tes sudah terselesaikan | Catatan kondisi awal: paket `app/` hanya berisi kerangka `__init__.py`; UI Docker sehat di `http://localhost:8000`, tetapi `/api/health` mengembalikan HTTP 501. FastAPI sudah tercantum sebagai dependensi runtime proyek, tetapi FastAPI dan pytest belum terpasang di interpreter lokal saat audit sehingga baseline tes tidak dapat dijalankan; import package smoke lulus. Instruksi ada di `docs/AGENTS.md` (judul isi `CLAUDE.md`), yang terlewat saat pemeriksaan awal hanya mencari instruksi di root. Pembaruan setelah Step 6: `app/` kini memiliki implementasi backend/API; `python -m pytest -q` lulus (129 passed), begitu pula `ruff check .` dan `ruff format --check .`. Tes API memakai TestClient dan `/api/health` mengembalikan 200 di tes. Docker belum diverifikasi ulang; pemeriksaan Compose dan alur UI tetap menunggu Step 7. | Menunggu konfirmasi pengguna |
| 2. Fondasi backend dan kontrak inti | Selesai dan terverifikasi | `python -m pytest -q`: 19 passed. `ruff check .` lulus; `ruff format --check .` lulus. JSON Schema berhasil dibuat untuk 46 model Pydantic. | Menunggu konfirmasi pengguna |
| 3. Loader dan validasi dokumen | Selesai dan terverifikasi | `python -m pytest -q`: 31 passed. `ruff check .` dan `ruff format --check .` lulus. Tes mencakup PDF multipage/rotasi/tanpa text layer, PNG/JPG, EXIF orientation, batas piksel/ukuran, MIME/ekstensi, dan file korup. PDF menggunakan API `pymupdf` tanpa deprecation warning. | Menunggu konfirmasi pengguna |
| 4. Pipeline offline dengan fake provider | Selesai; evaluasi fuzzy masih tertunda | `python -m pytest -q`: 54 passed; `ruff check .` lulus; `ruff format --check .` lulus; Pydantic JSON Schema berhasil untuk 47 model. Pipeline memakai profil YAML, template prompt v1, fake provider, satu repair, validasi evidence/status, agregasi, dan renderer; tes menguji sukses, kegagalan parsial, autentikasi fatal, serta halaman tanpa vision. Evidence PDF dicocokkan secara exact setelah normalisasi whitespace/case; threshold fuzzy belum dikalibrasi karena sampel `e2e-sample.pdf` tidak dapat dibuka sebagai PDF dan sampel gambar tidak tersedia. | Dilanjutkan ke Step 5 atas persetujuan pengguna |
| 5. Resiliensi dan provider live | Adapter ditambahkan; smoke live OpenRouter berhasil, Groq belum diuji | `python -m pytest -q`: 107 passed; `ruff check .` dan `ruff format --check .` lulus; schema Pydantic 47 model berhasil. Pada 2026-11-04, tes live OpenRouter membaca `.env` lokal tanpa mencetak key, mengirim gambar sintetis dan JSON Schema ke `google/gemini-3-flash-preview`, lalu menerima JSON valid dengan transkripsi tepat `SMOKE-482` (2,65 detik; 1.142 token input, 12 output). Request dijalankan dari Python lokal, bukan dalam Docker; container Compose yang terverifikasi sehat saat itu hanya melayani UI. Gemini sebelumnya mendapat HTTP 404; Groq belum diuji live. Tes otomatis adapter tetap memakai `httpx.MockTransport`; panduan ada di `docs/PROVIDERS.md`. | Menunggu konfirmasi pengguna |
| 6. API dan run store sementara | Selesai dan terverifikasi | Implementasi `app/main.py` sebagai composition root, seluruh endpoint API pada `app/api/`, run store in-memory dengan TTL, batas jumlah run, progres polling, validasi input, error JSON konsisten, dan cleanup unggahan sementara. `python -m pytest -q`: 129 passed; `ruff check .`, `ruff format --check .`, dan `git diff --check` lulus. Tes kontrak mencakup PDF/PNG fake end-to-end, input invalid/corrupt/ukuran, provider/domain tidak valid, run queued/running/terminal, kegagalan halaman parsial dan auth, unduhan, TTL/eviction, serta redaksi key. Satu warning deprecation berasal dari pasangan Starlette TestClient/httpx. Cache dan penggabungan tabel belum diimplementasikan (Should). API belum disambungkan ke UI/Docker. | Menunggu konfirmasi pengguna |
| 7. Integrasi UI dan Docker | Selesai dan terverifikasi | `static/js/api.js` kini memakai fetch nyata ke `/api/providers`, `/api/domains`, `/api/extract`, dan `/api/runs/{id}`; polling berjarak 1 detik. Data demo dan server statis 501 dihapus. FastAPI menyajikan UI beserta aset pada satu origin. `Dockerfile` multi-stage membangun Tailwind/vendor secara lokal lalu menjalankan API pada runtime Python; `.dockerignore` mengecualikan `.env`, dan Compose memasok `.env` saat runtime. `npm run build`, `npm run test:ui` (5 passed), `python -m pytest -q` (130 passed), Ruff, format check, `docker compose config --quiet`, dan `git diff --check` lulus. `docker compose up --build -d` menghasilkan container healthy; `/api/health`, providers, domains, CSS dan JS merespons. UI browser menjalankan PDF sintetis dengan Fake hingga selesai (1/1 halaman), menampilkan Markdown/metadata dan berhasil mengunduh `.md`; berkas PDF invalid memunculkan error HTTP yang terlihat. Hasil Fake pada input valid ini kosong, sesuai batasan adapter uji; ini bukan evaluasi akurasi. Sampel asli/provider live tidak diuji ulang, dan cek visual responsif penuh tidak dilakukan. | Step 7 selesai; menunggu permintaan lanjutan |
