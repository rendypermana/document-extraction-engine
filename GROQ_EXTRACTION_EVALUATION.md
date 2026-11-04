# Catatan Ekstraksi Dokumen dengan Groq

**Tanggal pengujian:** 4 November 2026  
**Provider/model:** Groq — `openai/gpt-oss-120b`  
**Instruksi:** `Extract all readable content: prose, tables, charts, and form fields.`  
**Domain:** Umum  
**Vision:** Tidak aktif  
**Structured output:** Aktif

## Ringkasan

PDF CV `Rendy_Permana_CV_2026.pdf` (119.498 byte, 2 halaman) berhasil dimuat aplikasi. Text layer lokal tersedia pada kedua halaman (2.343 karakter di halaman 1 dan 1.972 karakter di halaman 2).

Dua run melalui aplikasi selesai dengan status `completed_with_warnings`, tetapi keduanya hanya memproses halaman 1. Halaman 2 gagal dengan `provider_rate_limit` (`Groq rate limit exceeded`). Percobaan kedua dilakukan dengan permintaan halaman yang diserialkan; hasilnya tetap sama. Karena itu, **pemrosesan seluruh halaman PDF belum terpenuhi**. Keberhasilan satu halaman tidak boleh dianggap sebagai ekstraksi PDF penuh.

| Run | Status | Halaman selesai | Halaman gagal | Temuan |
|---|---|---:|---:|---|
| `33252e17-191c-4123-9a1d-d5cee708490f` | `completed_with_warnings` | 1/2 | 1 | Halaman 2 terkena rate limit; satu excerpt halaman 1 tidak ditemukan pada text layer |
| `dd9fd449-c289-464b-96ac-750f5135d3f8` | `completed_with_warnings` | 1/2 | 1 | Halaman 2 terkena rate limit |

Model tidak menerima gambar (`vision=false`). Konfigurasi ini cocok untuk ekstraksi teks yang tersedia pada text layer, tetapi tidak dapat diandalkan untuk konten yang hanya tampak secara visual, seperti halaman scan atau chart berbasis gambar.

## Cakupan Required Scope

| Kebutuhan | Hasil |
|---|---|
| PDF | CV PDF berhasil dimuat; hasil ekstraksi Groq hanya mencakup halaman 1 dari 2. |
| PNG/JPG | Loader aplikasi mendukung PNG/JPG, tetapi sampel gambar yang diwajibkan (`images.png`, form pajak) tidak tersedia di workspace saat pengujian dan belum dijalankan. |
| Kedua sampel brief | Belum terpenuhi. PDF CV bukan pengganti PDF riset 18 halaman; sampel PDF riset dan gambar form pajak belum diuji. |
| Seluruh halaman PDF | Belum terpenuhi karena halaman 2 gagal diproses akibat rate limit Groq. |
| Konten tidak terbaca/batasan | Dicatat di bawah. |

## Batasan dan Tindak Lanjut

- Ulangi pemrosesan PDF setelah kuota/rate limit Groq pulih, lalu pastikan status akhir menunjukkan **2/2 halaman selesai**. Simpan run ID dan hasil akhir sebagai bukti.
- Jalankan PDF riset 18 halaman dan gambar form pajak yang ditentukan brief; dokumentasikan jumlah halaman, halaman gagal, dan temuan yang benar-benar terlihat.
- Gunakan model vision untuk dokumen scan, chart, atau informasi yang hanya tersedia pada gambar. Model `openai/gpt-oss-120b` pada konfigurasi ini tidak menerima gambar.
- Satu excerpt pada run pertama dinyatakan tidak ditemukan pada text layer. Referensi tersebut perlu ditinjau sebelum menyatakan hasilnya terverifikasi.
- Belum dibuat ground truth manual untuk menghitung akurasi nilai atau kelengkapan ekstraksi.

## Hasil Ekstraksi yang Diberikan Pengguna

Bagian berikut mempertahankan teks hasil ekstraksi yang disampaikan pengguna. Isinya merujuk ke halaman 1 dan **belum diverifikasi ulang secara manual terhadap sumber**. Bagian ini bukan bukti bahwa run di atas memproses semua halaman.

# Hasil ekstraksi

## ABOUT ME

Full-Stack Developer with extensive experience building production-grade web platforms and AI-powered digital products. Experienced in developing end-to-end applications, integrating AI capabilities into real-world workflows, and building platforms powered by both external and self-hosted Large Language Models. Currently focused on AI-enabled product development, intelligent automation, social media intelligence, data-driven platforms, and reusable AI services. Combines strong full-stack engineering fundamentals with practical AI integration to transform complex business requirements into scalable, intuitive, and impactful digital products.
[S1]

## AREA OF EXPERTISE

AI & LLM Integration  
AI-Powered Product Engineering  
Scalable Full-Stack Development  
Automation & Intelligent Workflows  
Data Analytics & Visualization  
System Architecture & API Integration  
[S2]

## TECH STACK

Languages & Frameworks: TypeScript, JavaScript, Python, PHP, Node.js, Next.js, Vue.js, Nuxt.js, Angular, Laravel  
AI & LLM: vLLM, Ollama, OpenAI, Vertex AI, OpenRouter, Grok  
Databases: PostgreSQL, MySQL, SQLite  
Testing & Tools: Cypress, Mocha/Chai, Git, Linux Server  
[S3]

## PROFESSIONAL EXPERIENCE

Apr 2023 - Present  
Full-stack Developer | Mediawave

- Build and maintain AI-powered web applications across internal systems, client solutions, and commercial products, handling the full cycle from feature development and API integration to troubleshooting and performance improvements.
- Designed and developed an AI-powered Asset Management System using Next.js, PostgreSQL, MinIO, and self-hosted LLMs (Qwen, DeepSeek) served through vLLM.
- Developed a confidential Social Media Intelligence platform for a government client to monitor and analyze social media conversations and surface insights on organizations, topics, and emerging issues.
- Contribute to an internal AI Gateway that provides centralized AI capabilities and APIs for the MWX product ecosystem, and continuously enhance its AI-powered products for MSME/SME users.
- Collaborate with product, UI/UX, backend, AI, and business teams to turn business requirements into scalable, practical AI-enabled features.
[S4]

## Sumber

- [S1] Halaman 1 — dikutip pada hasil yang diberikan pengguna: deskripsi profil “Full-Stack Developer with extensive experience building production-grade web platforms and AI-powered digital products.”
- [S2] Halaman 1 — dikutip pada hasil yang diberikan pengguna: “AI & LLM Integration”.
- [S3] Halaman 1 — dikutip pada hasil yang diberikan pengguna: “Languages & Frameworks: TypeScript, JavaScript, Python, PHP, Node.js, Next.js, Vue.js, Nuxt.js,”.
- [S4] Halaman 1 — dikutip pada hasil yang diberikan pengguna: “Apr 2023 - Present / Full-stack Developer | Mediawave”.
