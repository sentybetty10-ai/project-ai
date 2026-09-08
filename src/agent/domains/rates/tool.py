from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.agent.domains.rates.pipeline import run_rates_query_async
from src.agent.domains.rates.types import TOOL_NAME, split_tool_payload

logger = logging.getLogger("gyntrans.domains.rates")


@tool(TOOL_NAME, response_format="content_and_artifact")
async def tools_rates(
    origin: str = "",
    destinasi: str = "",
    customer: str = "",
    expedisi: str = "",
    type_mobil: str = "",
) -> tuple[dict, dict]:
    """Cek tarif masterdata RATES (ongkos D.O per rute, mitra, dan armada).

    Panggil untuk SEMUA pertanyaan tarif meski informasi belum lengkap —
    backend mencoba dulu dan hanya bertanya setelah semua langkah gagal.

    Aturan pengisian slot:
    - origin/destinasi: WAJIB salin SELURUH blok alamat muat/bongkar apa
      adanya — nama pabrik, jalan, desa, kecamatan, kota/kabupaten — bukan
      hanya nama pabriknya. Nama kota sering berada di tengah/akhir alamat;
      membuang alamat berarti membuang rutenya. Contoh: "Muat : Wavin Trading
      Indonesia, Mangunsari, Kedawung, Banyuputih, Batang Regency, Central
      Java 51271" -> origin = "Wavin Trading Indonesia, Mangunsari, Kedawung,
      Banyuputih, Batang Regency, Central Java 51271".
    - Salin angka apa adanya (jakarta 2, smg 4) dan multi-kota apa adanya
      (jkt+smg, Tangerang Bogor dan Bekasi, Tanggerang-Bogor-Bekasi). Kata
      titik/zona dan nama pabrik di dalam alamat tidak perlu dibuang —
      backend yang memisahkannya dari nama kota.
    - customer: nama dari baris Customer/Cust/Mitra, atau nama PT/CV di baris
      Muat (misal: PT.EASTWIND/CV.KAYU BAGUS).
    - expedisi: nama dari baris Expedisi. Boleh tertukar dengan customer,
      backend yang mencocokkan.
    - type_mobil: baris Armada/Tipe Mobil bila disebut, salin apa adanya
      (FLatbed Trailer, Wing Box, CDD, CDD BOX, CDDL, Tronton Bak Terbuka).
    - JANGAN memasukkan tanggal, jam, nomor HP/WA, PIC, driver, nopol, atau
      detail muatan (CBM, dimensi, jenis barang) ke slot mana pun.

    Args:
        origin: Blok alamat muat lengkap dari user.
        destinasi: Blok alamat bongkar/tujuan lengkap dari user.
        customer: Nama mitra/customer.
        expedisi: Nama ekspedisi.
        type_mobil: Tipe mobil/armada bila disebut.
    """
    logger.info(
        "tools_rates origin=%r destinasi=%r customer=%r expedisi=%r type_mobil=%r",
        origin,
        destinasi,
        customer,
        expedisi,
        type_mobil,
    )
    return split_tool_payload(
        await run_rates_query_async(
            origin=origin,
            destinasi=destinasi,
            customer=customer,
            expedisi=expedisi,
            type_mobil=type_mobil,
        )
    )
