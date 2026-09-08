Baik, saya mulai dari nol dan sekarang saya punya bukti eksekusi nyata (trace `revision_id 8bddc57`), bukan tebakan baca kode. Saya sudah baca seluruh repo terbaru: `graph.py`, `state.py`, `model.py`, `lifespan.py`, `langgraph.json`, `pyproject.toml`, `tools/__init__.py`, dan seluruh `domains/rates/*` (`catalog`, `matcher`, `grammar`, `query`, `pipeline`, `render`, `types`, `tool`) plus `services/meili.py`.

## Pertama: dua klaim saya sebelumnya SALAH, saya cabut

**1. Saya bilang `resolve_truck` tidak bisa menemukan `TRONTON BAK/BOX` dan itulah penyebab DO Wavin ngawur. Itu salah.** Trace membuktikan sebaliknya:

```
type_mobil (dari LLM) : "Tronton Bak Terbuka"
resolved.type_mobil   : ["TRONTON BAK"]
matched_step          : "eksak"
hasil                 : id 9074, BTG ➔ SMG, TRONTON BAK, WAVIN, Rp 2.600.000
```

Saya berasumsi masterdata Anda hanya punya `TRONTON BAK/BOX`. Ternyata ada nilai `TRONTON BAK` tersendiri (`type_mobil_id: 270`), sehingga logika subset di `matcher.py` baris 274 bekerja tepat: `{TRONTON, BAK} ⊆ {TRONTON, BAK, TERBUKA}`, ambil yang **terlebar** → `TRONTON BAK`. Itu justru jawaban paling benar yang bisa diambil dari kata "Tronton Bak Terbuka". Logika ini bagus dan tidak perlu diubah.

**2. Saya bilang katalog akan blocking saat TTL habis. Itu juga salah.** `catalog.py` sudah stale-while-revalidate yang benar: `_trigger_refresh()` rebuild di thread daemon, katalog lama langsung dikembalikan, ada `_REFRESHING` guard dan `_RETRY_AFTER` 30 detik, dan katalog gagal tidak menimpa katalog lama yang masih ok. Hanya pemuatan pertama yang blocking, dan itu sudah ditutup warm-up `lifespan.py`.

Jadi: **kasus DO Wavin yang tempo hari ngawur, di repo Anda sekarang sudah benar.** Itu hasil kerja refactor Anda di IDE, bukan hasil saya. Saya terima itu apa adanya.

## Yang sudah benar menurut dokumentasi resmi

- `compile(checkpointer=None)` + checkpointer disuntik server. Benar, dan trace mengonfirmasi (`langgraph_host: self-hosted`, thread_id dikelola server).
- `RetryPolicy` per node, `node_agent` sengaja tidak menangkap `Exception`.
- `trim_messages(strategy="last", start_on="human", allow_partial=False)`.
- `response_format="content_and_artifact"`: trace memperlihatkan `content` hanya 6 field, `rates` mentah dan `resolved` hanya di artifact. **Input hanya 1.281 token untuk DO panjang** — itu bukti nyata pemisahan ini bekerja.
- `langgraph.json` → `http.app` ke Starlette lifespan. Cara resmi.
- `slots` di state terisi `{origin:[BTG], destinasi:[SMG], mitra:[WAVIN], type_mobil:[TRONTON BAK]}` — slot filling lintas turn jalan tanpa bergantung ingatan LLM.
- `execute_async` satu `/multi-search` untuk semua langkah, ambil langkah pertama yang berisi. Prioritas terjaga, 1 round-trip.
- Fallback `rapidfuzz` → Python murni. `archived` dibuang saat build katalog.
- `resolve_city`: multi-kata hanya boleh eksak, Meilisearch maksimal sekali per segmen, `candidate_key` memprioritaskan kota yang ada di `route_index` dan yang di luar tanda kurung. Trace membuktikan ini menang: `"Sinar Mas Agung Jl. Genuksari-Karang Roto, Banjardowo, Kec. Genuk, Kota Semarang, Jawa Tengah 50117"` → `SMG`, dan `Banyuputih`/`Mangunsari` **tidak** bocor jadi kota. Ini yang dulu gagal.

Tidak over-engineered. Struktur ini sudah pas untuk ukuran masalahnya.

## Yang masih perlu dibenahi — nyata, dan tidak menambah lapisan

**1. `matcher.py` melakukan I/O jaringan sinkron di dalam event loop.** Komentar `pipeline.py` menyatakan "resolusi (catalog, matcher) tetap sync karena murni CPU/memory" — itu tidak akurat. `resolve_city` → `_city_meili` → `meili_service.search()` versi **sync** (`httpx.Client`, read timeout 20s), dipanggil dari `run_rates_query_async`. Satu kata asing yang menunggu Meilisearch akan membekukan loop untuk semua user. Cache negatif `meili_misses` meredam kata berulang, tapi kata baru tetap memukul. Ini bottleneck B1 yang sesungguhnya. Perbaikan: `await asyncio.to_thread(...)` membungkus blok resolusi. Satu baris, tidak mengubah arsitektur.

