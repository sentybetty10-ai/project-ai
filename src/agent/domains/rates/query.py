from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from src.agent.domains.rates.catalog import Catalog
from src.agent.domains.rates.grammar import RouteSide, parse_db_side
from src.agent.domains.rates.types import cfg
from src.agent.services.meili import meili_service
from src.agent.utils.text import normalize_upper, parse_numeric

logger = logging.getLogger("gyntrans.domains.rates.query")

BASE_FILTER = 'status != "archived"'


@dataclass(frozen=True)
class QueryStep:
    name: str
    filter_expr: str


@dataclass
class QueryOutcome:
    hits: list[dict[str, Any]] = field(default_factory=list)
    estimated_total: int = 0
    step: str = ""
    steps_tried: list[str] = field(default_factory=list)


def quote(value: str) -> str:
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def in_filter(field_name: str, values: list[str]) -> str:
    if not values:
        return ""
    if len(values) == 1:
        return f"{field_name} = {quote(values[0])}"
    return f"{field_name} IN [{', '.join(quote(v) for v in values)}]"


def _all_of(parts: list[str]) -> str:
    return " AND ".join(p for p in parts if p)


def partner_clause(groups: list[list[str]], *, require_all: bool) -> str:
    clauses: list[str] = []
    for group in groups:
        if not group:
            continue
        clauses.append(f"({in_filter('customer_nama', group)} OR {in_filter('expedisi_nama', group)})")
    if not clauses:
        return ""
    if len(clauses) == 1:
        return clauses[0]
    if require_all:
        return " AND ".join(clauses)
    return "(" + " OR ".join(clauses) + ")"


def route_values(catalog: Catalog, side: RouteSide, *, ignore_order: bool = False) -> list[str]:
    if not side:
        return []
    if ignore_order:
        return catalog.route_index_sorted.get(side.sorted_key, [])
    return catalog.route_index.get(side.key, [])


def build_steps(
    catalog: Catalog,
    *,
    partner_groups: list[list[str]],
    origin: RouteSide,
    destinasi: RouteSide,
    trucks: list[str],
) -> list[QueryStep]:
    p_all = partner_clause(partner_groups, require_all=True)
    p_any = partner_clause(partner_groups, require_all=False)
    o = in_filter("origin", route_values(catalog, origin))
    d = in_filter("destinasi", route_values(catalog, destinasi))
    o_any = in_filter("origin", route_values(catalog, origin, ignore_order=True))
    d_any = in_filter("destinasi", route_values(catalog, destinasi, ignore_order=True))
    t = in_filter("truck_type", trucks)

    steps: list[QueryStep] = []
    seen: set[str] = set()

    def add(name: str, parts: list[str], *, need: list[str]) -> None:
        if not all(need):
            return
        expr = _all_of([BASE_FILTER, *parts])
        if expr == BASE_FILTER or expr in seen:
            return
        seen.add(expr)
        steps.append(QueryStep(name=name, filter_expr=expr))

    add("eksak", [p_all, o, d, t], need=[p_all, o, d, t])
    add("tanpa_urutan", [p_all, o_any, d_any, t], need=[p_all, o_any, d_any, t])
    add("tanpa_destinasi", [p_all, o_any, t], need=[p_all, o_any, t])
    add("tanpa_origin", [p_all, d_any, t], need=[p_all, d_any, t])
    add("tanpa_truck", [p_all, o, d], need=[p_all, o, d])

    if p_any != p_all:
        add("mitra_or_eksak", [p_any, o, d, t], need=[p_any, o, d, t])
        add("mitra_or_tanpa_truck", [p_any, o, d], need=[p_any, o, d])
        add("mitra_or_tanpa_destinasi", [p_any, o_any, t], need=[p_any, o_any, t])
        add("mitra_or_tanpa_origin", [p_any, d_any, t], need=[p_any, d_any, t])

    if not o and not d:
        add("mitra_saja", [p_any], need=[p_any])
    return steps


def execute(
    catalog: Catalog,
    *,
    partner_groups: list[list[str]],
    origin: RouteSide,
    destinasi: RouteSide,
    trucks: list[str],
) -> QueryOutcome:
    outcome = QueryOutcome()
    steps = build_steps(
        catalog,
        partner_groups=partner_groups,
        origin=origin,
        destinasi=destinasi,
        trucks=trucks,
    )
    for step in steps:
        outcome.steps_tried.append(step.name)
        result = meili_service.search(
            cfg.index,
            filter_expr=step.filter_expr,
            limit=cfg.search_limit,
        )
        if result.hits:
            outcome.hits = result.hits
            outcome.estimated_total = result.estimated_total
            outcome.step = step.name
            logger.info("rates: langkah %r menghasilkan %d baris", step.name, len(result.hits))
            return outcome

    logger.info("rates: semua langkah kosong (%s)", ", ".join(outcome.steps_tried) or "tidak ada")
    return outcome


def _match_cardinality(
    hits: list[dict[str, Any]],
    field_name: str,
    want_multi: bool,
) -> list[dict[str, Any]]:
    """Saring hit sesuai kardinalitas sisi rute (single vs multi).

    Simetris untuk origin dan destinasi: rute multi disaring keluar dari
    pencarian single, dan sebaliknya. Jika kelompok yang diinginkan kosong,
    semua hit dikembalikan apa adanya (fallback, bukan penyaringan paksa).
    """
    preferred = [h for h in hits if ("+" in (h.get(field_name) or "")) == want_multi]
    return preferred or hits


def sort_hits(
    hits: list[dict[str, Any]],
    *,
    origin: RouteSide,
    destinasi: RouteSide,
    origin_raw: str = "",
    destinasi_raw: str = "",
    partners: list[str],
    trucks: list[str],
) -> list[dict[str, Any]]:
    o_key = origin.key
    d_key = destinasi.key
    partner_set = {p.upper() for p in partners}
    truck_set = {t.upper() for t in trucks}

    def score(hit: dict[str, Any]) -> tuple:
        points = 0
        ho = parse_db_side(hit.get("origin") or "").key
        hd = parse_db_side(hit.get("destinasi") or "").key
        if o_key and ho == o_key:
            points += 40
        if d_key and hd == d_key:
            points += 40
        if normalize_upper(hit.get("customer_nama")) in partner_set:
            points += 30
        if normalize_upper(hit.get("expedisi_nama")) in partner_set:
            points += 30
        if normalize_upper(hit.get("truck_type")) in truck_set:
            points += 20
        if str(hit.get("status") or "").lower() == "published":
            points += 5
        return (
            -points,
            ho,
            hd,
            normalize_upper(hit.get("truck_type")),
            parse_numeric(hit.get("id")),
            str(hit.get("id") or ""),
        )

    origin_multi = ("+" in origin_raw) or (len(origin.codes) > 1)
    dest_multi = ("+" in destinasi_raw) or (len(destinasi.codes) > 1)

    filtered = _match_cardinality(hits, "origin", origin_multi)
    filtered = _match_cardinality(filtered, "destinasi", dest_multi)

    return sorted(filtered, key=score)
