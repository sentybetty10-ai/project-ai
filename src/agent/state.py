from __future__ import annotations

from typing import Any, NotRequired

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """State graf: riwayat pesan + slot hasil resolusi tool terakhir.

    `slots` dan `last_result` ditulis oleh node_tools dari payload tool,
    sehingga konteks slot menempel lintas turn (slot filling) dan tidak
    bergantung pada ingatan LLM semata.

    Keduanya NotRequired karena di turn pertama belum tersedia.
    """

    slots: NotRequired[dict[str, Any]]
    last_result: NotRequired[dict[str, Any] | None]
