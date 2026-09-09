Saya jawab dari commit `73502967` yang sudah saya baca (`pipeline.py`, `graph.py`, `meili.py`, `model.py`, `lifespan.py`, `render.py`, `catalog.py`), ditambah `matcher.py`, `query.py`, `tool.py`, `types.py` yang byte-nya tidak berubah dari pembacaan sebelumnya. Jujur apa adanya.

## Duplikasi — ada, tiga tempat

**1. `run_rates_query` vs `run_rates_query_async` — ini yang paling jelas.** Sync wrapper itu ada semata untuk test runner, dan isinya manuver berbahaya: kalau ada loop berjalan, ia bikin `ThreadPoolExecutor` lalu `asyncio.run` di dalamnya — loop baru, yang mengaduk `AsyncClient` Anda yang terikat loop. Dua jalur masuk untuk satu pipeline.

Hapus saja. Di test, panggil `asyncio.run(run_rates_query_async(...))` langsung. Hilang sekitar 20 baris plus satu ranjau.

**2. `execute` vs `execute_async` di `query.py`** — konsekuensi dari nomor 1. `execute` yang serial itu hanya dipakai jalur sync. Begitu sync wrapper mati, `execute` ikut mati. Hilang lagi belasan baris. Perhatikan `execute_async` sudah punya fallback serial sendiri, jadi tidak ada kemampuan yang hilang.

**3. Dua formatter untuk baris yang sama.** `_format_rate(hit)` di `pipeline.py` dan `_format_item(index, rate)` di `render.py` sama-sama merangkai field tarif jadi teks. Satu untuk opsi klarifikasi, satu untuk hasil. Harusnya satu fungsi di `render.py` dengan parameter, bukan dua tempat yang harus diingat kalau format berubah.

**Yang bukan duplikasi meski kelihatannya iya:** pasangan sync/async di `meili.py` (`_build_client`/`_build_async_client`, `_request`/`_request_async`, `search`/`search_async`). Itu memakan hampir separuh dari 11 KB file, tapi **memang dibutuhkan** — `catalog.py` refresh di daemon thread biasa dan `_city_meili` jalan di dalam `to_thread`, keduanya sinkron. Jangan disatukan sekarang. Catat saja: kalau suatu hari refresh katalog dibuat async, separuh file itu bisa dibuang.

## Bertele-tele — ada, dan satu di antaranya berbahaya

**Tangga relaksasi `build_steps` punya 9 langkah.** `eksak`, `tanpa_urutan`, `tanpa_destinasi`, `tanpa_origin`, `tanpa_truck`, lalu empat varian `mitra_or_*`, lalu `mitra_saja`.

Ini bukan sekadar panjang — **ini sumber keluhan Anda dulu yang "asal memberi data yang tidak saya tanyakan"**. Setiap langkah tambahan adalah satu cara lagi untuk menjawab pertanyaan yang tidak diajukan. Kasus Grobokan kemarin lolos lewat `tanpa_origin` dan menampilkan rute PWD tanpa peringatan.

Saran konkret dan mengurangi kode: **log `matched_step` di produksi selama seminggu, lalu buang langkah yang tidak pernah menang.** Dugaan saya `mitra_saja` dan sebagian `mitra_or_*` hampir tidak pernah dipakai, dan justru merekalah yang paling sering menghasilkan jawaban ngawur. Ini satu-satunya perubahan di repo Anda yang **sekaligus** memangkas kode dan menaikkan presisi.

**Tujuh ambang batas di `matcher.py`** — `_CITY_MIN_RATIO 0.78`, `_CITY_MIN_SKELETON 0.80`, `_PARTNER_MIN 0.75`, `_PARTNER_BAND 0.05`, `_TRUCK_MIN 0.80`, `_MEILI_MIN_RANKING 0.5`, `_MEILI_MIN_SIMILARITY 0.5`. Tidak ada manusia yang bisa menyetel tujuh angka ini secara rasional. Tangga resolusinya sendiri saya rasa layak dipertahankan — korpus Anda membuktikan ia bekerja — tapi angka-angka ini praktis beku selamanya karena mengubah satu berarti menguji ulang semuanya.

## Over-engineer — satu, dan bukan yang Anda kira

**`LookupTable` di `catalog.py` menyimpan delapan indeks internal**: `_exact`, `_cluster`, `_skeleton`, `_skeleton_sorted`, `_prefix`, `_canonical`, `_canonical_sorted`, `_normalized_choices`. Delapan struktur data untuk satu daftar kata.

