"""Unit test offline untuk query.py.

Menutup celah cakupan lama: sort_hits sebelumnya tidak punya test offline
sama sekali, termasuk aturan kardinalitas rute yang kini simetris antara
sisi origin dan destinasi.
"""

from __future__ import annotations

from src.agent.domains.rates.grammar import RouteSide
from src.agent.domains.rates.query import sort_hits


def _hit(id_, origin, destinasi, truck="CDD", customer="PT X", expedisi="", status="published"):
    return {
        "id": id_,
        "origin": origin,
        "destinasi": destinasi,
        "customer_nama": customer,
        "expedisi_nama": expedisi,
        "type_mobil": truck,
        "status": status,
    }


def _ids(hits):
    return [h["id"] for h in hits]


def test_origin_single_menyaring_multi_muat():
    hits = [
        _hit(1, "JKT+SMG", "SOLO"),
        _hit(2, "JKT", "SOLO"),
    ]
    ranked = sort_hits(
        hits,
        origin=RouteSide(("JKT",)),
        destinasi=RouteSide(("SOLO",)),
        partners=[],
        trucks=[],
    )
    assert _ids(ranked) == [2]


def test_destinasi_single_menyaring_multi_drop():
    hits = [
        _hit(1, "WNG", "SMG+JKT"),
        _hit(2, "WNG", "SMG"),
    ]
    ranked = sort_hits(
        hits,
        origin=RouteSide(("WNG",)),
        destinasi=RouteSide(("SMG",)),
        partners=[],
        trucks=[],
    )
    assert _ids(ranked) == [2]


def test_origin_multi_menyaring_single():
    hits = [
        _hit(1, "JKT", "SBY"),
        _hit(2, "JKT+SMG", "SBY"),
    ]
    ranked = sort_hits(
        hits,
        origin=RouteSide(("JKT", "SMG")),
        destinasi=RouteSide(("SBY",)),
        origin_raw="jkt+smg",
        partners=[],
        trucks=[],
    )
    assert _ids(ranked) == [2]


def test_destinasi_multi_menyaring_single():
    hits = [
        _hit(1, "WNG", "SMG"),
        _hit(2, "WNG", "SMG+JKT"),
    ]
    ranked = sort_hits(
        hits,
        origin=RouteSide(("WNG",)),
        destinasi=RouteSide(("SMG", "JKT")),
        destinasi_raw="smg+jkt",
        partners=[],
        trucks=[],
    )
    assert _ids(ranked) == [2]


def test_preferensi_kosong_jatuh_ke_semua():
    """Jika kardinalitas yang diinginkan tidak ada di hasil, jangan disaring paksa."""
    hits = [_hit(1, "WNG", "SMG+JKT")]
    ranked = sort_hits(
        hits,
        origin=RouteSide(("WNG",)),
        destinasi=RouteSide(("SMG",)),
        partners=[],
        trucks=[],
    )
    assert _ids(ranked) == [1]


def test_skor_rute_eksak_mengalahkan_relaksasi():
    hits = [
        _hit(1, "SMG", "JKT", customer="PT LAIN"),
        _hit(2, "WNG", "JKT", customer="PT X"),
    ]
    ranked = sort_hits(
        hits,
        origin=RouteSide(("WNG",)),
        destinasi=RouteSide(("JKT",)),
        partners=["PT X"],
        trucks=["CDD"],
    )
    assert ranked[0]["id"] == 2
