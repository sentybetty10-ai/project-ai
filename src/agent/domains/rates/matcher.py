from __future__ import annotations

import logging
import re

from src.agent.domains.rates.catalog import Catalog, get_catalog
from src.agent.domains.rates.grammar import (
    RouteSide,
    normalize_code,
    split_trailing_number,
    split_user_segments,
    strip_noise,
)
from src.agent.domains.rates.types import EntityMatch, cfg
from src.agent.services.meili import meili_service
from src.agent.utils.text import (
    STOP_WORDS,
    acronym,
    drop_stop_words,
    normalize_key,
    normalize_whitespace,
    partner_core_similarity,
    string_similarity,
)

logger = logging.getLogger("gyntrans.domains.rates.matcher")

_CITY_MIN_RATIO = 0.78
_CITY_MIN_SKELETON = 0.80
_PARTNER_MIN = 0.75
_PARTNER_BAND = 0.05
_TRUCK_MIN = 0.80

# Pagar untuk tangga Meilisearch: tanpa ini, hit pertama apa pun diterima
# mentah dan kata asing bisa terpaut paksa ke kota yang salah.
_MEILI_MIN_RANKING = 0.5
_MEILI_MIN_SIMILARITY = 0.5


def _city_exact(cat: Catalog, base: str) -> EntityMatch | None:
    hit = cat.cities.exact(base)
    return EntityMatch(hit, "kota_eksak", 1.0) if hit else None


def _city_skeleton_exact(cat: Catalog, base: str) -> EntityMatch | None:
    found = cat.cities.by_skeleton(base)
    if len(found) == 1:
        return EntityMatch(found[0], "kota_skeleton_eksak", 0.95)
    return None


def _city_nearest(cat: Catalog, base: str) -> EntityMatch | None:
    found = cat.cities.nearest(base, _CITY_MIN_RATIO)
    return EntityMatch(found[0], "kota_dekat", found[1]) if found else None


def _city_skeleton_nearest(cat: Catalog, base: str) -> EntityMatch | None:
    found = cat.cities.nearest_skeleton(base, _CITY_MIN_SKELETON)
    return EntityMatch(found[0], "kota_skeleton_dekat", found[1]) if found else None


def _city_meili(cat: Catalog, base: str) -> EntityMatch | None:
    probe = normalize_key(base)
    if not probe or probe in cat.meili_misses:
        return None

    result = meili_service.search(
        cfg.index_lokasi,
        base,
        attributes_to_search_on=["alamat_lengkap", "alamat_tujuan"],
        limit=5,
        with_ranking_score=True,
    )
    for hit in result.hits:
        candidate, _ = split_trailing_number(normalize_code(hit.get("alamat_tujuan") or ""))
        if not candidate or candidate not in cat.cities:
            continue
        ranking = hit.get("_rankingScore")
        if ranking is not None:
            if ranking < _MEILI_MIN_RANKING:
                continue
        elif (
            max(
                string_similarity(base, str(hit.get("alamat_lengkap") or "")),
                string_similarity(base, candidate),
            )
            < _MEILI_MIN_SIMILARITY
        ):
            continue
        return EntityMatch(candidate, "kota_meili", 0.70)

    # Cache negatif: kata yang sudah pasti gagal tidak ditanyakan lagi ke
    # Meilisearch selama katalog ini hidup.
    cat.meili_misses.add(probe)
    return None


def resolve_city(
    segment: str,
    catalog: Catalog | None = None,
    *,
    allow_meili: bool = True,
) -> EntityMatch | None:
    cat = catalog or get_catalog()
    base_raw, number = split_trailing_number(strip_noise(segment))
    base = drop_stop_words(base_raw)
    if len(base) < 3:
        return None

    words = base.split()
    if len(words) > 1:
        match = _city_exact(cat, base)
    else:
        match = (
            _city_exact(cat, base)
            or _city_skeleton_exact(cat, base)
            or _city_nearest(cat, base)
            or _city_skeleton_nearest(cat, base)
            or (_city_meili(cat, base) if allow_meili else None)
        )

    if match is None:
        return None

    code = normalize_code(f"{match.value} {number}") if number else match.value
    if code not in cat.city_codes:
        return None
    res = EntityMatch(value=code, strategy=match.strategy, score=match.score)
    logger.debug("matcher.city: %r -> %s via %s (skor=%.2f)", segment, res.value, res.strategy, res.score)
    return res


