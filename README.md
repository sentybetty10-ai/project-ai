# Asisten AI Operasional GYNTRANS (LangGraph)

## Jalankan

```bash
uv run langgraph dev --tunnel

uv run pytest -q -m "not live"   # unit test, tanpa jaringan
uv run pytest -q -m live         # korpus regresi, butuh .env terisi
```

## Cara kerja `tools_rates`

Alur: `grammar -> catalog -> matcher -> query -> pipeline`.

1. **grammar** Nilai `origin` dan `destinasi` mengikuti tata bahasa tertutup:
   `sisi := KODE ("+" KODE)*`, dengan KODE diambil apa adanya dari
   `kode_destinasi`. Angka di belakang kota adalah bagian dari kode, jadi
   `SMG 2` bukan variasi longgar dari `SMG` melainkan kode yang berbeda.
   Tanda hubung hanya pemisah tampilan dan tidak pernah tersimpan di DB.
2. **catalog** Masterdata dimuat sekali ke memori dengan TTL 15 menit, termasuk
   `route_index` yang memetakan bentuk kanonik ke nilai DB yang persis.
   Pencarian karena itu bisa memakai filter eksak tanpa perlu menambah field
   turunan di Meilisearch. Nilai rute yang gagal di-parse dicatat ke log
   sebagai penanda inkonsistensi penulisan di masterdata.
3. **matcher** Satu-satunya tempat pencocokan fuzzy terjadi, dan hanya untuk
   satu segmen teks menjadi satu entitas kanonik. Strateginya bertangga
   (eksak, skeleton konsonan, Levenshtein, lalu Meilisearch) dan yang pertama
   kena langsung menang. Setiap hasil mencatat strategi mana yang dipakai.
4. **query** Enam langkah relaksasi, masing-masing satu filter eksak, dari
   paling tepat sampai mitra saja. Langkah yang menang dicatat di
   `matched_step`.
5. **pipeline** Berusaha dulu, bertanya hanya setelah semua langkah gagal, dan
   pertanyaannya membawa temuan lewat field `options`.

## Menambah kasus regresi

Tambahkan satu blok ke `tests/corpus/rates.yaml`. Tidak perlu menulis kode.
Ini cara utama menjaga sistem tetap tahan banting terhadap typo dan bentuk
chat baru.

## Data

Directus adalah sumber kebenaran, Meilisearch proyeksinya. Index `rates`
memakai field `customer_nama`, `expedisi_nama`, `origin`, `destinasi`,
`truck_type`, `rate`, `dp`, `uang_jalan`, dan `status`.

Semua pencarian selalu menyertakan `status != "archived"`, jadi `status` wajib
ada di `filterableAttributes` index. Begitu pula `customer_nama`,
`expedisi_nama`, `origin`, `destinasi`, dan `truck_type`.

Variabel lingkungan: `MEILISEARCH_URL`, `MEILISEARCH_KEY`, `DIRECTUS_BASE_URL`,
`DIRECTUS_TOKEN`, dan kunci API model sesuai provider di `src/agent/config.py`.
