# Rekonstruksi Arsitektur — Changelog

Seluruh perubahan di bawah ini dieksekusi berdasarkan hasil review arsitektur.
Signature fungsi publik (`run_rates_query`, `resolve_city`, `resolve_route_side`,
`resolve_partner`, `resolve_truck`, `build_catalog`, `get_catalog`, dll.)
TIDAK berubah, sehingga test lama tetap hijau. ReAct dipertahankan;
Temporal/Postgres belum diaktifkan, tapi fondasinya disiapkan (`build_graph`
menerima checkpointer).

## Kritis

1. **Bug kardinalitas `sort_hits` disimetriskan** (`query.py`).
   Filter single/multi kini berlaku untuk KEDUA sisi (origin dan destinasi)
   dan KEDUA arah (query single menyaring multi-drop, query multi menyaring
   single). Fungsi baru `_match_cardinality` dengan fallback aman: jika
   kardinalitas yang diinginkan tidak ada di hasil, tidak ada penyaringan paksa.
2. **Meilisearch maksimal 1 panggilan per segmen** (`matcher.py`).
   Per-word fallback memakai `allow_meili=False`, sehingga alamat panjang tidak
   lagi memicu ledakan HTTP call. Ditambah cache negatif (`Catalog.meili_misses`)
   untuk kata yang sudah pasti gagal resolve.

## Sedang

3. **Tangga `kota_meili` diberi pagar validasi** (`matcher.py`): wajib lolos
   `_rankingScore >= 0.5` (via `showRankingScore`) atau cek kemiripan internal
   sebagai fallback — selaras dengan threshold ketat tangga lainnya.
4. **Renderer deterministik** (`render.py`, baru): blok `formatted` dirender
   Python dari data tool; LLM diinstruksikan mengutipnya persis (prompt baru
   di `model.py`). Angka tarif tidak pernah lagi melewati penulisan ulang LLM.
   Aturan DP & Uang Jalan jadi satu saklar: `RatesConfig.include_dp_uang_jalan`.
5. **Stale-while-revalidate untuk katalog** (`catalog.py`): katalog lama tetap
   melayani saat TTL habis, rebuild berjalan di background thread. Cooldown
   retry kegagalan jadi satu mekanisme (`_RETRY_AFTER`), menggantikan logika
   ganda `_LAST_FAILED_AT`.
6. **State & memori slot** (`state.py` baru, `graph.py`): `AgentState`
   menyimpan `slots` + `last_result` dari payload tool (`resolved`), disuntik
   ke prompt sebagai KONTEKS SLOT TERAKTUAL — jawaban singkat user ("dari
   semarang") tidak lagi kehilangan slot mitra dari turn sebelumnya.
7. **Pangkas riwayat pesan** (`graph.py`): `trim_messages` (20 pesan terakhir,
   `start_on="human"`) agar token & latensi tidak membengkak di thread panjang.
8. **`langgraph.json` diperbaiki** sesuai dokumen resmi: key `source` yang tidak
   terdokumentasi dihapus, `dependencies: ["."]` ditambahkan.
9. **TLS verify bisa dikonfigurasi** (`services/meili.py`, `directus.py`):
   default AMAN (verify aktif), `HTTP_VERIFY_TLS=false` hanya untuk darurat
   dengan warning keras di log. Warning urllib3 ikut diredam saat dimatikan.

## Minor

10. **Pesan error ke user digeneriskan** (`graph.py`); nama exception hanya di log.
11. **Dead code dihapus**: `get_model()` di `model.py`. Warning jelas saat
    `GOOGLE_API_KEY` kosong.
12. **`services/__init__.py` disimetriskan**: export directus + meili.
13. **Cache sorted skeleton** di `LookupTable.skeleton_keys` (menghilangkan
    `sorted()` ulang di setiap panggilan `nearest_skeleton`).
14. **`meili_service.search`** mendapat parameter `with_ranking_score`.

## Test

- Test lama: tidak diubah, diharapkan tetap hijau (signature publik stabil).
- `tests/test_query.py` (baru): 6 test offline untuk kardinalitas simetris,
  fallback aman, dan prioritas skor `sort_hits`.
- `tests/test_render.py` (baru): 5 test untuk renderer deterministik,
  format rupiah Indonesia, dan saklar DP/Uang Jalan.

## Cara verifikasi

```bash
uv run ruff check . && uv run ruff format .
uv run pytest -q -m "not live"   # unit test, tanpa jaringan
uv run pytest -q -m live         # korpus regresi, butuh .env terisi
```

## Catatan fondasi ke depan (belum diaktifkan sesuai permintaan)

- Produksi: `build_graph(checkpointer=PostgresSaver(...))`, `thread_id` = nomor WA.
- Domain baru (orders, invoice): tambah tool di `src/agent/tools/` + modul
  `src/agent/domains/<nama>/` mengikuti pola rates; topologi graf tidak berubah.
- Aksi tulis ke database nanti: gunakan `interrupt` (human-in-the-loop) untuk
  konfirmasi sebelum membuat order/invoice.
