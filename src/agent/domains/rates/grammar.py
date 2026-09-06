from __future__ import annotations

import re
from dataclasses import dataclass

from src.agent.utils.text import normalize_whitespace

_NOISE_WORDS = (
    "titik",
    "titk",
    "ttik",
    "tttik",
    "ttk",
    "zona",
    "zone",
    "point",
    "poin",
    "drop",
)
_NOISE_RE = re.compile(r"\b(?:" + "|".join(_NOISE_WORDS) + r")\b", re.IGNORECASE)
_USER_SPLIT_RE = re.compile(r"\s*(?:\+|,|;|/|\(|\)|\bdan\b|-)\s*", re.IGNORECASE)
_DB_SPLIT_RE = re.compile(r"\s*\+\s*")
_TRAILING_NUM_RE = re.compile(r"^(.*?)\s*(\d{1,2})$")
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


@dataclass(frozen=True)
class RouteSide:
    codes: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.codes)

    def __len__(self) -> int:
        return len(self.codes)

    @property
    def key(self) -> str:
        return "+".join(self.codes)

    @property
    def sorted_key(self) -> str:
        return "+".join(sorted(self.codes))

    @property
    def is_multi(self) -> bool:
        return len(self.codes) > 1


def normalize_code(text: str) -> str:
    t = normalize_whitespace(text).upper()
    if not t:
        return ""
    m = _TRAILING_NUM_RE.match(t)
    if m and m.group(1).strip():
        return f"{m.group(1).strip()} {int(m.group(2))}"
    return t


def split_trailing_number(code: str) -> tuple[str, str]:
    t = normalize_code(code)
    m = _TRAILING_NUM_RE.match(t)
    if m and m.group(1).strip():
        return m.group(1).strip(), str(int(m.group(2)))
    return t, ""


def strip_noise(text: str) -> str:
    cleaned = _URL_RE.sub(" ", str(text or ""))
    return normalize_whitespace(_NOISE_RE.sub(" ", cleaned))


def parse_db_side(value: str) -> RouteSide:
    parts = [normalize_code(p) for p in _DB_SPLIT_RE.split(str(value or ""))]
    return RouteSide(tuple(p for p in parts if p))


def split_user_segments(text: str) -> list[str]:
    cleaned = strip_noise(text)
    if not cleaned:
        return []
    return [s.strip() for s in _USER_SPLIT_RE.split(cleaned) if s and s.strip()]
