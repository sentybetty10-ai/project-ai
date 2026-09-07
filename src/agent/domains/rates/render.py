"""Renderer deterministik untuk hasil pipeline rates.

Angka tarif, rupiah, dan nama mitra dirender murni oleh Python dari data
tool — tidak pernah ditulis ulang oleh LLM, sehingga mustahil berubah.
LLM hanya menambah kalimat pembuka/penutup di sekitar blok ini.
"""

from __future__ import annotations

from typing import Any

from src.agent.domains.rates.types import PipelineResult


def format_rupiah(value: int | float) -> str:
    return f"Rp {int(value):,}".replace(",", ".")


def _format_item(index: int, rate: dict[str, Any]) -> list[str]:
    return [
        f"{index}. Rute: {rate['origin']} ➔ {rate['destinasi']}",
        f"   - Tipe Truk: {rate['type_mobil']}",
        f"   - Ekspedisi: {rate['expedisi_nama']}",
        f"   - Customer: {rate['customer_nama']}",
        f"   - Rate: {format_rupiah(rate['rate'])}",
        f"   - DP: {format_rupiah(rate['dp'])}",
        f"   - Uang jalan: {format_rupiah(rate['uang_jalan'])}",
    ]


def format_result(result: PipelineResult) -> str:
    """Render blok tarif final. Mengembalikan string kosong untuk status
    non-success agar LLM memakai field `message` sebagai gantinya."""
    if result.status != "success" or not result.rates:
        return ""
    parts = [result.message, ""]
    for i, rate in enumerate(result.rates, 1):
        parts.extend(_format_item(i, rate))
        parts.append("")
    return "\n".join(parts).rstrip()
