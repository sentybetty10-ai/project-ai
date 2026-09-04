"""Unit test tata bahasa rute. Murni string, tanpa masterdata dan tanpa jaringan."""

from __future__ import annotations

import pytest

from src.agent.domains.rates.grammar import (
    RouteSide,
    normalize_code,
    parse_db_side,
    split_trailing_number,
    split_user_segments,
    strip_noise,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("smg", "SMG"),
        ("smg2", "SMG 2"),
        ("  SMG   2 ", "SMG 2"),
        ("smg 02", "SMG 2"),
        ("tronton bak", "TRONTON BAK"),
        ("", ""),
    ],
)
def test_normalize_code(raw, expected):
    assert normalize_code(raw) == expected


@pytest.mark.parametrize(
    ("raw", "base", "number"),
    [
        ("TGR 2", "TGR", "2"),
        ("TGR", "TGR", ""),
        ("tangerang 2", "TANGERANG", "2"),
        ("2", "2", ""),
    ],
)
def test_split_trailing_number(raw, base, number):
    assert split_trailing_number(raw) == (base, number)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("tangerang 2 titik", "tangerang 2"),
        ("sby 3 zona", "sby 3"),
        ("jkt 2 point", "jkt 2"),
        ("semarang", "semarang"),
    ],
)
def test_strip_noise(raw, expected):
    assert strip_noise(raw) == expected


def test_parse_db_side_tunggal():
    assert parse_db_side("SMG").codes == ("SMG",)


def test_parse_db_side_multi_kota():
    assert parse_db_side("JKT+SMG 2").codes == ("JKT", "SMG 2")


def test_parse_db_side_toleran_spasi():
    assert parse_db_side("JKT + SMG  2").key == "JKT+SMG 2"


def test_parse_db_side_tidak_memecah_strip():
    """Tanda hubung hanya pemisah tampilan, bukan pemisah nilai di DB."""
    assert len(parse_db_side("TGR-BGR").codes) == 1


def test_route_side_key_dan_sorted_key():
    side = RouteSide(("SMG 2", "JKT"))
    assert side.key == "SMG 2+JKT"
    assert side.sorted_key == "JKT+SMG 2"
    assert side.is_multi is True


def test_route_side_kosong_bernilai_false():
    assert not RouteSide()


@pytest.mark.parametrize(
    ("raw", "jumlah"),
    [
        ("Tangerang, Bogor, dan Bekasi", 3),
        ("Tanggerang-Bogor-Bekasi", 3),
        ("jkt+smg", 2),
        ("surabaya (pt.excellent)", 2),
        ("Semarang", 1),
        ("", 0),
    ],
)
def test_split_user_segments(raw, jumlah):
    assert len(split_user_segments(raw)) == jumlah
