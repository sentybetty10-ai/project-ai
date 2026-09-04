"""Unit test tangga strategi pencocokan. Tanpa jaringan, katalog diinjeksi."""

from __future__ import annotations

import pytest

from src.agent.domains.rates.matcher import (
    resolve_city,
    resolve_partner,
    resolve_route_side,
    resolve_truck,
)


@pytest.mark.parametrize(
    ("raw", "kode"),
    [
        ("SMG", "SMG"),
        ("semarang", "SMG"),
        ("Kota Semarang, Jawa Tengah", "SMG"),
        ("smrng", "SMG"),
        ("semarng", "SMG"),
        ("jkrta", "JKT"),
        ("tgrng", "TGR"),
        ("bandng", "BDG"),
        ("surabya", "SBY"),
        ("wonogri", "WNG"),
        ("gringsing", "GRS"),
        ("jogja", "JGJ"),
        ("solo", "SOLO"),
    ],
)
def test_resolve_city_typo(catalog, raw, kode):
    match = resolve_city(raw, catalog)
    assert match is not None, raw
    assert match.value == kode


@pytest.mark.parametrize(
    ("raw", "kode"),
    [
        ("tangerang 2", "TGR 2"),
        ("tangerang 2 titik", "TGR 2"),
        ("jakarta 2", "JKT 2"),
        ("sby 3 zona", "SBY 3"),
    ],
)
def test_resolve_city_angka_bagian_dari_kode(catalog, raw, kode):
    match = resolve_city(raw, catalog)
    assert match is not None, raw
    assert match.value == kode


def test_kombinasi_angka_tidak_ada_ditolak(catalog):
    """Angka bukan pengubah, jadi kode yang tidak ada tidak boleh dikarang."""
    assert resolve_city("semarang 9", catalog) is None


@pytest.mark.parametrize("raw", ["AICA", "Central Java", "Jawa Tengah"])
def test_bukan_kota_mengembalikan_none(catalog, raw):
    assert resolve_city(raw, catalog) is None


def test_multi_kota(catalog):
    side, leftovers = resolve_route_side("Tangerang, Bogor, dan Bekasi", catalog)
    assert side.codes == ("TGR", "BGR", "BKS")
    assert side.key == "TGR+BGR+BKS"
    assert leftovers == []


def test_multi_kota_dengan_strip(catalog):
    side, _ = resolve_route_side("Tanggerang-Bogor-Bekasi", catalog)
    assert side.key == "TGR+BGR+BKS"


def test_keterangan_wilayah_tidak_dianggap_kota_kedua(catalog):
    """Kasus yang dulu memaksa adanya daftar kata hasil tuning manual."""
    side, leftovers = resolve_route_side("Batang Regency, Central Java", catalog)
    assert side.codes == ("BTG",)
    assert leftovers == ["Central Java"]


def test_nama_pabrik_di_lokasi_menjadi_sisa(catalog):
    side, leftovers = resolve_route_side("surabaya (pt.excellent)", catalog)
    assert side.codes == ("SBY",)
    assert leftovers == ["pt.excellent"]


def test_lokasi_bukan_kota_menghasilkan_sisi_kosong(catalog):
    side, leftovers = resolve_route_side("AICA", catalog)
    assert not side
    assert leftovers == ["AICA"]


@pytest.mark.parametrize(
    ("raw", "kanonik"),
    [
        ("EDS", "EDS"),
        ("Makmur Technology", "MAKMUR TECHNOLOGY I"),
        ("Makmur Technologi", "MAKMUR TECHNOLOGY I"),
        ("Pt liebra permna", "PT LIEBRA PERMANA"),
        ("Excellent", "EXCELLENCE QUALITIES YARN"),
        ("oocl", "OOCL"),
    ],
)
def test_resolve_partner(catalog, raw, kanonik):
    hasil = resolve_partner(raw, catalog)
    assert hasil, raw
    assert hasil[0].value == kanonik


def test_nama_asing_tidak_dipaksa_cocok(catalog):
    """Nama dari baris Note tidak boleh menyeret mitra mana pun."""
    assert resolve_partner("Yuyun", catalog) == []


@pytest.mark.parametrize(
    ("raw", "kanonik"),
    [
        ("WB", ["WB"]),
        ("Wing Box", ["WB"]),
        ("Tronton Bak Terbuka", ["TRONTON BAK"]),
        ("CDD", ["CDD"]),
    ],
)
def test_resolve_truck(catalog, raw, kanonik):
    assert resolve_truck(raw, catalog) == kanonik


def test_route_index_memetakan_ke_nilai_db(catalog):
    assert catalog.route_index["TGR+BGR+BKS"] == ["TGR+BGR+BKS"]
    assert catalog.route_index["JKT+SMG 2"] == ["JKT+SMG 2"]
    assert catalog.route_index_sorted["JKT+SMG 2"] == ["JKT+SMG 2"]
    assert catalog.unparsed_routes == []


def test_resolve_route_side_memisahkan_mitra_dan_kota(catalog):
    side, leftovers = resolve_route_side("EDS TANGERANG", catalog)
    assert side.codes == ("TGR",)
    assert leftovers == ["EDS"]
    assert resolve_partner(leftovers[0], catalog)[0].value == "EDS"
