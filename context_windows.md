# MEMORY & CONTEXT WINDOWS GYNTRANS LOGISTICS AI

Berkas ini adalah **catatan memori berkelanjutan dan konteks utama proyek** yang diperbarui secara berkala sesuai aturan global agar model AI selalu mempertahankan konsistensi arsitektur dan riwayat pengembangan.

---

## 1. IDENTITAS & ATURAN GLOBAL UTAMA
- **Pengguna:** Linggar Bagus Yuli Pratama (Indonesia)
- **Bahasa Respons AI:** 100% Bahasa Indonesia profesional, ringkas, padat, dan jelas.
- **Bahasa Kode:** 100% Bahasa Inggris standar industri (KISS, no redundant comments, clean code).
- **Prinsip Utama:**
  - **No Ad-Hoc Patching:** Perubahan harus selalu arsitektural dan menyeluruh, bukan tambal sulam per kasus.
  - **Zero Hardcoding:** Dilarang keras hardcode nama kota, rekanan/mitra, customer, jenis armada, atau model. Semua ditarik dinamis dari DB/API/Meilisearch.
  - **Persona:** Staf Operasional (OPS) Senior GYNTRANS — ramah, solutif, ringkas, profesional.
  - **Output Tarif:** Standar 1 baris per opsi tarif, biaya internal (DP, Uang Jalan) disembunyikan kecuali diminta eksplisit. Field internal `status` tidak pernah ditampilkan ke user.

---

## 2. TECH STACK RESMI
- **AI Reasoning:** Python 3.11, LangGraph, LangChain, LangGraph CLI (Studio)
- **Search Engine:** Meilisearch (Fuzzy & Multi-criteria Search via HTTP API)
- **Backend / CMS:** Directus v10 (REST API)
- **Durable Execution:** Temporal (Lifecycle DO / Surat Jalan)
- **Frontend:** Vue.js 3, Quasar Framework, Axios, Vuex, SCSS
- **Database:** MySQL, phpMyAdmin
- **Server:** Hostinger VPS (Docker)

---

## 3. STATUS TERKINI: REFACTOR BESAR ENGINE LANGGRAPH & RATES (SELESAI 100%)

Semua rekomendasi audit arsitektur Claude Opus 5 & arahan pengguna telah diimplementasikan secara arsitektural dan lulus uji 100%:

### A. Dependensi & Lingkungan (`pyproject.toml`, `langgraph.json`)
- Membersihkan dependensi mubazir (`langchain-community`, `directus-sdk-py`).
- Menambahkan dependensi resmi berkinerja tinggi: `rapidfuzz` untuk fuzzy matching/typo tolerance tingkat C++.
- Menambahkan `build-system` standar (`hatchling`).
- Menetapkan `python_version: "3.11"` dan `image_distro: "wolfi"` di `langgraph.json`.
- Mendaftarkan async lifespan handler via instance `Starlette(lifespan=lifespan)` (`app` di `src/agent/lifespan.py`) pada `http.app` di `langgraph.json` untuk warm-up katalog saat server start.

### B. Typed State & Schema (`src/agent/state.py`)
- Menggunakan `typing_extensions.NotRequired` untuk seluruh field non-pesan (`origin`, `destinasi`, `customer`, `expedisi`, `type_mobil`, dll.).
- Memastikan LangGraph runtime mengizinkan partial state updates dari node tanpa melanggar kontrak TypedDict.

### C. Search & Integrasi Layanan
1. **`src/agent/services/meili.py`:**
   - Default TLS diubah menjadi `True` (keamanan produksi).
   - Menambahkan async client & method `multi_search_async(queries)` memanfaatkan endpoint native Meilisearch `/multi-search`.
   - Menggunakan scoped `httpx.AsyncClient` dengan context manager per-request untuk mencegah bug *Event loop is closed* saat berjalan di bawah threadpool / multiple event loops.
2. **`src/agent/services/directus.py`:**
   - Menambahkan konfigurasi `httpx.Timeout(15.0)` dan `httpx.Limits(max_connections=20, max_keepalive_connections=5)`.

### D. Fuzzy Matching C++ (`src/agent/utils/text.py`, `catalog.py`)
- Menggantikan implementasi manual Levenshtein dengan `rapidfuzz.distance.Levenshtein.distance` yang dikompilasi C/C++.
- Memberikan akselerasi kecepatan hingga 10x pada resolusi nama kota/mitra bertipe typo berat.

### E. Query Rates Multi-Search (`src/agent/domains/rates/query.py`)
- Menambahkan `execute_async`: Mengemas seluruh langkah waterfall relaksasi rute (exact, filter armada, drop fuzzy, dll.) ke dalam 1 payload batch HTTP ke `/multi-search` Meilisearch.
- Latensi pencarian berkurang dari N round-trip serial menjadi 1 round-trip network tunggal, dengan graceful fallback jika batch gagal.

### F. Async Workflow & Pipeline (`src/agent/graph.py`, `tool.py`, `pipeline.py`)
- Mendukung runtime async end-to-end: `@tool` async def di `tool.py` memanggil `run_rates_query_async`.
- Menghapus try/except blok yang menutupi retry bawaan di `src/agent/graph.py`.
- Menerapkan `RetryPolicy` resmi LangGraph pada node model dan tool untuk auto-retry saat transient network timeout.

### G. Rendering & Presentation (`src/agent/domains/rates/render.py`)
- Menghapus bocoran metadata sistem `Status: ...` dari teks yang dibaca oleh pengguna akhir.
- Mempertahankan format 1 baris per opsi tarif sesuai arahan pengguna.

