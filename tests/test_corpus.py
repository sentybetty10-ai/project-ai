"""Runner korpus regresi.

Kasus disimpan sebagai data di tests/corpus/rates.yaml supaya siapa pun bisa
menambah kasus chat nyata tanpa menulis kode.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

CORPUS_PATH = Path(__file__).parent / "corpus" / "rates.yaml"
_SLOT_KEYS = {"origin", "destinasi", "customer", "expedisi", "truck_type"}
_STATUS_SAH = {"success", "not_found", "needs_clarification", "error"}


def _load_cases() -> list[dict]:
    with CORPUS_PATH.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle).get("cases", []) or []


CASES = _load_cases()


def test_korpus_valid():
    """Berjalan di CI tanpa jaringan: pastikan korpus tidak rusak bentuknya."""
    assert CASES, "korpus kosong"
    seen: set[str] = set()
    for case in CASES:
        case_id = case.get("id")
        assert case_id, f"kasus tanpa id: {case}"
        assert case_id not in seen, f"id ganda: {case_id}"
        seen.add(case_id)

        slots = case.get("slots") or {}
        assert slots, f"{case_id}: slots kosong"
        unknown = set(slots) - _SLOT_KEYS
        assert not unknown, f"{case_id}: slot tidak dikenal {unknown}"

        harap = case.get("harap") or {}
        assert harap.get("status") in _STATUS_SAH, f"{case_id}: status harap tidak sah"


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("MEILISEARCH_URL"), reason="butuh koneksi Meilisearch")
@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_korpus_live(case):
    from src.agent.domains.rates.pipeline import run_rates_query

    out = run_rates_query(**(case.get("slots") or {}))
    harap = case.get("harap") or {}
    case_id = case["id"]

    assert out["status"] == harap["status"], f"{case_id}: {out['message']}"

    if "needs" in harap:
        assert harap["needs"] in out["needs_clarification"], out["needs_clarification"]

    if "row_id" in harap:
        ids = [str(r.get("id")) for r in out["rates"]]
        assert str(harap["row_id"]) in ids, f"{case_id}: dapat {ids}"

    if "truck_type" in harap:
        trucks = {str(r.get("truck_type", "")).upper() for r in out["rates"]}
        assert harap["truck_type"].upper() in trucks, trucks

    if "destinasi_mengandung" in harap:
        for row in out["rates"]:
            assert harap["destinasi_mengandung"] in str(row["destinasi"]).upper()
