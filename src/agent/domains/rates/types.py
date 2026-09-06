from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TOOL_NAME = "tools_rates"


@dataclass(frozen=True)
class RatesConfig:
    index: str = "rates"
    index_lokasi: str = "kode_destinasi"
    max_display: int = 5
    max_candidates: int = 8
    search_limit: int = 60
    catalog_ttl_seconds: float = 900.0
    catalog_batch_size: int = 1000
    # Satu-satunya saklar aturan tampil DP & Uang Jalan di blok formatted.
    include_dp_uang_jalan: bool = True


cfg = RatesConfig()


# Field yang boleh dibaca LLM (content). Sisanya (rates mentah, resolved)
# hanya disimpan di artifact state — tidak dikirim ke model, tidak dibayar token.
_CONTENT_KEYS = (
    "status",
    "message",
    "formatted",
    "has_more",
    "needs_clarification",
    "options",
)


def split_tool_payload(full: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pisahkan payload tool menjadi (content untuk LLM, artifact untuk state)."""
    content = {k: full[k] for k in _CONTENT_KEYS if k in full}
    return content, full


@dataclass(frozen=True)
class EntityMatch:
    value: str
    strategy: str
    score: float = 1.0


@dataclass
class PipelineResult:
    status: str
    message: str = ""
    total_found: int = 0
    displayed_count: int = 0
    has_more: bool = False
    remaining_count: int = 0
    needs_clarification: list[str] = field(default_factory=list)
    options: dict[str, list[str]] = field(default_factory=dict)
    rates: list[dict[str, Any]] = field(default_factory=list)
    matched_step: str = ""
    # Slot hasil resolusi backend; dibaca node_tools untuk memori lintas turn.
    resolved: dict[str, Any] = field(default_factory=dict)
    # Blok jawaban final hasil render deterministik; LLM wajib mengutip persis.
    formatted: str = ""

    def to_tool_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "total_found": self.total_found,
            "displayed_count": self.displayed_count,
            "has_more": self.has_more,
            "remaining_count": self.remaining_count,
            "needs_clarification": self.needs_clarification,
            "options": self.options,
            "rates": self.rates,
            "matched_step": self.matched_step,
            "resolved": self.resolved,
            "formatted": self.formatted,
        }