def resolve_route_side(text: str, catalog: Catalog | None = None) -> tuple[RouteSide, list[str]]:
    cat = catalog or get_catalog()
    raw = strip_noise(text)
    if not raw:
        return RouteSide(), []

    segments = split_user_segments(raw)
    if not segments:
        return RouteSide(), []

    resolved_segments: list[EntityMatch | None] = []
    all_candidates: list[tuple[EntityMatch, str]] = []
    all_leftovers: list[str] = []

    for seg in segments:
        # Meilisearch maksimal satu kali per segmen, tidak per kata.
        match = resolve_city(seg, cat)
        if match:
            resolved_segments.append(match)
            all_candidates.append((match, seg))
            continue

        resolved_segments.append(None)
        words = seg.split()
        if len(words) > 1:
            seg_candidates: list[tuple[EntityMatch, str]] = []
            leftover_words: list[str] = []
            for w in words:
                w_match = resolve_city(w, cat, allow_meili=False)
                if w_match:
                    seg_candidates.append((w_match, w))
                elif w.upper() not in STOP_WORDS:
                    leftover_words.append(w)

            if seg_candidates:
                best_sub, best_w = seg_candidates[0]
                all_candidates.append((best_sub, best_w))
                for _, other_w in seg_candidates[1:]:
                    leftover_words.append(other_w)
                if leftover_words:
                    all_leftovers.append(" ".join(leftover_words))
            else:
                all_leftovers.append(seg)
        else:
            if seg.upper() not in STOP_WORDS:
                all_leftovers.append(seg)

    valid_matches = [m for m in resolved_segments if m is not None]

    has_connector = bool(re.search(r"\b(?:dan|\+)\b", raw, re.IGNORECASE))
    has_dash = "-" in raw and not bool(re.search(r"[()]", raw))
    has_explicit_multi = has_connector or has_dash

    multi_codes = [m.value for m in valid_matches]
    multi_key = "+".join(multi_codes)
    multi_sorted = "+".join(sorted(multi_codes))
    is_in_db_routes = multi_key in cat.route_index or multi_sorted in cat.route_index_sorted

    if len(valid_matches) == len(segments) and len(segments) > 1:
        if has_explicit_multi or is_in_db_routes:
            return RouteSide(tuple(multi_codes)), all_leftovers

    if len(all_candidates) > 1:
        has_comma = "," in raw
        if has_explicit_multi or has_comma or is_in_db_routes:
            cand_codes = [m.value for m, _ in all_candidates]
            cand_key = "+".join(cand_codes)
            cand_sorted = "+".join(sorted(cand_codes))
            if cand_key in cat.route_index or cand_sorted in cat.route_index_sorted:
                return RouteSide(tuple(cand_codes)), all_leftovers

    if not all_candidates:
        return RouteSide(), all_leftovers

    def candidate_key(item: tuple[EntityMatch, str]) -> tuple[int, int, int, float, int]:
        m, s = item
        in_routes = 1 if m.value in cat.route_index else 0
        is_exact = 1 if m.strategy == "kota_eksak" else 0
        in_paren = bool(re.search(rf"\([^)]*{re.escape(s)}[^)]*\)", raw))
        not_in_paren = 0 if in_paren else 1
        return (in_routes, not_in_paren, is_exact, m.score, len(s))

    all_candidates.sort(key=candidate_key, reverse=True)
    best_match, best_seg = all_candidates[0]
    codes = [best_match.value]
    for _, s in all_candidates[1:]:
        all_leftovers.append(s)

    return RouteSide(tuple(codes)), all_leftovers


def resolve_partner(text: str, catalog: Catalog | None = None) -> list[EntityMatch]:
    cat = catalog or get_catalog()
    probe = normalize_whitespace(text)
    if len(probe) < 2:
        return []

    cluster = cat.partners.cluster(probe)
    if cluster:
        logger.debug("matcher.partner: %r -> eksak cluster (%d nama)", text, len(cluster))
        return [EntityMatch(name, "mitra_eksak", 1.0) for name in cluster]

    pool = cat.partners.prefix_candidates(probe) or cat.partners.values
    scored = [
        (score, name)
        for score, name in ((partner_core_similarity(probe, n), n) for n in pool)
        if score >= _PARTNER_MIN
    ]
    if not scored:
        return []

    scored.sort(key=lambda item: (-item[0], item[1]))
    top = scored[0][0]
    candidates: list[EntityMatch] = []
    seen: set[str] = set()
    for score, name in scored:
        if score >= top - _PARTNER_BAND:
            for variant in cat.partners.cluster(name) or [name]:
                if variant not in seen:
                    seen.add(variant)
                    candidates.append(EntityMatch(variant, "mitra_kemiripan", score))
        if len(candidates) >= cfg.max_candidates:
            break
    if candidates:
        logger.debug(
            "matcher.partner: %r -> %d kandidat via kemiripan (top_skor=%.2f)",
            text,
            len(candidates),
            top,
        )
    return candidates


def resolve_truck(text: str, catalog: Catalog | None = None) -> list[str]:
    cat = catalog or get_catalog()
    probe = normalize_whitespace(text).upper()
    if not probe:
        return []

    hit = cat.trucks.exact(probe)
    if hit:
        return [hit]

    initials = acronym(probe)
    if initials:
        hit = cat.trucks.exact(initials)
        if hit:
            return [hit]

    tokens = {t for t in probe.split() if t}
    if tokens:
        subset = [c for c in cat.trucks.values if set(c.split()) <= tokens]
        if subset:
            widest = max(len(c.split()) for c in subset)
            return sorted(c for c in subset if len(c.split()) == widest)

    superset = [c for c in cat.trucks.values if tokens <= set(c.split())]
    if superset:
        return sorted(superset)[: cfg.max_candidates]

    found = cat.trucks.nearest(probe, _TRUCK_MIN) or cat.trucks.nearest_skeleton(probe, _TRUCK_MIN)
    res = [found[0]] if found else []
    if res:
        logger.debug("matcher.truck: %r -> %r", text, res)
    return res