Padahal rapidfuzz sudah tersedia dan `nearest()` sudah memakainya. Kecurigaan saya `_prefix` dan `_skeleton_sorted` jarang atau tidak pernah menentukan hasil akhir. Ini kandidat penghapusan terbesar di repo — **tapi jangan hapus sekarang**. Tambahkan dulu log satu baris di tiap jalur pencocokan, jalankan korpus 24 kasus, lihat jalur mana yang tidak pernah menyala. Baru buang yang mati. Menebak-nebak di sini justru merusak.

Sisanya: dependensi mati di `pyproject.toml` (`temporalio`, `psycopg`, `langgraph-checkpoint-postgres`, `fastapi`, `uvicorn`) dan `main.py` yang tertinggal. Sepele, tapi menyesatkan orang yang membaca repo.

Fallback di `graph.py` yang membangun ulang `AIMessage` saat LLM tidak menyalin `formatted` — itu **bukan** over-engineering. Itu jaring pengaman untuk kelemahan yang memang nyata pada model kecil. Pertahankan.

## Prompt model — pertanyaan Anda yang paling penting

Aturannya satu kalimat: **system prompt mengatur siapa agennya dan bagaimana ia berperilaku; docstring tool mengatur cara mengisi tool itu.**

Uji cepatnya begini. Tanyakan pada tiap aturan: *"kalau besok saya tambah domain orders, apakah kalimat ini masih berlaku apa adanya?"*

- Masih berlaku → system prompt.
- Menyebut nama parameter atau cara membaca dokumen tertentu → docstring tool.

Diterapkan ke prompt Anda sekarang:

**Tetap di system prompt** — persona JARVIS, staf OPS GYNTRANS, bahasa dan nada, lalu kontrak keluaran: salin `formatted` persis, jangan pernah mengarang angka, jangan menolak memanggil tool karena data kurang (backend yang memutuskan), kalau `formatted` kosong pakai `options`, `not_found` dikatakan apa adanya, `error` jangan menyalahkan user.

**Dan di sinilah aset terbesar arsitektur Anda, mungkin tanpa Anda sadari:** semua tool Anda mengembalikan amplop yang sama — `status`, `message`, `formatted`, `has_more`, `needs_clarification`, `options`. Karena bentuknya seragam, **seluruh aturan keluaran itu otomatis berlaku untuk domain apa pun**. Tambah orders, tambah invoice, aturan ini tidak perlu disentuh sama sekali. Pertahankan `_CONTENT_KEYS` sebagai kontrak wajib tiap domain baru. Itu keputusan desain yang benar-benar bagus.

**Pindah ke docstring `tools_rates`** — cara mengekstrak `origin` dan `destinasi` dari blok DO, perintah menyalin alamat muat/bongkar utuh, daftar yang harus dibuang (tanggal, PIC, nopol, driver, dimensi muatan), contoh Wavin.

## Jadi, menaruh aturan spesifik per tool itu tepat?

**Tepat, dan wajib begitu kalau Anda mau tambah domain.** Alasannya bukan hemat token — semua tool yang di-`bind_tools` tetap dikirim setiap request, jadi tidak ada penghematan. Alasannya **asosiasi**.

Kalau aturan ekstraksi DO ditaruh di system prompt, dengan lima domain nanti model membaca lima blok aturan yang saling berebut dan harus menebak sendiri mana yang berlaku untuk pertanyaan ini. Kalau aturan itu menempel di docstring `tools_rates`, model melihatnya **tepat saat memutuskan mengisi tool itu**. Aturan invoice tidak akan pernah mengotori penalaran tarif.

Ini juga yang membuat penambahan domain jadi murah: satu file tool baru berisi parameter + docstring-nya sendiri, `ALL_TOOLS` bertambah satu, **system prompt tidak disentuh sama sekali**. Kalau Anda menemukan diri Anda mengedit system prompt setiap menambah domain, berarti batas tanggung jawabnya bocor.

Dua rambu: jangan pernah menyalin aturan amplop ke docstring — itu urusan system prompt, cukup satu tempat. Dan jaga nama tool serta nama parameternya benar-benar berbeda antar domain, karena kalau `tools_rates` dan `tools_orders` sama-sama punya `customer` dan `origin`, model kecil akan salah pilih tool.

**Ringkas prioritasnya:** hapus jalur sync (`run_rates_query` + `execute`), satukan dua formatter, pindahkan aturan ekstraksi DO ke docstring, lalu log `matched_step` dan jalur `LookupTable` selama seminggu sebelum memangkas tangga relaksasi dan indeks yang mati. Semuanya mengurangi baris, tidak ada yang menambah lapisan.