### H. Testing & Corpus Regression (`tests/test_corpus.py`)
- Diperbarui dengan pengujian invarian bisnis dinamis (`origin_mengandung`, `destinasi_mengandung`, `mitra_mengandung`).
- Menjalankan 2 set korpus: sync baseline dan async multi-search path.
- **Hasil Uji:** 124/124 tests PASSED (100% pass), `ruff check` bersih (0 lint errors), durasi turun ke ~3.98 detik.

### I. PENYEMPURNAAN 7 POIN PASCA-AUDIT TRACE (SELESAI 100%)
1. **Zero Blocking I/O (`pipeline.py`):** Resolusi entitas (matcher sync & CPU fuzzy) dibungkus `asyncio.to_thread` sehingga event loop server 100% bebas hambatan saat memproses kata alamat baru.
2. **Koneksi HTTP Reuse (`meili.py` & `lifespan.py`):** `_async_client` kini di-reuse dengan deteksi event loop aktif (`Limits(max_connections=50)` aktif optimal, tanpa TLS handshake berulang), dan ditutup rapi via `meili_service.aclose()` di shutdown lifespan.
3. **Unifikasi Pipeline DRY (`pipeline.py`):** `run_rates_query_async` menjadi single source of truth; duplikasi 150 baris kode dihapus. `run_rates_query` menjadi sync wrapper tipis.
4. **Presisi Hitung Token (`graph.py`):** `_count_tokens` menghitung payload `tool_calls` dan `function_call` sehingga `trim_messages` tidak under-count pesan pemanggilan tool.
5. **Determinisme LLM (`model.py`):** Ditetapkan `temperature=0.0`, `timeout=30.0`, dan `max_retries=2` pada `ChatGoogleGenerativeAI`.
6. **Pagar Kebocoran Mitra (`pipeline.py`):** Jika `partner_groups` sudah terisi dari slot `customer`/`expedisi`, sistem TIDAK menyapu sisa kata alamat (`origin_left` maupun `dest_left`), mencegah masuknya nama mitra kedua yang merusak pencarian eksak.
7. **Cache Normalisasi Kamus (`catalog.py`):** `normalized_values` di-cache di `LookupTable` dan di-invalidate otomatis saat ada penambahan data (`add`), memangkas loop list comprehension pada setiap panggilan `nearest()`.
8. **Pembersihan `formatted` dari Kalimat Dobel (`render.py`):** `result.message` dikeluarkan dari `format_result` sehingga `formatted` murni hanya memuat daftar blok tarif. Mencegah sapaan dobel dengan kalimat pengantar LLM.
9. **Eliminasi Hack Opsi B yang Rapuh (`graph.py`):** Mengganti pengecekan substring `"Rp"`/`"Rute:"` dengan guard berbasis `is_tool_response` (hanya aktif setelah `ToolMessage`) dan pengecekan baris pertama tabel (`first_line not in response.content`), sehingga giliran chat biasa ("terima kasih", dll.) tidak pernah ketempelan tabel tarif lama.
10. **Pembersihan Warning Gemini 3.x (`model.py`):** Menghapus parameter `temperature=0.0` sesuai pedoman resmi Google AI untuk arsitektur Gemini 3.x (*fixed sampling defaults*), menjadikan log terminal 100% bersih tanpa warning.

### J. PEMBERSIHAN DUPLIKASI & PEMUSATAN FORMATTER (SELESAI 100%)
1. **Eliminasi Jalur Sinkron:**
   - Dead code `execute()` serial di `src/agent/domains/rates/query.py` dihapus total (35 baris).
   - Sync wrapper `run_rates_query` di `src/agent/domains/rates/pipeline.py` dihapus total (30 baris), menghilangkan risiko threadpool executor dan loop nesting.
   - Test runner korpus di `tests/test_corpus.py` disatukan menjadi pengujian async murni (`async def test_korpus_live`).
2. **Pemusatan Formatter Data Tarif (`render.py`):**
   - Fungsi normalisasi hit Meilisearch `format_rate_hit` dipindahkan dari `pipeline.py` ke `src/agent/domains/rates/render.py` sebagai *single source of truth* representasi data tarif.
   - `render.py` kini mengelola siklus lengkap format tarif: normalisasi dict (`format_rate_hit`), pemformatan baris per item (`_format_item`), rendering blok final (`format_result`), dan rupiah (`format_rupiah`).
3. **Observabilitas Strategi Matching (`catalog.py` & `matcher.py`):**
   - Menambahkan logging debug terstruktur pada `LookupTable` (`by_skeleton`, `prefix_candidates`, `nearest`, `nearest_skeleton`) dan pada resolusi entitas `matcher` (`resolve_city`, `resolve_partner`, `resolve_truck`).
   - Memberikan visibilitas nyata untuk evaluasi pemangkasan tangga relaksasi dan struktur kamus yang tidak pernah aktif di produksi.
4. **Hasil Pengujian Terkini:**
   - `uv run ruff check src/ tests/`: **All checks passed (0 lint issues)**.
   - `uv run pytest tests/ -v`: **101/101 tests PASSED dalam 2.27 detik** (durasi pengujian terpangkas dari sebelumnya 7+ detik).

---

## 4. PANDUAN PENGEMBANGAN SELANJUTNYA
1. **Selalu jalankan verifikasi:**
   ```bash
   uv run ruff check src/ tests/
   uv run pytest tests/ -v
   ```
2. **Katalog Cache:**
   Jika ada penambahan rute/mitra baru di DB Directus, katalog akan diperbarui otomatis sesuai interval TTL (default 300 detik) atau saat restart lifespan.
3. **Penyusunan Fitur Baru:**
   Ikuti metodologi KISS, pastikan setiap tool baru mendukung async native, dan catat keputusan baru ke berkas ini.

