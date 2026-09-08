Repo-nya publik dan struktur filenya sudah saya dapat. Sekarang saya baca isi file-nya satu per satu.

Semua file inti sudah terbaca. Sisa beberapa file + verifikasi ke dokumentasi resmi LangGraph.

Saya sudah membaca **seluruh 20 file** di repo Anda. Catatan teknis: sandbox saya tidak punya akses jaringan untuk `git clone`, jadi saya baca lewat GitHub API + raw file. Semua terbaca, termasuk `meili.py` dan `test_corpus.py` yang sempat gagal beberapa kali.

Saya juga sudah cek dokumentasi resmi LangGraph/LangChain untuk hal-hal yang saya klaim di bawah, terutama [referensi `langgraph.json`](https://docs.langchain.com/langsmith/cli), [persistence](https://docs.langchain.com/oss/python/langgraph/persistence), dan [custom auth](https://docs.langchain.com/langsmith/custom-auth).

Satu hal yang perlu saya sampaikan di depan: **kode Anda jauh di atas rata-rata proyek LangGraph pemula.** Saya tidak mengatakan itu untuk menyenangkan Anda — saya akan tunjukkan spesifiknya di bagian D1. Tapi ada beberapa hal yang akan benar-benar menggigit di 500 user, dan dua hal yang menurut saya blocker keamanan.

---

# A. Koreksi — hal yang salah atau akan gagal

### A1. `pyproject.toml` merujuk `README.md` yang tidak ada

`readme = "README.md"`, tapi root repo hanya berisi `.gitignore`, `.python-version`, `langgraph.json`, `main.py`, `pyproject.toml`, `src/`, `tests/`, `uv.lock`.

`langgraph dev` lolos karena tidak mem-build package. `langgraph build` / `uv pip install .` akan gagal. Ini deterministik — buat README-nya.

### A2. Tidak ada `[build-system]`, padahal `langgraph.json` pakai `"dependencies": ["."]`

Dokumentasi CLI menyebut `"."` = "look for local Python packages" di direktori tempat `pyproject.toml` berada, dan sejak CLI v0.3 installer default adalah `uv pip`. Tanpa `[build-system]`, hasilnya tidak deterministik antar-versi tooling.

### A3. Tidak ada `src/__init__.py`, tapi semua impor pakai `from src.agent...`

Ini jalan sekarang berkat PEP 420 namespace package + `pythonpath = ["."]` di konfigurasi pytest. Tapi setuptools melihat direktori bernama `src/` dan menyimpulkan ini "src-layout" — ia akan memasang paketnya sebagai `agent.*`, bukan `src.agent.*`. Di dalam container, `from src.agent.model import SYSTEM_PROMPT` (`src/agent/graph.py` baris 11) bisa gagal.

Saya tidak bisa membuktikannya tanpa menjalankan build, jadi saya sebut ini **risiko tinggi yang harus Anda verifikasi**, bukan kepastian. Cara membuktikan: jalankan `langgraph build -t coba` lokal. Kalau gagal, pilih satu:

- **Src-layout beneran** (rekomendasi saya): hapus prefix `src.` dari semua impor → `from agent.model import ...`, tambahkan `[build-system]` + `[tool.setuptools] package-dir = {"" = "src"}`. Path di `langgraph.json` tetap `./src/agent/graph.py:graph`.
- Atau pindahkan `agent/` ke root repo.

Jangan setengah-setengah seperti sekarang.

### A4. Tujuh dependency terpasang tapi tidak dipakai sama sekali

Di `pyproject.toml`: `fastapi`, `uvicorn[standard]`, `temporalio`, `langchain-anthropic`, `langchain-openai`, `langgraph-checkpoint-postgres`, `psycopg[binary,pool]`.

`main.py` isinya hanya docstring. Tidak ada satu pun impor ke paket-paket itu di seluruh `src/`.

`temporalio` khususnya berat dan menarik banyak transitive dependency. Efeknya: image lebih besar, cold start lebih lambat, permukaan CVE lebih luas, `uv lock` lebih lama. Hapus sampai benar-benar dipakai.

Catatan jujur soal `langgraph-checkpoint-postgres` + `psycopg`: itu memang akan dipakai **kalau** Anda bikin server sendiri. Kalau pakai LangGraph Server, dokumentasi menyatakan eksplisit *"Agent Server handles persistence automatically"* — Anda tidak perlu paket itu di app.

### A5. `try/except Exception` di `node_agent` membunuh retry LangGraph

`src/agent/graph.py`:

```python
try:
    response = model_with_tools.invoke(messages)
except Exception:
    logger.exception("LLM invoke error")
    response = AIMessage(content="Maaf, sedang ada gangguan...")
```

Rate limit 429 dari Gemini, timeout transien, 503 — semuanya jadi "maaf ada gangguan" permanen untuk turn itu, padahal retry 1 detik kemudian akan berhasil.

LangGraph punya `RetryPolicy` di level node, tapi **hanya bekerja kalau exception keluar dari node**:

```python
from langgraph.pregel import RetryPolicy
workflow.add_node("agent", node_agent, retry_policy=RetryPolicy(max_attempts=3))
```

Buang try/except-nya, atau tangkap hanya error final (auth, 400) dan biarkan yang transien naik. Dengan 500 user, rate limit itu kejadian rutin — bukan pengecualian.

### A6. `_MAX_HISTORY = 20` memotong berdasarkan jumlah pesan, bukan token

`src/agent/graph.py`:

```python
trim_messages(messages, strategy="last", max_tokens=_MAX_HISTORY, token_counter=len, ...)
```

`token_counter=len` artinya tiap pesan dihitung 1. Jadi ini "simpan 20 pesan terakhir", bukan "20 token".

Masalahnya, isi `ToolMessage` Anda adalah JSON dari `split_tool_payload()` (`src/agent/domains/rates/types.py`) yang memuat `formatted` — 5 baris tarif × 7 field. Lalu jawaban AI mengutip blok yang sama persis lagi. Jadi tiap turn menambah blok tarif **dua kali** ke riwayat.

Perkiraan kasar (tolong perlakukan sebagai orde besaran, bukan angka pasti): ~6–8k token input per request. 500 user × ~10 pesan/hari ≈ 40 juta token input/hari. Di kelas flash-lite itu masih murah, tapi bukan nol, dan itu murni pemborosan.

Perbaikan: `token_counter=count_tokens_approximately` dari `langchain_core.messages.utils`, dengan `max_tokens` sungguhan (mis. 4000).

Tambahan: system prompt + schema tool Anda (~1,5k token) dikirim ulang tiap request. `gemini-3.5-flash-lite` mendukung context caching — layak dilihat.

### A7. `trim_messages` mengurangi prompt, tidak mengurangi state

Ini beda yang sering terlewat. `state["messages"]` **tetap tumbuh selamanya** di checkpointer. Dokumentasi persistence resmi menyebut ini eksplisit sebagai masalah umum ("Checkpoints growing unboundedly").

500 user × percakapan harian = tabel checkpoint Postgres membengkak tanpa batas. Dua perbaikan yang saling melengkapi:

- Di graph: buang pesan lama dari state dengan `RemoveMessage` / `REMOVE_ALL_MESSAGES` (`langgraph.graph.message`).
- Di `langgraph.json`: `"checkpointer": {"ttl": {"strategy": "delete", "default_ttl": 43200, "sweep_interval_minutes": 60}}`.

### A8. `AgentState` — field wajib tanpa default, tanpa reducer

`src/agent/state.py`:

```python
class AgentState(MessagesState):
    slots: dict[str, Any]
    last_result: dict[str, Any] | None
```

TypedDict default `total=True`, jadi kedua key ini secara tipe wajib — padahal di turn pertama tidak ada. Kode Anda aman karena selalu pakai `.get()`, tapi type checker akan protes dan `state["slots"]` di mana pun akan `KeyError`.

Perbaikan minimal: `slots: NotRequired[dict[str, Any]]`.

Yang lebih penting untuk masa depan: tanpa reducer, penulisan dari beberapa cabang paralel akan saling menimpa. Begitu Anda punya 2+ domain, siapkan `Annotated[dict, merge_slots]`.

### A9. `node_tools` menimpa `last_result` di dalam loop

`src/agent/graph.py`, loop `for message in result["messages"]`. Kalau LLM memanggil tool dua kali dalam satu AIMessage (Gemini bisa), hanya hasil terakhir yang tersimpan. Dan `prev_result = state.get("last_result")` masih nilai turn sebelumnya karena state belum ter-update di tengah node — jadi deteksi `is_clarification` bisa salah.

Belum kelihatan sekarang karena baru satu tool. Akan jadi bug halus begitu domain kedua masuk.

### A10. Tidak ada pengaman loop `agent ↔ tools`

`route_after_agent` tidak punya batas iterasi. Default `recursion_limit=25` LangGraph akan melempar `GraphRecursionError` yang tidak Anda tangani → user dapat error mentah.

### A11. Yang saya cek dan ternyata BENAR (supaya tidak Anda ubah percuma)

- **`gemini-3.5-flash-lite` itu model yang valid.** Stable, update Juli 2026, mendukung function calling. Saya sempat curiga typo, ternyata bukan. Tapi ini tier paling ringan — relevan untuk poin D7.
- **`graph = build_graph()` dengan `checkpointer=None` sudah tepat.** Docstring Anda benar: LangGraph Server mengelola persistence sendiri. Ini justru hal yang sering salah dilakukan orang.
- **`start_on="human"` + `allow_partial=False`** adalah kombinasi yang benar untuk mencegah `ToolMessage` yatim (yang bikin Gemini API error). Anda sudah pakai.
- **Escaping filter Meilisearch aman** — lihat C5.

---

# B. Arsitektur LangGraph untuk 500+ user

### B1. Semua node sync, semua HTTP client sync — ini bottleneck terbesar

`node_agent` dan `node_tools` di `src/agent/graph.py` adalah `def`, bukan `async def`. `httpx.Client` di `src/agent/services/meili.py` dan `directus.py` blocking.

LangGraph menjalankan node sync di thread pool dengan jumlah thread terbatas. Lalu perhatikan ini: satu request bisa memanggil Meilisearch **sampai 9 kali berurutan** — `build_steps()` di `src/agent/domains/rates/query.py` menghasilkan hingga 9 `QueryStep`, dan `execute()` menjalankannya satu per satu sampai ada hit.

Jadi satu user dengan hasil `not_found` menahan satu thread selama 9 × latensi Meili. Ditambah plafon keras `max_connections=50` (meili) dan `30` (directus).

Untuk 500 user konkuren, ini akan antre. Perbaikan: `async def` + `await model_with_tools.ainvoke(...)` + `await _tool_node.ainvoke(state)` + `httpx.AsyncClient`. Tool-nya juga jadi `async def` — decorator `@tool` LangChain mendukung coroutine.

Perubahan mekanis, dampaknya besar.

### B2. Belum ada streaming

`model.invoke()` bukan stream. Untuk chat, first-token-latency terasa. LangGraph Server sudah menyediakan `stream_mode="messages"` — tapi hanya berguna kalau node async dan tidak memblokir.

### B3. Dua panggilan LLM per pertanyaan, padahal bisa satu

Alur sekarang: `agent` (pilih tool) → `tools` → `agent` (tulis jawaban sambil mengutip `formatted`).

Padahal `src/agent/domains/rates/render.py` **sudah** menghasilkan blok jawaban final yang deterministik. Panggilan LLM kedua hanya membungkus dengan sapaan — dan itu justru sumber risiko: seluruh `## ATURAN DATA (PALING PENTING)` di `src/agent/model.py` ada untuk memaksa model tidak mengubah angka.

Pola LangGraph yang cocok — `Command` untuk lompat langsung ke END:

```python
from langgraph.types import Command
return Command(
    update={"messages": [tool_message, AIMessage(content=sapaan + formatted)]},
    goto=END,
)
```

Untungnya: −50% biaya LLM, −1 round-trip latensi, dan **0% kemungkinan angka rupiah diubah model**. Sapaan bervariasi tidak butuh LLM — cukup template berdasarkan jam + nama user.

Kalau Anda tetap mau LLM di akhir, minimal tambahkan validasi pasca-LLM: cek `formatted` tersalin utuh sebagai substring; kalau tidak, kirim `formatted` apa adanya.

Ini penting karena Anda mengirim angka uang ke client, dan `flash-lite` adalah tier paling ringan — kepatuhan instruksi "salin persis" tidak 100%.

### B4. `langgraph.json` masih konfigurasi dev minimal

Sekarang hanya `dependencies`, `graphs`, `env`. Berdasarkan referensi CLI resmi, menuju produksi tambahkan:

| Key | Kenapa |
| --- | --- |
| `"auth"` | **Wajib.** Lihat C1 |
| `"python_version": "3.11"` | Eksplisit, sinkron dengan `.python-version` |
| `"image_distro": "wolfi"` | Image lebih kecil & lebih aman |
| `"checkpointer": {"ttl": {...}}` | Lihat A7 |
| `"http": {"cors": {...}}` | Kalau diakses dari web client |
| `"store"` | Nanti, untuk memori lintas-thread (rute favorit user) |
| `"api_version"` | Pin versi server, hindari kejutan saat rebuild |

Dan `"env": ".env"` → di produksi ganti jadi env var container / secret manager, jangan file `.env` di image.

### B5. `langgraph dev` bukan runtime produksi

Ia in-memory dan single-process. Untuk 500 user, pilih **secara sadar**:

- **LangGraph Server via Docker** (`langgraph build` / `langgraph up`) + Postgres + Redis. Catatan jujur: dokumentasi CLI menyebut `langgraph up` butuh *"LangSmith API key for local dev; license for production"*. Cek implikasi biayanya sebelum berkomitmen.
- **Server sendiri**: FastAPI (sudah ada di dependencies) + `AsyncPostgresSaver`. Lebih murah, tapi Anda harus bangun sendiri: antrean run, streaming, cancel, penanganan double-texting, retry.

Untuk pengguna WhatsApp, "double-texting" (user kirim 3 pesan beruntun) itu nyata. LangGraph Server punya `multitask_strategy` (`reject` / `rollback` / `interrupt` / `enqueue`) yang menyelesaikan ini — kalau server sendiri, Anda yang harus menanganinya.

### B6. Belum ada observability

Saat ada yang lapor "tarifnya salah", Anda perlu bisa menelusuri: pesan user → slot yang diekstrak LLM → `matched_step` mana yang kena → filter Meili apa → baris mana yang terpilih.

Kabar baiknya, `matched_step` sudah ada di `PipelineResult` (`src/agent/domains/rates/types.py`) dan `EntityMatch` sudah menyimpan `strategy` + `score`. Infrastrukturnya sudah Anda siapkan — tinggal dikirim ke tracing (LangSmith) atau minimal ke structured log dengan `thread_id`.

### B7. Cold start katalog memblokir

`get_catalog()` di `src/agent/domains/rates/catalog.py`: panggilan pertama setelah proses hidup memuat **seluruh** dokumen `kode_destinasi` + **seluruh** ~7.000 baris `rates` (batch 1000 → ~8 round-trip) + synonyms, secara sinkron. User pertama setelah deploy menunggu semua itu.

Pola stale-while-revalidate Anda bagus untuk refresh berikutnya — tapi tidak menolong cold start. Panggil `get_catalog()` saat startup lewat custom lifespan (`http.app` di `langgraph.json`).

Catatan skala: kalau ada N replika, tiap proses punya `_CATALOG` sendiri → N× memori dan N× beban refresh ke Meili tiap 15 menit (`catalog_ttl_seconds = 900`). Untuk beberapa replika ini masih wajar, tapi sadari trade-off-nya.

### B8. Fuzzy matching murni Python = CPU-bound di thread yang melayani user

`src/agent/utils/text.py` — `levenshtein_distance()` implementasi manual O(n·m).
`src/agent/domains/rates/catalog.py` — `LookupTable.nearest()` scan **seluruh** nilai kanonik.
`src/agent/domains/rates/matcher.py` — `resolve_partner()`: kalau `prefix_candidates` kosong, fallback ke `cat.partners.values` (**semua mitra**), lalu tiap kandidat dihitung `partner_core_similarity()` yang sendirinya O(token_user × token_db) Levenshtein.

Data Anda punya `customer_id: 377` → ratusan sampai ribuan mitra. Kasus terburuk adalah nama mitra yang tidak dikenal — yang justru sering terjadi (lihat kasus `M-mitra-tidak-dikenal` di corpus Anda). Itu bisa ribuan Levenshtein per request, di thread yang sama yang melayani user.

Perbaikan: **`rapidfuzz`** (implementasi C++). `rapidfuzz.process.extract(..., score_cutoff=0.75)` dan `process.cdist` untuk batch. Ordo 50–100× lebih cepat. Satu dependency kecil yang menghapus satu kelas masalah skalabilitas — dan Anda sudah punya slot dependency kosong dari A4.

### B9. 9 langkah query = 9 HTTP call berurutan → bisa jadi 1

Meilisearch punya endpoint **`POST /multi-search`** yang menerima beberapa query sekaligus. Kirim semua langkah dari `build_steps()` dalam satu request, lalu ambil hasil dari langkah dengan prioritas tertinggi yang tidak kosong.

`src/agent/services/meili.py` sekarang hanya punya `search()` single-index — perlu ditambah `multi_search()`. Ini mungkin perbaikan latensi dengan rasio effort-to-impact terbaik di seluruh daftar ini.

### B10. Peluang penyederhanaan: pakai `destinasi_id`, bukan string origin+destinasi

Dari struktur Directus yang Anda kirim, `destinasi` itu **tabel rute**: `{id: 9, kode: "JTG", origin: "SMG", destinasi: "JKT"}`. Jadi `destinasi_id` di index Meili = ID rute, bukan ID kota. (Penamaannya menyesatkan — `rute_id` akan lebih jelas.)

Sekarang `query.py` memfilter `origin IN [...] AND destinasi IN [...]` dengan daftar string dari `route_index`. Kalau `destinasi_id` dijadikan filterable dan Anda bangun peta `(origin_key, dest_key) → [destinasi_id]`, filternya jadi satu klausa `destinasi_id IN [...]`. Lebih pendek, lebih cepat, dan menghapus seluruh kelas bug "urutan multi-kota" (`route_index` vs `route_index_sorted`).

**Jujur: ini usulan yang perlu Anda verifikasi dulu.** Kode Anda membaca index `kode_destinasi` lewat field `alamat_tujuan`/`alamat_lengkap`, sementara Directus punya `kode`/`origin`/`destinasi`. Sepertinya itu dua hal berbeda, dan saya tidak bisa mengecek isi index Anda dari sini.

---

# C. Keamanan & data — bagian paling serius

### C1. Tidak ada autentikasi sama sekali — blocker

`langgraph.json` tidak punya blok `auth`. LangGraph Server tanpa custom auth berarti siapa pun yang bisa menjangkau endpoint bisa membuat run **dan membaca thread milik user lain** — thread hanya dibedakan `thread_id`, dan ada endpoint `/threads/search`.

Untuk sistem yang Anda sebut "jembatan client dengan database internal", ini tidak bisa dinegosiasikan.

Yang perlu dibuat: `src/agent/auth.py` berisi instance `langgraph_sdk.Auth`:

```python
from langgraph_sdk import Auth
auth = Auth()

@auth.authenticate
async def authenticate(authorization: str | None):
    # verifikasi token (JWT sistem login Anda / token Directus)
    return {"identity": user_id, "divisi": divisi, "role": role}

@auth.on.threads
async def scope_threads(ctx, value):
    # user hanya melihat thread miliknya
    filters = {"owner": ctx.user.identity}
    metadata = value.setdefault("metadata", {})
    metadata.update(filters)
    return filters
```

Lalu daftarkan: `"auth": {"path": "./src/agent/auth.py:auth"}`.

Bonus penting: identitas terautentikasi otomatis masuk ke `config["configurable"]["langgraph_auth_user"]` — itu yang Anda butuhkan untuk C2 dan C3.

### C2. Tidak ada otorisasi data — semua user melihat semua tarif

Data Directus Anda punya `divisi: "Divisi Jawa Tengah"` dan `user_created`. Index Meili Anda **tidak memuat `divisi`**. Artinya sekarang mustahil membatasi jawaban per divisi.

Kalau "client" berarti customer eksternal, maka customer A **tidak boleh** bisa menanyakan tarif customer B. Sekarang bisa — cukup sebut nama mitra lain di chat.

Perbaikan:

1. Tambahkan `divisi` (dan `customer_id`) ke index rates sebagai filterable.
2. Ambil scope dari auth context.
3. **Inject filter itu ke `BASE_FILTER`** di `src/agent/domains/rates/query.py` — bukan sebagai parameter tool.

Poin ke-3 kritis: **jangan pernah biarkan LLM yang menentukan scope otorisasi.** Kalau scope jadi parameter tool, prompt injection bisa mengubahnya.

### C3. `render.py` membocorkan angka internal

`_format_item()` di `src/agent/domains/rates/render.py` menampilkan **Rate, DP, dan Uang jalan** ke semua orang. Di Directus bahkan ada `harga_dasar` dan `tagihan_mobil`.

`uang_jalan` dan `harga_dasar` adalah struktur biaya internal — itu margin Anda. Kalau penerima jawaban adalah client, ini kebocoran komersial langsung.

Perbaikan: satu set field per peran. Client → `rate` saja. Internal OPS → semuanya. Ditentukan dari auth, bukan dari prompt.

### C4. Verifikasi TLS dimatikan secara default di dua service

`src/agent/services/meili.py` dan `src/agent/services/directus.py`:

```python
enabled = os.getenv("HTTP_VERIFY_TLS", "false").strip().lower() in {"1","true","yes"}
```

Default `False`. Bearer token Meilisearch dan Directus dikirim lewat TLS yang tidak diverifikasi → rentan MITM, dan warning-nya sengaja dibungkam.

Saya menghargai bahwa komentar Anda jujur menjelaskan alasannya (SAN sertifikat belum mencakup subdomain). Tapi *default*-nya harus aman:

- Ganti default jadi `true`.
- Jalur yang benar: terbitkan sertifikat dengan SAN yang tepat (Let's Encrypt gratis), **atau** kalau Meili di jaringan privat yang sama, panggil lewat `http://` internal / nama service Docker — tidak perlu TLS sama sekali.
- Kalau memang harus custom CA: `verify="/path/ca.pem"`, bukan `verify=False`.

Detail kecil: kode meng-import `urllib3` untuk membungkam warning, padahal client-nya `httpx` yang **tidak memakai urllib3**. Jadi baris itu kemungkinan besar tidak melakukan apa-apa.

### C5. Filter injection — sudah aman, dan itu desain yang bagus

Saya cek khusus. `quote()` di `query.py` meng-escape `\` dan `"`. Tapi yang lebih penting: **semua nilai yang masuk filter berasal dari katalog** (`route_index`, `partners.values`, `trucks`), bukan dari string mentah user. String user tidak pernah menyentuh filter Meilisearch.

Ini pola yang benar. Pertahankan aturan ini saat menambah domain — tulis di README sebagai aturan arsitektur.

### C6. `status != "archived"` — tarif `draft` ikut ditampilkan sebagai harga final

`BASE_FILTER = 'status != "archived"'` di `src/agent/domains/rates/query.py`.

Contoh data yang Anda kirim sendiri berstatus `"draft"`. `sort_hits()` hanya memberi **+5 poin** untuk `published` — sementara kecocokan rute bernilai +40. Jadi baris draft dengan rute yang lebih cocok akan **mengalahkan** baris published.

Anda akan mengutip harga draft ke client sebagai harga final. Ini risiko bisnis, bukan risiko teknis.

Perbaikan: allowlist eksplisit `status = "published"`. Kalau draft memang perlu tampil, tandai di `render.py` — misal `(draft, belum final)`.

Terkait: `status_rate: "original"` ada di Directus tapi tidak di index Meili. Kalau ada nilai `revisi` atau `nego`, Anda tidak bisa membedakannya. Perlu dicek ke data asli.

---

# D. Domain rates — kualitas logika

### D1. Yang sudah bagus dan jangan diubah

Saya sebutkan spesifik supaya tidak terdengar basa-basi:

- **Pemisahan `grammar / matcher / catalog / query / pipeline / render / tool`.** Setiap file punya satu tanggung jawab, batasnya jelas. Ini yang membuat repo Anda bisa saya baca dalam sekali jalan.
- **Resolusi entitas dilakukan sebelum menyentuh filter.** LLM tidak pernah mengarang nama kota/mitra, dan tidak ada jalur injection.
- **`render.py` deterministik.** Angka rupiah tidak pernah ditulis LLM. Ini keputusan arsitektur yang tepat untuk data finansial.
- **`response_format="content_and_artifact"` + `split_tool_payload()`.** Data mentah masuk artifact, tidak dikirim ke model. Hemat token dan mengurangi permukaan halusinasi. Ini pemakaian LangChain yang benar dan tidak banyak orang tahu.
- **Slot persistence lewat state graph**, bukan mengandalkan ingatan LLM. Komentar Anda di `src/agent/state.py` menyebut ini eksplisit. Ini pemahaman LangGraph yang tepat.
- **`_MEILI_MIN_RANKING` / `_MEILI_MIN_SIMILARITY`** di `matcher.py` — Anda sudah sadar bahaya "hit pertama diterima mentah", dan komentarnya menjelaskan kenapa.
- **Cache negatif `meili_misses`** — kata yang sudah pasti gagal tidak ditanya ulang.
- **`tests/conftest.py`** yang mematikan jaringan untuk unit test, dengan komentar yang jujur: *"Tes lama tidak punya isolasi ini, sehingga sebuah tes bisa lulus justru ketika Meilisearch mati total."* Itu kesadaran testing yang bagus.

### D2. Ambang fuzzy hasil tuning manual, tanpa jaring pengaman

`matcher.py`: `_CITY_MIN_RATIO = 0.78`, `_CITY_MIN_SKELETON = 0.80`, `_PARTNER_MIN = 0.75`, `_TRUCK_MIN = 0.80`, `_PARTNER_BAND = 0.05`.

Angka ini pas untuk katalog **sekarang**. Saat masterdata tumbuh dan ada mitra baru yang namanya mirip mitra lama, 0.75 mulai salah — dan tidak ada mekanisme yang memberi tahu Anda saat itu terjadi.

Dua perbaikan:

1. Catat `strategy` + `score` tiap match ke tracing. Struktur `EntityMatch` sudah menyimpannya, tinggal dipakai. Pantau distribusinya.
2. Kalau skor tertinggi berada dalam `_PARTNER_BAND` dengan skor kedua, itu **kasus ambigu** — layak jadi `needs_clarification`, bukan diam-diam pilih yang pertama.

### D3. `resolve_truck()` bisa mengembalikan banyak tipe, dan semuanya diterima

Di `matcher.py`, cabang `superset` mengembalikan `sorted(superset)[:cfg.max_candidates]` — sampai 8 tipe. Lalu `query.py` memasukkan semuanya ke `type_mobil IN [...]`.

Contoh: user bilang "TRONTON". Katalog punya `TRONTON BAK`, `TRONTON BOX`, `TRONTON WING` → semuanya dianggap cocok, dan user bisa dapat harga tipe yang salah.

Yang menarik: corpus Anda punya kasus `T-wavin-logwin-marunda-tronton` dengan `type_mobil: "TRONTON"` — tapi `harap`-nya hanya memeriksa `row_id` dan `destinasi_mengandung`, **tidak memeriksa `type_mobil`**. Jadi kasus itu tidak menguji hal yang paling berisiko di dalamnya.

Perbaikan: >1 tipe hasil = `needs_clarification` dengan `options`, jangan tampilkan semua diam-diam.

### D4. `sort_hits()` menyembunyikan ambiguitas harga

`sort_hits()` mengurutkan, lalu `pipeline.py` memotong `[:cfg.max_display]` (5). Kalau dua baris punya skor identik (mitra sama, rute sama, armada sama — beda `id` saja), tie-break jatuh ke `id`.

Data Anda memang punya kembar semacam ini — lihat `RATE_ROWS` id 5 & 6 di `tests/conftest.py` (WAVIN, BTG→SMG, beda hanya `TRONTON BAK` vs `TRONTON BOX`).

Kalau ada >1 baris skor puncak sama tapi `rate` berbeda, itu sinyal masterdata bermasalah. Tampilkan semua secara eksplisit **dan** log-kan supaya tim data bisa membereskan sumbernya.

### D5. `_ask_route()` menawarkan opsi dari sampel, bukan dari populasi

Di `pipeline.py`, saat mitra dikenal tapi rute belum disebut, ia menjalankan langkah `mitra_saja` dengan `limit = cfg.search_limit = 60`, lalu:

```python
message = f"Mitra {nama} punya {outcome.estimated_total} data tarif..."
options = {"origin": asal[:10], "destinasi": tujuan[:10]}
```

`estimated_total` bisa 300, tapi `asal`/`tujuan` hanya diambil dari **60 hit pertama**. Jadi Anda bilang "punya 300 data" lalu menawarkan 10 kota yang kebetulan ada di 60 baris pertama. Bisa menyesatkan.

Perbaikan: pakai **facet** Meilisearch (`facets: ["origin", "destinasi"]`). Itu memberi distribusi lengkap tanpa menarik semua dokumen.

### D6. Deteksi multi-kota bergantung tanda baca mentah

Di `matcher.py`:

```python
has_dash = "-" in raw and not bool(re.search(r"[()]", raw))
```

Jadi `"Semarang - Jakarta"` (rute ditulis pakai strip, bukan multi-titik) akan dibaca sebagai multi-kota `SMG+JKT` di **satu sisi**.

Corpus Anda punya kasus `Q-liebra-cddl-wonogiri-cakung` dengan chat `"Rute: WONOGIRI - CAKUNG"` — tapi slot-nya sudah dipisah manual oleh penulis corpus (`origin: "WONOGIRI"`, `destinasi: "CAKUNG"`). Jadi corpus **tidak menguji** apakah LLM benar-benar memisahkannya. Ini contoh konkret dari D7.

### D7. Soal corpus — dan di sini saya harus paling jujur

`tests/test_corpus.py` memanggil:

```python
out = run_rates_query(**(case.get("slots") or {}))
```

**Slot-nya ditulis tangan di YAML, bukan dihasilkan LLM.**

Artinya corpus Anda menguji pipeline deterministik (grammar → matcher → query → render). Dan itu memang lulus — saya percaya Anda.

Tapi corpus **sama sekali tidak menguji bagian yang paling rapuh di produksi: apakah `gemini-3.5-flash-lite` benar-benar mengisi slot seperti itu.**

Seluruh instruksi ekstraksi Anda ada di docstring `tools_rates` (`src/agent/domains/rates/tool.py`, ~2,7 KB). Itu instruksi panjang dan bernuansa — "salin SELURUH blok alamat apa adanya", "nama kota sering berada di tengah/akhir alamat", "boleh tertukar dengan customer, backend yang mencocokkan", "JANGAN memasukkan tanggal, jam, nomor HP/WA, PIC, driver, nopol" — untuk model tier paling ringan.

Corpus Anda sendiri mengakui ini di field `chat`:

- `A-makmur-multikota-koma-dan`: *"LLM sering menulis ulang menjadi Tangerang, Bogor, dan Bekasi"*
- `F-slot-tertukar`: *"LLM menukar slot, customer=rapi dan expedisi=eds"*
- `K-nama-noise-diabaikan`: *"LLM salah mengambil Yuyun dari baris Note"*

Anda sudah membuat pipeline **tahan** terhadap kesalahan-kesalahan itu. Itu pertahanan yang benar dan saya menghargainya. Tapi Anda belum punya angka: **berapa persen pesan WA nyata yang slot-nya diekstrak dengan benar?**

Menurut saya ini gap terbesar antara "lulus tes" dan "siap 500 user". Semua perbaikan lain di dokumen ini bisa diukur; yang ini belum.

Yang perlu dibuat: **eval level-LLM.** Ambil 100–200 pesan WA asli, jalankan lewat model, bandingkan slot yang dihasilkan dengan slot yang benar. Bentuk paling sederhana: file YAML kedua `tests/corpus/extraction.yaml` berisi `chat` → `slots_harapan`, dengan runner yang memanggil model beneran (di-mark `live`). Kalau mau lebih serius, LangSmith punya dataset + evaluator untuk ini.

Angka itu juga yang akan memberi tahu Anda apakah `flash-lite` cukup, atau perlu naik ke `gemini-3.5-flash` untuk node ekstraksi.

### D8. Corpus memakai `row_id` — itu sebabnya cepat basi

```yaml
harap:
  status: success
  row_id: 6403
```

ID baris berubah saat masterdata di-import ulang. Anda sendiri bilang datanya kadang tidak ter-update — inilah mekanismenya.

Perbaikan: assert pada **invarian bisnis**, bukan ID:

```yaml
harap:
  status: success
  origin: "SMG"
  destinasi: "TGR+BGR+BKS"
  mitra: "MAKMUR TECHNOLOGY I"
  type_mobil: "CDD"
```

Itu tetap benar walau ID berubah, dan jauh lebih mudah dibaca saat gagal. Beberapa kasus Anda sudah pakai `destinasi_mengandung` — arah yang benar, tinggal dikonsistenkan.

### D9. Tidak ada CI

Tidak ada `.github/workflows/`. Padahal `test_korpus_valid` sudah sengaja dirancang jalan tanpa jaringan. Sayang tidak dijalankan otomatis:

```yaml
- run: uv sync --dev
- run: uv run ruff check
- run: uv run pytest -q -m "not live"
```

---

# E. Hal kecil tapi layak dibereskan

- **`main.py`** isinya hanya docstring tapi namanya menyiratkan entry point. Hapus atau pindahkan — file kosong di root membingungkan.
- **Tidak ada `README.md`.** Untuk proyek yang Anda pakai sambil belajar, dokumentasi alur `graph → tool → pipeline → matcher → query → render` akan sangat membantu Anda sendiri tiga bulan lagi.
- **`src/agent/model.py`**: `ChatGoogleGenerativeAI` tanpa `temperature`. Untuk ekstraksi slot, `temperature=0` mengurangi variasi yang tidak perlu. Juga belum ada `timeout` dan `max_retries` eksplisit.
- **`src/agent/model.py`** membuat instance model saat import. Kalau `GOOGLE_API_KEY` kosong hanya ada `logger.warning` — graph tetap ter-compile dan baru gagal saat request pertama. Untuk produksi, fail-fast saat startup lebih baik.
- **`.python-version`** — pastikan isinya sama dengan `python_version` di `langgraph.json`.
- **`_tool_payload()`** di `src/agent/graph.py` sekarang jalur mati (semua tool Anda pakai `content_and_artifact`). Tidak salah, tapi kode mati akan menipu Anda nanti.
- **`.gitignore`** sudah benar, dan komentarnya jujur soal pola lama yang tidak pernah cocok. Bagus.

---

# F. Prioritas — kalau saya jadi Anda

### Sebelum ada user selain Anda

1. Auth + otorisasi per divisi/customer — **C1, C2**
2. Sembunyikan `uang_jalan` / `dp` dari peran client — **C3**
3. `BASE_FILTER` → hanya `published` — **C6**
4. TLS verify default `true` + perbaiki sertifikat — **C4**
5. Packaging: README, build-system, layout `src`. Buktikan dengan `langgraph build` yang berhasil, bukan hanya `langgraph dev` — **A1, A2, A3**

### Sebelum 500 user

1. Node + service jadi async — **B1**
2. Meilisearch multi-search, 9 RTT → 1 — **B9**
3. `rapidfuzz` menggantikan Levenshtein manual — **B8**
4. Buang try/except yang menelan error, pasang `RetryPolicy` — **A5**
5. Trim berbasis token + `RemoveMessage` + `checkpointer.ttl` — **A6, A7**
6. Warm-up katalog saat startup — **B7**
7. Tracing/observability — **B6**
8. Putuskan runtime produksi secara sadar — **B5**
9. Hapus dependency yang tidak dipakai — **A4**

### Untuk kualitas jawaban

1. **Eval ekstraksi slot level-LLM dengan pesan WA nyata — D7.** Menurut saya ini yang paling menentukan apakah sistem ini dipercaya.
2. `Command(goto=END)` supaya blok tarif tidak pernah lewat LLM — **B3**
3. Assertion corpus dari `row_id` → invarian bisnis — **D8**
4. Ambiguitas armada & tarif kembar jadi `needs_clarification` — **D3, D4**
5. Facet untuk opsi rute — **D5**

### Sebelum domain kedua

1. Reducer state & `NotRequired` — **A8, A9**. Ini akan menggigit begitu ada dua tool.
2. Angkat pola `catalog / matcher / query / render` jadi kontrak yang bisa dipakai ulang (mis. protokol `DomainPipeline`), supaya domain berikutnya bukan copy-paste enam file.

---

## Penutup

Keputusan Anda menggarap `rates` duluan sebagai pondasi itu tepat — dan yang lebih penting, cara Anda menggarapnya (resolusi entitas deterministik, render di Python, artifact terpisah dari content) adalah pola yang akan tetap berguna di domain-domain berikutnya.

Yang menurut saya paling perlu berubah cara pandangnya cuma satu: **saat ini pipeline Anda yang teruji, bukan sistemnya.** Corpus membuktikan pipeline benar bila slot benar. Belum ada bukti seberapa sering slot itu benar di lapangan, dan belum ada pembatas siapa boleh melihat apa. Dua hal itu yang membedakan demo yang bagus dari sistem yang dipakai 500 orang.

Kalau mau, saya bisa buatkan salah satu dari ini:

- Halaman Notion berisi checklist prioritas di atas supaya bisa Anda centang sambil kerja
- Contoh konkret `src/agent/auth.py` + `langgraph.json` versi produksi
- Versi async dari `graph.py`, `meili.py`, `directus.py` sebagai patch

Tinggal bilang mau yang mana.