"""Unit test renderer deterministik.

Blok `formatted` adalah satu-satunya sumber tampilan data tarif; angka rupiah
dan nama mitra wajib persis dari database, bukan tulisan ulang LLM.
"""

from __future__ import annotations

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
                "customer_nama": "PT KAYU BAGUS",
                "expedisi_nama": "PT KAYU BAGUS INTERNASIONAL",
                "type_mobil": "Flatbed Trailer",
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


def test_urutan_baris_formatted_presisi():
    text = render_module.format_result(_result())
    expected_lines = [
        "1. Rute: SMG ➔ SDA",
        "   - Tipe Truk: Flatbed Trailer",
        "   - Ekspedisi: PT KAYU BAGUS INTERNASIONAL",
        "   - Customer: PT KAYU BAGUS",
        "   - Rate: Rp 2.400.000",
        "   - DP: Rp 500.000",
        "   - Uang jalan: Rp 1.150.000",
    ]
    for line in expected_lines:
        assert line in text

    # Pastikan urutan munculnya baris sesuai urutan
    indices = [text.index(line) for line in expected_lines]
    assert indices == sorted(indices)


def test_status_non_success_tanpa_formatted():
    result = PipelineResult(status="not_found", message="Tidak ada data.")
    assert render_module.format_result(result) == ""


def test_format_rate_hit():
    raw_hit = {
        "id": "123",
        "status": "published",
        "rate": "2500000",
        "dp": "500000",
        "uang_jalan": "1000000",
        "expedisi_nama": "PT GYNTRANS",
        "origin": "JKT",
        "destinasi": "SUB",
    }
    normalized = render_module.format_rate_hit(raw_hit)
    assert normalized["id"] == "123"
    assert normalized["rate"] == 2500000
    assert normalized["dp"] == 500000
    assert normalized["uang_jalan"] == 1000000
    assert normalized["expedisi_nama"] == "PT GYNTRANS"
    assert normalized["customer_nama"] == "-"
    assert normalized["type_mobil"] == "-"

