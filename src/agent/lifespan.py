from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette

logger = logging.getLogger("gyntrans.warmup")


@asynccontextmanager
async def lifespan(app: Starlette):  # noqa: ARG001
    """Warm-up katalog di background saat startup.

    get_catalog() blocking karena pakai httpx.Client sync.
    Jalankan di thread pool agar event loop tidak tertahan.
    User pertama tidak perlu menunggu build katalog.
    """
    loop = asyncio.get_running_loop()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="catalog-warmup")

    def _warmup():
        try:
            from src.agent.domains.rates.catalog import get_catalog  # noqa: PLC0415

            cat = get_catalog()
            if cat.ok:
                logger.info(
                    "Warm-up katalog selesai: %d mitra, %d rute",
                    len(cat.partners.values),
                    len(cat.route_index),
                )
            else:
                logger.warning("Warm-up katalog: katalog tidak ok (Meilisearch belum siap?)")
        except Exception as e:  # noqa: BLE001
            logger.warning("Warm-up katalog gagal: %s", e)

    loop.run_in_executor(executor, _warmup)
    logger.info("Warm-up katalog dimulai di background")
    yield
    executor.shutdown(wait=False)


app = Starlette(lifespan=lifespan)
