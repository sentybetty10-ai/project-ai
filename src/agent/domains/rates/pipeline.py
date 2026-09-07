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
from src.agent.domains.rates.render import format_result
from src.agent.domains.rates.types import PipelineResult, cfg
from src.agent.utils.text import normalize_upper, normalize_whitespace, parse_numeric

logger = logging.getLogger("gyntrans.domains.rates.pipeline")

_MAX_OPTIONS = 10


def _finalize(result: PipelineResult) -> dict[str, Any]:
    result.formatted = format_result(result)
    return result.to_tool_dict()


def _resolve_partner_groups(
    slots: list[str],
    catalog: Catalog,
) -> tuple[list[list[str]], list[str], list[str]]:
    groups: list[list[str]] = []
    unresolved: list[str] = []
    canonicals: list[str] = []

    for slot in slots:
        if catalog.partners.exact(slot):
            parts = [slot]
        else:
            parts = [
                p.strip() for p in re.split(r"[/,;&|\+]+|\bdan\b", slot, flags=re.IGNORECASE) if p.strip()
            ]
        slot_candidates: list[str] = []
        for p in parts if parts else [slot]:
            matches = resolve_partner(p, catalog)
            if matches:
                if matches[0].value not in canonicals:
                    canonicals.append(matches[0].value)
                for m in matches:
                    if m.value not in slot_candidates:
                        slot_candidates.append(m.value)
            else:
                unresolved.append(p)
        if slot_candidates and not any(set(slot_candidates) & set(g) for g in groups):
            groups.append(slot_candidates)

    return groups, unresolved, canonicals


def _format_rate(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": hit.get("id"),
        "status": hit.get("status", ""),
        "rate": parse_numeric(hit.get("rate", 0)),
        "dp": parse_numeric(hit.get("dp", 0)),
        "uang_jalan": parse_numeric(hit.get("uang_jalan", 0)),
        "expedisi_id": hit.get("expedisi_id"),
        "expedisi_nama": hit.get("expedisi_nama", "-"),
        "customer_id": hit.get("customer_id"),
        "customer_nama": hit.get("customer_nama", "-"),
        "destinasi_id": hit.get("destinasi_id"),
        "origin": hit.get("origin", "-"),
        "destinasi": hit.get("destinasi", "-"),
        "type_mobil_id": hit.get("type_mobil_id"),
        "type_mobil": hit.get("type_mobil", "-"),
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
    origin_raw: str,
    destinasi_raw: str,
    partner_groups: list[list[str]],
    truck_raw: str,
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
    type_mobil: str = "",
) -> dict[str, Any]:
    origin = normalize_whitespace(origin)
    destinasi = normalize_whitespace(destinasi)
    customer = normalize_whitespace(customer)
    expedisi = normalize_whitespace(expedisi)
    type_mobil = normalize_whitespace(type_mobil)

    catalog = get_catalog()
    if not catalog.ok:
        return _finalize(
            PipelineResult(
                status="error",
                message=(
                    "Data master tarif sedang tidak bisa diakses, jadi pencarian belum "
                    "bisa dijalankan. Ini gangguan di sisi sistem, bukan kesalahan penulisan."
                ),
            )
        )

    origin_side, origin_left = resolve_route_side(origin, catalog)
    dest_side, dest_left = resolve_route_side(destinasi, catalog)

    partner_groups, unresolved, canonical_partners = _resolve_partner_groups(
        [s for s in (customer, expedisi) if s],
        catalog,
    )

    leftover_candidates: list[str] = []
    # Jika mitra belum terdeteksi dari slot customer/expedisi, periksa sisa kata asal dan tujuan.
    # Jika mitra sudah terdeteksi, abaikan dest_left (alamat bongkar penerima) agar
    # potongan nama jalan/daerah tidak ter-resolve paksa menjadi mitra asing.
    leftover_sources = origin_left if partner_groups else [*origin_left, *dest_left]
    for leftover in leftover_sources:
        found = resolve_partner(leftover, catalog)
        if found:
            for m in found:
                if m.value not in leftover_candidates:
                    leftover_candidates.append(m.value)
    if leftover_candidates and not any(set(leftover_candidates) & set(g) for g in partner_groups):
        partner_groups.append(leftover_candidates)
        if leftover_candidates[0] not in canonical_partners:
            canonical_partners.append(leftover_candidates[0])

    trucks = resolve_truck(type_mobil, catalog) if type_mobil else []
    has_route = bool(origin_side) or bool(dest_side)

    # Rampingkan slot mitra untuk memori konteks LLM: gunakan representasi kanonik input.
    initial_mitra = canonical_partners or list(dict.fromkeys(group[0] for group in partner_groups if group))

    resolved: dict[str, Any] = {
        "origin": list(origin_side.codes),
        "destinasi": list(dest_side.codes),
        "mitra": initial_mitra,
        "type_mobil": trucks,
    }

    if not partner_groups:
        if unresolved:
            result = PipelineResult(
                status="needs_clarification",
                message=(
                    f'Nama mitra "{unresolved[0]}" belum terdaftar di data kami. '
                    "Mohon dicek penulisannya atau sebutkan nama lengkapnya."
                ),
                needs_clarification=["customer_atau_expedisi"],
                resolved=resolved,
            )
            return _finalize(result)

        pesan = (
            "Rute sudah jelas, tapi mitranya belum disebut. Mohon sebutkan nama customer atau ekspedisinya."
            if has_route
            else "Mohon sebutkan nama mitra dan rutenya agar tarif bisa dicek."
        )
        return _finalize(
            PipelineResult(
                status="needs_clarification",
                message=pesan,
                needs_clarification=["customer_atau_expedisi"],
                resolved=resolved,
            )
        )

    if not has_route:
        result = _ask_route(catalog, partner_groups)
        result.resolved = resolved
        return _finalize(result)

    outcome = query_engine.execute(
        catalog,
        partner_groups=partner_groups,
        origin=origin_side,
        destinasi=dest_side,
        trucks=trucks,
    )
    if not outcome.hits:
        result = _not_found(origin, destinasi, partner_groups, type_mobil)
        result.resolved = resolved
        return _finalize(result)

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

    # Selaraskan slot mitra dengan entitas yang nyata-nyata cocok di baris tarif hasil query
    matched_partners: list[str] = []
    for h in displayed:
        for name in (h.get("customer_nama"), h.get("expedisi_nama")):
            if name and any(name.upper() == p.upper() for p in partners_flat):
                if name not in matched_partners:
                    matched_partners.append(name)
    if matched_partners:
        resolved["mitra"] = matched_partners

    # Selaraskan sisi rute jika sebelumnya kosong akibat relaksasi query (misal: TJ.PRIOK via tanpa_origin)
    if not resolved.get("origin"):
        origin_hits = list(dict.fromkeys(h.get("origin") for h in displayed if h.get("origin")))
        if origin_hits:
            resolved["origin"] = origin_hits

    if not resolved.get("destinasi"):
        dest_hits = list(dict.fromkeys(h.get("destinasi") for h in displayed if h.get("destinasi")))
        if dest_hits:
            resolved["destinasi"] = dest_hits

    return _finalize(
        PipelineResult(
            status="success",
            message=_success_message(total, len(displayed), remaining),
            total_found=total,
            displayed_count=len(displayed),
            has_more=remaining > 0,
            remaining_count=remaining,
            rates=[_format_rate(h) for h in displayed],
            matched_step=outcome.step,
            resolved=resolved,
        )
    )