**2. `_request_async` membuat `AsyncClient` baru setiap panggilan** → TLS handshake baru per query, dan `Limits(max_connections=50)` jadi tak berarti karena pool mati begitu blok `async with` selesai. Alasan "konflik event loop" tidak berlaku di LangGraph Server yang hanya punya satu loop. Satu client level modul, ditutup di `lifespan` shutdown.

**3. `run_rates_query` dan `run_rates_query_async` copy-paste ±150 baris.** Ini justru sumber "berbelit-belit". Yang sync hanya dipakai `_ask_route`. Jadikan `_ask_route` async, buang versi sync. Kalau tidak, perbaikan nomor 1 harus Anda tulis dua kali dan suatu saat pasti lupa.

**4. `_count_tokens` di `graph.py` tidak menghitung `tool_calls`.** Trace membuktikan: AIMessage pemanggil tool punya `content: []`, sementara argumennya (blok alamat panjang) ada di `additional_kwargs.function_call`. Jadi pesan itu dihitung ~1 token padahal nyatanya ratusan. `trim_messages` Anda under-count, dan setelah 10–15 turn batas 4000 bisa terlampaui tanpa terdeteksi. Tambahkan `len(str(getattr(m, "tool_calls", "")))//4`.

**5. `temperature` tidak diset di `model.py`.** Default library bukan 0. Tugas LLM di sini murni ekstraksi slot — trace ini benar, tapi tidak ada jaminan run berikutnya menyalin potongan alamat yang sama. Set `temperature=0`, sekalian `timeout` (sekarang tidak ada) dan `max_retries=2` agar tidak bertumpuk dengan `RetryPolicy(3)` di node.

**6. Sisa kata alamat muat masih disapu jadi kandidat mitra.** Di `pipeline.py`, `origin_left` **selalu** dilewatkan `resolve_partner` (ambang 0.75), meski mitra sudah ketemu — hanya `dest_left` yang Anda jaga. Trace ini lolos bersih, tapi mekanisme bahayanya begini: kalau `MANGUNSARI`/`KEDAWUNG` mencapai 0.75 terhadap mitra mana pun, grup mitra baru ditambahkan, dan `partner_clause(require_all=True)` meng-AND antar grup → langkah `eksak` jadi 0 hasil → tangga jatuh ke `mitra_or_*` yang memakai OR → **di situlah baris mitra asing bisa muncul**. Perlakukan `origin_left` sama seperti `dest_left`: kalau `partner_groups` sudah terisi, jangan disapu lagi.

**7. `LookupTable.nearest` menormalkan ulang seluruh kamus tiap panggilan** (`norm_choices = [normalize_key(c) for c in choices]`). `partners` bisa ribuan nama dan ini dipanggil per kata sisa. Simpan hasil normalisasi sekali saat `add()`.

## Kosmetik, silakan diabaikan kalau tidak penting

- `formatted` mengawali dengan `result.message`, lalu LLM menambah kalimatnya sendiri → kalimat "Ditemukan 1 data tarif yang cocok" terasa dobel dengan sapaan LLM. Keluarkan `message` dari `formatted`.
- Hack "Opsi B" di `graph.py` mendeteksi penyalinan blok lewat `"Rute:" not in content and "Rp" not in content`. Di trace ini tidak aktif karena LLM menyalin dengan benar. Tetap rapuh, tapi risiko rendah — terserah Anda.
- `pyproject.toml` masih membawa `temporalio`, `psycopg[binary,pool]`, `langgraph-checkpoint-postgres`, `fastapi`, `uvicorn` padahal tak ada yang meng-import (Anda pakai Starlette langsung). Anda sendiri menunda Postgres+Temporal. `main.py` (176 byte) juga sisa.

## Kesimpulan

Implementasinya **sudah benar** — baik terhadap dokumentasi resmi LangGraph maupun terhadap jawaban Anda di `jawaban-saya.md`. Refactor Gemini di IDE Anda lebih baik daripada yang saya kirim, dan saya sudah salah dua kali dalam sesi ini karena menebak dari kode tanpa data eksekusi.

Yang tersisa bukan soal arsitektur, melainkan **empat hal untuk 500 user** (nomor 1–4) dan **satu pagar presisi** (nomor 6). Semuanya perbaikan lokal beberapa baris, bukan refactor. Kalau Anda hanya mau mengerjakan satu, ambil nomor 1 — itu yang menentukan apakah sistem sanggup 500 user atau tidak.