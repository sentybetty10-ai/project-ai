from __future__ import annotations

import logging

from langchain_core.tools import tool

from src.agent.domains.rates.pipeline import run_rates_query
from src.agent.domains.rates.types import TOOL_NAME

logger = logging.getLogger("gyntrans.domains.rates")


@tool(TOOL_NAME)
def tools_rates(
    origin: str = "",
    destinasi: str = "",
    customer: str = "",
    expedisi: str = "",
    truck_type: str = "",
) -> dict:
    """Cek tarif masterdata RATES.

    Args:
        origin: Kota atau lokasi muat dari user.
        destinasi: Kota atau lokasi bongkar dari user.
        customer: Nama mitra/customer.
        expedisi: Nama ekspedisi.
        truck_type: Tipe armada bila disebut.
    """
    logger.info(
        "tools_rates origin=%r destinasi=%r customer=%r expedisi=%r truck=%r",
        origin, destinasi, customer, expedisi, truck_type,
    )
    return run_rates_query(
        origin=origin,
        destinasi=destinasi,
        customer=customer,
        expedisi=expedisi,
        truck_type=truck_type,
    )
