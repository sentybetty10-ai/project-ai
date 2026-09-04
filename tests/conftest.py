"""Fixture pengujian.

Unit test WAJIB berjalan tanpa jaringan. Katalog diinjeksi dan pemanggilan
Meilisearch di matcher dimatikan. Tes lama tidak punya isolasi ini, sehingga
sebuah tes bisa lulus justru ketika Meilisearch mati total.
"""

from __future__ import annotations

import pytest

from src.agent.domains.rates import catalog as catalog_module
from src.agent.domains.rates import matcher as matcher_module
from src.agent.services.meili import SearchResult

# Masterdata palsu yang meniru bentuk kode_destinasi.
LOCATIONS = [
    {"alamat_tujuan": "SMG", "alamat_lengkap": "SEMARANG"},
    {"alamat_tujuan": "SMG 2", "alamat_lengkap": ""},
    {"alamat_tujuan": "JKT", "alamat_lengkap": "JAKARTA"},
    {"alamat_tujuan": "JKT 2", "alamat_lengkap": ""},
    {"alamat_tujuan": "TGR", "alamat_lengkap": "TANGERANG"},
    {"alamat_tujuan": "TGR 2", "alamat_lengkap": ""},
    {"alamat_tujuan": "BGR", "alamat_lengkap": "BOGOR"},
    {"alamat_tujuan": "BKS", "alamat_lengkap": "BEKASI"},
    {"alamat_tujuan": "SBY", "alamat_lengkap": "SURABAYA"},
    {"alamat_tujuan": "SBY 3", "alamat_lengkap": ""},
    {"alamat_tujuan": "BDG", "alamat_lengkap": "BANDUNG"},
    {"alamat_tujuan": "WNG", "alamat_lengkap": "WONOGIRI"},
    {"alamat_tujuan": "GRS", "alamat_lengkap": "GRINGSING"},
    {"alamat_tujuan": "BTG", "alamat_lengkap": "BATANG"},
    {"alamat_tujuan": "JGJ", "alamat_lengkap": "JOGJAKARTA"},
    {"alamat_tujuan": "SOLO", "alamat_lengkap": "SOLO"},
    {"alamat_tujuan": "PKL", "alamat_lengkap": "PEKALONGAN"},
]

# Baris tarif palsu yang meniru bentuk index rates.
RATE_ROWS = [
    {"origin": "SMG", "destinasi": "TGR+BGR+BKS",
     "customer_nama": "MAKMUR TECHNOLOGY I", "expedisi_nama": "", "truck_type": "CDD"},
    {"origin": "JGJ", "destinasi": "SMG",
     "customer_nama": "MAKMUR TECHNOLOGY I", "expedisi_nama": "", "truck_type": "CDD"},
    {"origin": "TGR 2", "destinasi": "SMG",
     "customer_nama": "EDS", "expedisi_nama": "RAPI JKT", "truck_type": "CDD BOX"},
    {"origin": "SBY", "destinasi": "PKL",
     "customer_nama": "EXCELLENCE QUALITIES YARN",
     "expedisi_nama": "EXCELLENCE QUALITIES YARN", "truck_type": "WB"},
    {"origin": "BTG", "destinasi": "SMG",
     "customer_nama": "WAVIN TRADING INDONESIA", "expedisi_nama": "",
     "truck_type": "TRONTON BAK"},
    {"origin": "BTG", "destinasi": "SMG",
     "customer_nama": "WAVIN TRADING INDONESIA", "expedisi_nama": "",
     "truck_type": "TRONTON BOX"},
    {"origin": "WNG", "destinasi": "JKT 2",
     "customer_nama": "PT LIEBRA PERMANA", "expedisi_nama": "OOCL", "truck_type": "CDD"},
    {"origin": "JKT+SMG 2", "destinasi": "SBY 3",
     "customer_nama": "AST", "expedisi_nama": "", "truck_type": "WB"},
]


@pytest.fixture
def catalog():
    return catalog_module.build_catalog(locations=LOCATIONS, rate_rows=RATE_ROWS)


@pytest.fixture(autouse=True)
def no_network(request, monkeypatch):
    """Matikan jalur Meilisearch hanya untuk unit test non-live."""
    if request.node.get_closest_marker("live"):
        yield
        return

    monkeypatch.setattr(
        matcher_module.meili_service, "search", lambda *a, **k: SearchResult(),
    )
    catalog_module.reset_catalog()
    yield
    catalog_module.reset_catalog()
