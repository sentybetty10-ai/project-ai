from __future__ import annotations

import re
from typing import Any

_ENTITY_PREFIXES: frozenset[str] = frozenset({
    "PT", "CV", "UD", "TB", "PD", "FA", "KOPERASI", "FIRMA", "PERUSAHAAN",
    "PAK", "BAPAK", "IBU", "BU", "BPK",
})

STOP_WORDS: frozenset[str] = frozenset({
    "PT", "CV", "UD", "TB", "PD", "AND", "THE", "FOR", "OF", "OR",
    "JL", "JLN", "JALAN", "GANG", "GG", "NO",
    "INDONESIA", "TRADING",
    "JAWA", "TENGAH", "BARAT", "TIMUR", "SELATAN", "UTARA", "CENTRAL", "JAVA",
    "PROV", "PROVINSI", "REGENCY", "KOTA", "KAB", "KABUPATEN",
    "KECAMATAN", "KELURAHAN", "DESA",
    "PAK", "BAPAK", "IBU", "BU", "BPK",
})


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def normalize_upper(value: object) -> str:
    return normalize_whitespace(str(value or "")).upper()


def normalize_key(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", normalize_whitespace(text).upper())


def parse_numeric(val: Any) -> int:
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return 0


def tokenize(text: str, min_length: int = 2, exclude_stop_words: bool = True) -> list[str]:
    if not text:
        return []
    raw = [
        w.upper()
        for w in re.split(r"[\s,.\-/()\[\]+]+", str(text).strip())
        if len(w) >= min_length
    ]
    if exclude_stop_words:
        return [w for w in raw if w not in STOP_WORDS]
    return raw


def drop_stop_words(text: str) -> str:
    kept = [w for w in normalize_whitespace(text).upper().split() if w not in STOP_WORDS]
    return " ".join(kept)


def acronym(text: str) -> str:
    words = [w for w in normalize_whitespace(text).upper().split() if w]
    return "".join(w[0] for w in words) if len(words) > 1 else ""


def levenshtein_distance(s1: str, s2: str) -> int:
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0 = v1[:]

    return v1[len(s2)]


def ratio(probe: str, target: str) -> float:
    if not probe or not target:
        return 0.0
    if probe == target:
        return 1.0
    longest = max(len(probe), len(target))
    return max(0.0, 1.0 - (levenshtein_distance(probe, target) / longest))


def string_similarity(s1: str, s2: str) -> float:
    return ratio(normalize_key(s1), normalize_key(s2))


def consonant_skeleton(text: str) -> str:
    cleaned = re.sub(r"[^A-Z]", "", normalize_whitespace(text).upper())
    return re.sub(r"[AEIOU]", "", cleaned)


def strip_entity_prefix(text: str) -> str:
    parts = normalize_whitespace(text).upper().replace(".", " ").split()
    stripped = [w for w in parts if w not in _ENTITY_PREFIXES]
    return " ".join(stripped) if stripped else normalize_whitespace(text).upper()


def partner_core_similarity(raw_user: str, db_val: str) -> float:
    core_user = strip_entity_prefix(raw_user)
    core_db = strip_entity_prefix(db_val)
    full_sim = string_similarity(raw_user, db_val)
    core_sim = string_similarity(core_user, core_db)

    u_tokens = tokenize(core_user)
    d_tokens = tokenize(core_db)
    if not u_tokens or not d_tokens:
        return max(full_sim, core_sim)

    total = 0.0
    for ut in u_tokens:
        total += max(string_similarity(ut, dt) for dt in d_tokens)
    avg_token_sim = total / len(u_tokens)

    db_coverage = 0.0
    if d_tokens:
        db_total = 0.0
        all_matched = True
        for dt in d_tokens:
            best_sim = max(string_similarity(dt, ut) for ut in u_tokens)
            min_req = 1.0 if len(dt) <= 3 else 0.92
            if best_sim >= min_req:
                db_total += best_sim
            else:
                all_matched = False
                break
        if all_matched:
            db_coverage = db_total / len(d_tokens)

    return max(full_sim, core_sim, avg_token_sim, db_coverage)
