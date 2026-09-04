from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from src.agent.domains.rates.grammar import (
    normalize_code,
    parse_db_side,
    split_trailing_number,
)
from src.agent.domains.rates.types import cfg
from src.agent.services.directus import directus_service
from src.agent.services.meili import meili_service
from src.agent.utils.text import (
    consonant_skeleton,
    normalize_key,
    normalize_upper as _up,
    ratio,
    strip_entity_prefix,
    tokenize,
)

logger = logging.getLogger("gyntrans.domains.rates.catalog")

_RATE_SCAN_FIELDS = ["origin", "destinasi", "customer_nama", "expedisi_nama", "truck_type"]
_LOCATION_FIELDS = ["alamat_tujuan", "alamat_lengkap"]
_FAILED_RETRY_COOLDOWN = 30.0


class LookupTable:
    def __init__(self) -> None:
        self._exact: dict[str, str] = {}
        self._cluster: dict[str, set[str]] = defaultdict(set)
        self._skeleton: dict[str, list[str]] = defaultdict(list)
        self._prefix: dict[str, set[str]] = defaultdict(set)
        self._canonical: set[str] = set()
        self._canonical_sorted: list[str] | None = None

    def add(self, canonical: str, aliases: Iterable[str] = ()) -> None:
        canonical = _up(canonical)
        if not canonical:
            return
        self._canonical.add(canonical)
        self._canonical_sorted = None
        self._cluster[normalize_key(canonical)].add(canonical)
        for alias in {canonical, *(_up(a) for a in aliases)}:
            if not alias:
                continue
            key = normalize_key(alias)
            self._exact.setdefault(key, canonical)
            self._cluster[key].add(canonical)
            skeleton = consonant_skeleton(alias)
            if len(skeleton) >= 3 and canonical not in self._skeleton[skeleton]:
                self._skeleton[skeleton].append(canonical)
            for token in tokenize(alias, exclude_stop_words=False):
                if len(token) >= 3:
                    self._prefix[token[:3]].add(canonical)

    def __contains__(self, value: object) -> bool:
        return _up(value) in self._canonical

    def __len__(self) -> int:
        return len(self._canonical)

    @property
    def values(self) -> list[str]:
        if self._canonical_sorted is None:
            self._canonical_sorted = sorted(self._canonical)
        return self._canonical_sorted

    def exact(self, text: str) -> str | None:
        return self._exact.get(normalize_key(text))

    def cluster(self, text: str) -> list[str]:
        key = normalize_key(text)
        if not key:
            return []
        found = self._cluster.get(key)
        if found:
            return sorted(found)
        exact_match = self._exact.get(key)
        return [exact_match] if exact_match else []

    def by_skeleton(self, text: str) -> list[str]:
        skeleton = consonant_skeleton(text)
        if len(skeleton) < 3:
            return []
        return sorted(self._skeleton.get(skeleton, []))

    def prefix_candidates(self, text: str) -> list[str]:
        found: set[str] = set()
        for token in tokenize(text, exclude_stop_words=False):
            if len(token) >= 3:
                found |= self._prefix.get(token[:3], set())
        return sorted(found)

    def nearest(self, text: str, min_score: float) -> tuple[str, float] | None:
        probe = normalize_key(text)
        if not probe:
            return None
        best: tuple[str, float] | None = None
        for canonical in self.values:
            score = ratio(probe, normalize_key(canonical))
            if score >= min_score and (best is None or score > best[1]):
                best = (canonical, score)
        return best

    def nearest_skeleton(self, text: str, min_score: float) -> tuple[str, float] | None:
        probe = consonant_skeleton(text)
        if len(probe) < 3:
            return None
        best: tuple[str, float] | None = None
        for skeleton in sorted(self._skeleton):
            score = ratio(probe, skeleton)
            if score >= min_score and (best is None or score > best[1]):
                best = (sorted(self._skeleton[skeleton])[0], score)
        return best


@dataclass
class Catalog:
    cities: LookupTable = field(default_factory=LookupTable)
    city_codes: set[str] = field(default_factory=set)
    partners: LookupTable = field(default_factory=LookupTable)
    trucks: LookupTable = field(default_factory=LookupTable)
    route_index: dict[str, list[str]] = field(default_factory=dict)
    route_index_sorted: dict[str, list[str]] = field(default_factory=dict)
    unparsed_routes: list[str] = field(default_factory=list)
    loaded_at: float = 0.0
    ok: bool = False


