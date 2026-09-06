"""Unit test renderer deterministik.

Blok `formatted` adalah satu-satunya sumber tampilan data tarif; angka rupiah
dan nama mitra wajib persis dari database, bukan tulisan ulang LLM.
"""

from __future__ import annotations

import dataclasses

from src.agent.domains.rates import render as render_module
from src.agent.domains.rates.types import PipelineResult


def _result() -> PipelineResult:
    return PipelineResult(
        status="success",
        message="Ditemukan 1 data tarif yang cocok.",
        total_found=1,
        displayed_count=1,
        rates=[
            {
                "id": 10164,
                "origin": "SMG",
                "destinasi": "SDA",
                "customer": "PT KAYU BAGUS",
                "expedisi": "PT KAYU BAGUS INTERNASIONAL",
                "truck_type": "Flatbed Trailer",
                "rate": 2400000,
                "dp": 500000,
                "uang_jalan": 1150000,
                "status": "published",
            }
        ],
    )


def test_format_rupiah_indonesia():
    assert render_module.format_rupiah(2400000) == "Rp 2.400.000"
    assert render_module.format_rupiah(0) == "Rp 0"


def test_formatted_memuat_data_persis():
    text = render_module.format_result(_result())
    assert "SMG ➔ SDA" in text
    assert "Rp 2.400.000" in text
    assert "PT KAYU BAGUS INTERNASIONAL" in text
    assert "Flatbed Trailer" in text


def test_dp_uang_jalan_tampil_secara_default():
    text = render_module.format_result(_result())
    assert "DP: Rp 500.000" in text
    assert "Uang jalan: Rp 1.150.000" in text


def test_dp_uang_jalan_bisa_disembunyikan(monkeypatch):
    cfg_baru = dataclasses.replace(render_module.cfg, include_dp_uang_jalan=False)
    monkeypatch.setattr(render_module, "cfg", cfg_baru)
    text = render_module.format_result(_result())
    assert "DP:" not in text
    assert "Uang jalan" not in text
    assert "Rp 2.400.000" in text


def test_status_non_success_tanpa_formatted():
    result = PipelineResult(status="not_found", message="Tidak ada data.")
    assert render_module.format_result(result) == ""
