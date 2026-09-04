from __future__ import annotations

import logging
import re
from typing import Any

from src.agent.domains.rates import query as query_engine
from src.agent.domains.rates.catalog import Catalog, get_catalog
from src.agent.domains.rates.grammar import RouteSide
from src.agent.domains.rates.matcher import (
    resolve_partner,
    resolve_route_side,
    resolve_truck,
)
from src.agent.domains.rates.types import PipelineResult, cfg
from src.agent.utils.text import normalize_upper, normalize_whitespace, parse_numeric

logger = logging.getLogger("gyntrans.domains.rates.pipeline")

_MAX_OPTIONS = 10


def _resolve_partner_groups(
    slots: list[str], catalog: Catalog,
) -> tuple[list[list[str]], list[str]]:
    groups: list[list[str]] = []
    unresolved: list[str] = []

    for slot in slots:
        if catalog.partners.exact(slot):
            parts = [slot]
        else:
            parts = [
                p.strip()
                for p in re.split(r"[/,;&|\+]+|\bdan\b", slot, flags=re.IGNORECASE)
                if p.strip()
            ]
        slot_candidates: list[str] = []
        for p in (parts if parts else [slot]):
            matches = resolve_partner(p, catalog)
            if matches:
                for m in matches:
                    if m.value not in slot_candidates:
                        slot_candidates.append(m.value)
            else:
                unresolved.append(p)
        if slot_candidates and slot_candidates not in groups:
            groups.append(slot_candidates)

    return groups, unresolved


def _format_rate(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": hit.get("id"),
        "origin": hit.get("origin", "-"),
        "destinasi": hit.get("destinasi", "-"),
        "customer": hit.get("customer_nama", "-"),
        "expedisi": hit.get("expedisi_nama", "-"),
        "truck_type": hit.get("truck_type", "-"),
        "rate": parse_numeric(hit.get("rate", 0)),
        "dp": parse_numeric(hit.get("dp", 0)),
        "uang_jalan": parse_numeric(hit.get("uang_jalan", 0)),
        "status": hit.get("status", ""),
    }


def _success_message(total: int, displayed: int, remaining: int) -> str:
    if total <= 1:
        return "Ditemukan 1 data tarif yang cocok."
    base = f"Ditemukan {total} data tarif yang cocok."
    if remaining > 0:
        base += f" Menampilkan {displayed} data, masih ada {remaining} lainnya."
    return base


def _ask_route(catalog: Catalog, partner_groups: list[list[str]]) -> PipelineResult:
    outcome = query_engine.execute(
        catalog,
        partner_groups=partner_groups,
        origin=RouteSide(),
        destinasi=RouteSide(),
        trucks=[],
    )
    nama = partner_groups[0][0]
    if not outcome.hits:
        return PipelineResult(
            status="not_found",
            message=f"Mitra {nama} belum punya data tarif tersimpan.",
        )

    asal = sorted({normalize_upper(h.get("origin")) for h in outcome.hits if h.get("origin")})
    tujuan = sorted({normalize_upper(h.get("destinasi")) for h in outcome.hits if h.get("destinasi")})
    return PipelineResult(
        status="needs_clarification",
        message=(
            f"Mitra {nama} punya {outcome.estimated_total} data tarif. "
            "Mohon sebutkan kota muat atau kota tujuannya."
        ),
        total_found=outcome.estimated_total,
        needs_clarification=["origin_atau_destinasi"],
        options={"origin": asal[:_MAX_OPTIONS], "destinasi": tujuan[:_MAX_OPTIONS]},
    )


def _not_found(
    origin_raw: str, destinasi_raw: str, partner_groups: list[list[str]], truck_raw: str,
) -> PipelineResult:
    mitra = partner_groups[0][0] if partner_groups else "-"
    return PipelineResult(
        status="not_found",
        message=(
            f"Tidak ada data tarif untuk {origin_raw or '-'} ke {destinasi_raw or '-'} "
            f"(mitra: {mitra}, armada: {truck_raw or '-'})."
        ),
    )


def run_rates_query(
    *,
    origin: str = "",
    destinasi: str = "",
    customer: str = "",
    expedisi: str = "",
    truck_type: str = "",
) -> dict[str, Any]:
    origin = normalize_whitespace(origin)
    destinasi = normalize_whitespace(destinasi)
    customer = normalize_whitespace(customer)
    expedisi = normalize_whitespace(expedisi)
    truck_type = normalize_whitespace(truck_type)

    catalog = get_catalog()
    if not catalog.ok:
        return PipelineResult(
            status="error",
            message=(
                "Data master tarif sedang tidak bisa diakses, jadi pencarian belum "
                "bisa dijalankan. Ini gangguan di sisi sistem, bukan kesalahan penulisan."
            ),
        ).to_tool_dict()

    origin_side, origin_left = resolve_route_side(origin, catalog)
    dest_side, dest_left = resolve_route_side(destinasi, catalog)

    partner_groups, unresolved = _resolve_partner_groups(
        [s for s in (customer, expedisi) if s], catalog,
    )

    leftover_candidates: list[str] = []
    for leftover in [*origin_left, *dest_left]:
        found = resolve_partner(leftover, catalog)
        if found:
            for m in found:
                if m.value not in leftover_candidates:
                    leftover_candidates.append(m.value)
    if leftover_candidates and leftover_candidates not in partner_groups:
        partner_groups.append(leftover_candidates)

    trucks = resolve_truck(truck_type, catalog) if truck_type else []
    has_route = bool(origin_side) or bool(dest_side)

    if not partner_groups:
        if unresolved:
            return PipelineResult(
                status="needs_clarification",
                message=(
                    f"Nama mitra \"{unresolved[0]}\" belum terdaftar di data kami. "
                    "Mohon dicek penulisannya atau sebutkan nama lengkapnya."
                ),
                needs_clarification=["customer_atau_expedisi"],
            ).to_tool_dict()

        pesan = (
            "Rute sudah jelas, tapi mitranya belum disebut. "
            "Mohon sebutkan nama customer atau ekspedisinya."
            if has_route
            else "Mohon sebutkan nama mitra dan rutenya agar tarif bisa dicek."
        )
        return PipelineResult(
            status="needs_clarification",
            message=pesan,
            needs_clarification=["customer_atau_expedisi"],
        ).to_tool_dict()

    if not has_route:
        return _ask_route(catalog, partner_groups).to_tool_dict()

    outcome = query_engine.execute(
        catalog,
        partner_groups=partner_groups,
        origin=origin_side,
        destinasi=dest_side,
        trucks=trucks,
    )
    if not outcome.hits:
        return _not_found(origin, destinasi, partner_groups, truck_type).to_tool_dict()

    partners_flat = [name for group in partner_groups for name in group]
    ranked = query_engine.sort_hits(
        outcome.hits,
        origin=origin_side,
        destinasi=dest_side,
        origin_raw=origin,
        destinasi_raw=destinasi,
        partners=partners_flat,
        trucks=trucks,
    )
    displayed = ranked[: cfg.max_display]
    total = len(ranked)
    remaining = max(0, total - len(displayed))

    return PipelineResult(
        status="success",
        message=_success_message(total, len(displayed), remaining),
        total_found=total,
        displayed_count=len(displayed),
        has_more=remaining > 0,
        remaining_count=remaining,
        rates=[_format_rate(h) for h in displayed],
        matched_step=outcome.step,
    ).to_tool_dict()
