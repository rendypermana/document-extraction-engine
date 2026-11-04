# Document Extraction Engine

Repositori ini menggunakan dokumentasi di [`docs/`](docs/) sebagai **source of truth** untuk seluruh pekerjaan desain, implementasi, pengujian, dan review. Jangan mulai coding hanya berdasarkan asumsi, isi issue, atau kondisi kode saat ini.

## Aturan wajib sebelum coding

Untuk setiap tugas:

1. Baca [`docs/PLAN.md`](docs/PLAN.md) untuk memastikan milestone dan scope yang aktif.
2. Baca dokumen yang relevan dari matriks di bawah.
3. Periksa kode dan tes yang akan terdampak.
4. Bandingkan rencana perubahan dengan seluruh kontrak terkait di `docs/`.
5. Jika ada pertentangan antara permintaan, dokumentasi, kode, atau tes, **hentikan implementasi dan minta klarifikasi**. Jangan memilih interpretasi sendiri dan jangan mengubah kontrak secara diam-diam.
6. Setelah perubahan selesai, periksa kembali dokumen terkait, jalankan verifikasi yang relevan, lalu perbarui dokumentasi apabila perubahan kontrak memang telah disetujui.

> Prinsip utama: kode harus mengikuti dokumentasi. Kondisi kode yang berbeda dari dokumentasi adalah konflik yang harus dilaporkan, bukan preseden untuk mengabaikan dokumentasi.

## Peta source of truth

| Dokumen | Menjadi acuan untuk |
|---|---|
| [`docs/SPEC.md`](docs/SPEC.md) | kebutuhan, perilaku produk, scope, dan batasan |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | struktur modul, tanggung jawab, aliran data, dan arah dependensi |
| [`docs/SCHEMAS.md`](docs/SCHEMAS.md) | model data, status, validasi, dan kontrak schema |
| [`docs/API.md`](docs/API.md) | endpoint, request/response, error, polling, dan integrasi UI |
| [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) | seluruh keputusan visual, interaksi, responsivitas, dan aksesibilitas frontend |
| [`docs/PROMPTS.md`](docs/PROMPTS.md) | komposisi prompt, keluaran model, domain guidance, dan prompt-injection defense |
| [`docs/TESTING.md`](docs/TESTING.md) | strategi tes, test matrix, perintah verifikasi, dan release gate |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | ground truth, metrik, prosedur evaluasi, dan analisis kegagalan |
| [`docs/TECH_STACK_DECISIONS.md`](docs/TECH_STACK_DECISIONS.md) | pilihan teknologi dan alasan/trade-off di baliknya |
| [`docs/PLAN.md`](docs/PLAN.md) | milestone, urutan implementasi, dependensi, blocker, dan status pekerjaan |
| [`docs/AGENTS.md`](docs/AGENTS.md) | aturan kerja khusus untuk AI coding assistant |

Dokumen yang relevan harus dibaca **utuh**, bukan hanya judul atau cuplikannya. Perubahan frontend selalu wajib membaca `SPEC.md`, `ARCHITECTURE.md`, `API.md`, `SCHEMAS.md`, dan `DESIGN_SYSTEM.md` selain `PLAN.md`.

## Hierarki ketika sumber bertentangan

Gunakan urutan otoritas berikut:

1. Brief atau requirement asli yang disetujui pengguna.
2. `docs/SPEC.md`.
3. Schema aktual yang telah disetujui dan kontrak di `docs/SCHEMAS.md`.
4. `docs/ARCHITECTURE.md` dan `docs/API.md`.
5. Dokumen domain khusus yang relevan, seperti `docs/DESIGN_SYSTEM.md`, `docs/PROMPTS.md`, `docs/TESTING.md`, dan `docs/EVALUATION.md`.
6. `docs/TECH_STACK_DECISIONS.md` sebagai catatan alasan keputusan.
7. `docs/PLAN.md` sebagai status dan urutan kerja.

Hierarki ini membantu menemukan sumber konflik, tetapi **tidak memberikan izin untuk menyelesaikan konflik secara sepihak**. Laporkan dokumen/bagian yang bertentangan, dampaknya, dan keputusan yang diperlukan.

## Checklist pemeriksaan konflik

Sebelum menulis kode:

- [ ] Tugas berada dalam milestone aktif dan tidak melampaui scope.
- [ ] Perilaku yang diminta sesuai dengan `SPEC.md`.
- [ ] Penempatan kode dan dependensi sesuai dengan `ARCHITECTURE.md`.
- [ ] Model data dan status sesuai dengan `SCHEMAS.md`.
- [ ] Endpoint dan payload sesuai dengan `API.md`.
- [ ] Perubahan UI sesuai dengan seluruh release gate di `DESIGN_SYSTEM.md`.
- [ ] Prompt, evaluasi, dan tes mengikuti dokumen domain masing-masing.
- [ ] Tidak ada kontradiksi antara dokumentasi, kode, tes, dan permintaan pengguna.

Sebelum menyatakan pekerjaan selesai:

- [ ] Tes dan pemeriksaan kualitas yang relevan telah dijalankan.
- [ ] Perubahan telah dibandingkan ulang dengan dokumen terkait.
- [ ] Tidak ada kontrak publik yang berubah tanpa persetujuan dan pembaruan dokumentasi.
- [ ] Keterbatasan, konflik, atau verifikasi yang belum dapat dilakukan dilaporkan dengan jujur.
- [ ] `docs/PLAN.md` diperbarui bila status milestone atau pekerjaan berubah.

## Aturan untuk perubahan dokumentasi

- Jangan mengubah dokumentasi hanya untuk membenarkan implementasi yang sudah terlanjur berbeda.
- Perubahan requirement atau kontrak harus disetujui terlebih dahulu, lalu diperbarui pada semua dokumen yang terdampak.
- Hindari menduplikasi detail panjang ke README ini. Detail normatif tetap berada di dokumen pemilik domain dalam `docs/`.
- Jika suatu keputusan belum terdokumentasi, tandai sebagai keputusan terbuka dan minta arahan sebelum mengimplementasikannya.

## Format laporan setelah mengerjakan tugas

Setiap hasil pekerjaan minimal menyebutkan:

1. file dan perilaku yang berubah;
2. dokumen source of truth yang diperiksa;
3. tes atau verifikasi yang dijalankan beserta hasilnya;
4. konflik, asumsi, keterbatasan, atau bagian yang belum diverifikasi.