def _synonym_map(raw: dict[str, list[str]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for key, targets in (raw or {}).items():
        k = _up(key)
        if not k:
            continue
        for target in targets or []:
            t = _up(target)
            if not t:
                continue
            out[k].add(t)
            out[t].add(k)
    return out


def build_catalog(
    *,
    locations: list[dict],
    rate_rows: list[dict],
    synonyms: dict[str, list[str]] | None = None,
) -> Catalog:
    syn = _synonym_map(synonyms or {})

    cities = LookupTable()
    city_codes: set[str] = set()
    bases: dict[str, set[str]] = defaultdict(set)

    for row in locations:
        code = normalize_code(row.get("alamat_tujuan") or "")
        name = _up(row.get("alamat_lengkap") or "")
        if not code:
            continue
        city_codes.add(code)
        base, number = split_trailing_number(code)
        if not base:
            continue
        bases.setdefault(base, set())
        if not number and name:
            bases[base].add(name)

    for base, names in bases.items():
        aliases = set(names)
        for word in (base, *names):
            aliases |= syn.get(word, set())
        cities.add(base, aliases)

    route_sets: dict[str, set[str]] = defaultdict(set)
    route_sorted_sets: dict[str, set[str]] = defaultdict(set)
    seen_routes: set[str] = set()
    unparsed: set[str] = set()
    partner_names: set[str] = set()
    truck_names: set[str] = set()

    for row in rate_rows:
        for name in (_up(row.get("customer_nama")), _up(row.get("expedisi_nama"))):
            if name:
                partner_names.add(name)
        truck = _up(row.get("truck_type"))
        if truck:
            truck_names.add(truck)
        for raw in (_up(row.get("origin")), _up(row.get("destinasi"))):
            if not raw or raw in seen_routes:
                continue
            seen_routes.add(raw)
            if not any(c.isalnum() for c in raw):
                continue
            side = parse_db_side(raw)
            if not side:
                unparsed.add(raw)
                continue
            route_sets[side.key].add(raw)
            route_sorted_sets[side.sorted_key].add(raw)

    core_to_names: dict[str, set[str]] = defaultdict(set)
    for name in partner_names:
        core = strip_entity_prefix(name)
        if core and (len(core) >= 5 or " " in core):
            core_to_names[core].add(name)

    partners = LookupTable()
    for name in sorted(partner_names):
        core = strip_entity_prefix(name)
        cluster_aliases: set[str] = set()
        if core and (len(core) >= 5 or " " in core):
            cluster_aliases = core_to_names.get(core, set()) - {name}
        aliases = {core} | cluster_aliases
        partners.add(name, aliases)

    trucks = LookupTable()
    for name in sorted(truck_names):
        aliases = set()
        words = name.split()
        if len(words) >= 2:
            aliases.add("".join(w[0] for w in words))
            aliases.add(words[0] + "".join(w[0] for w in words[1:]))
            aliases.add(words[0] + "-" + "".join(w[0] for w in words[1:]))
        trucks.add(name, aliases)

    if unparsed:
        logger.warning(
            "Nilai rute tidak bisa di-parse (%d). Contoh: %s",
            len(unparsed), sorted(unparsed)[:20],
        )

    return Catalog(
        cities=cities,
        city_codes=city_codes,
        partners=partners,
        trucks=trucks,
        route_index={k: sorted(v) for k, v in route_sets.items()},
        route_index_sorted={k: sorted(v) for k, v in route_sorted_sets.items()},
        unparsed_routes=sorted(unparsed),
        loaded_at=time.time(),
        ok=bool(city_codes) and bool(route_sets),
    )


def _load_locations() -> list[dict]:
    docs = meili_service.get_documents(
        cfg.index_lokasi, fields=_LOCATION_FIELDS, batch_size=cfg.catalog_batch_size,
    )
    if docs:
        return docs
    logger.warning("kode_destinasi kosong dari Meilisearch, beralih ke Directus")
    return directus_service.get_all_items("kode_destinasi", fields=_LOCATION_FIELDS)


def _fetch_catalog() -> Catalog:
    locations = _load_locations()
    rate_rows = meili_service.get_documents(
        cfg.index, fields=_RATE_SCAN_FIELDS, batch_size=cfg.catalog_batch_size,
    )
    synonyms = meili_service.get_synonyms(cfg.index_lokasi)

    catalog = build_catalog(locations=locations, rate_rows=rate_rows, synonyms=synonyms)
    if catalog.ok:
        logger.info(
            "Katalog rates dimuat: %d kode kota, %d kunci rute, %d mitra, %d armada",
            len(catalog.city_codes), len(catalog.route_index),
            len(catalog.partners), len(catalog.trucks),
        )
    else:
        logger.error(
            "Katalog rates gagal dimuat (kota=%d, rute=%d)",
            len(catalog.city_codes), len(catalog.route_index),
        )
    return catalog


_LOCK = threading.RLock()
_CATALOG: Catalog | None = None
_LAST_FAILED_AT: float = 0.0


def get_catalog(*, force: bool = False) -> Catalog:
    global _CATALOG, _LAST_FAILED_AT
    with _LOCK:
        now = time.time()
        if not force and _CATALOG is not None:
            if _LAST_FAILED_AT and (now - _LAST_FAILED_AT) < _FAILED_RETRY_COOLDOWN:
                return _CATALOG

            age = now - _CATALOG.loaded_at
            if _CATALOG.ok and age < cfg.catalog_ttl_seconds:
                return _CATALOG
            if not _CATALOG.ok and age < _FAILED_RETRY_COOLDOWN:
                return _CATALOG

        built = _fetch_catalog()
        if built.ok or _CATALOG is None:
            _CATALOG = built
            _LAST_FAILED_AT = 0.0
        else:
            _LAST_FAILED_AT = now
        return _CATALOG


def set_catalog(catalog: Catalog) -> None:
    global _CATALOG, _LAST_FAILED_AT
    with _LOCK:
        _CATALOG = catalog
        _LAST_FAILED_AT = 0.0


def reset_catalog() -> None:
    global _CATALOG, _LAST_FAILED_AT
    with _LOCK:
        _CATALOG = None
        _LAST_FAILED_AT = 0.0
