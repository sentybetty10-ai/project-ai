from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, trim_messages
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.model import SYSTEM_PROMPT, model
from src.agent.state import AgentState
from src.agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

_MAX_HISTORY = 20

_tool_node = ToolNode(ALL_TOOLS)
model_with_tools = model.bind_tools(ALL_TOOLS)


def _history(messages: list) -> list:
    return trim_messages(
        messages,
        strategy="last",
        max_tokens=_MAX_HISTORY,
        token_counter=len,
        start_on="human",
        allow_partial=False,
    )


def node_agent(state: AgentState) -> dict[str, Any]:
    prompt = SYSTEM_PROMPT
    slots = state.get("slots")
    if slots:
        prompt += (
            "\n\n## KONTEKS SLOT TERAKTUAL\n"
            "Hasil resolusi slot dari pemanggilan tool sebelumnya. Jika pesan "
            "terbaru user hanya melengkapi slot yang kurang atau menanyakan tindak lanjut "
            "untuk pengiriman yang sama, gabungkan dengan konteks ini; jika user jelas "
            "memulai permintaan pengiriman baru atau merujuk pengiriman lain di riwayat chat, "
            "gunakan data pengiriman yang dimaksud.\n" + json.dumps(slots, ensure_ascii=False)
        )

    messages = [SystemMessage(content=prompt)] + _history(state["messages"])

    try:
        response = model_with_tools.invoke(messages)
    except Exception:
        logger.exception("LLM invoke error")
        response = AIMessage(
            content="Maaf, sedang ada gangguan saat memproses permintaan. Silakan coba lagi."
        )

    return {"messages": [response]}


def _tool_payload(message: Any) -> dict[str, Any] | None:
    content = getattr(message, "content", None)
    if not isinstance(content, str) or not content:
        return None
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def node_tools(state: AgentState) -> dict[str, Any]:
    result = _tool_node.invoke(state)
    updates: dict[str, Any] = {"messages": result["messages"]}

    for message in result["messages"]:
        # content_and_artifact: JSON lengkap ada di artifact (hemat token);
        # fallback baca content untuk tool lama tanpa artifact.
        data = getattr(message, "artifact", None)
        if not isinstance(data, dict):
            data = _tool_payload(message)
        if not data:
            continue
        updates["last_result"] = data
        resolved = data.get("resolved")
        if isinstance(resolved, dict) and resolved:
            # Jika turn sebelumnya butuh klarifikasi, gabungkan slot untuk slot-filling.
            # Jika transaksi baru / sudah tuntas, gunakan resolved saat ini sebagai state bersih.
            prev_result = state.get("last_result") or {}
            is_clarification = prev_result.get("status") == "needs_clarification"

            if is_clarification:
                merged = {**state.get("slots", {})}
                merged.update({k: v for k, v in resolved.items() if v})
                updates["slots"] = merged
            else:
                updates["slots"] = {k: v for k, v in resolved.items() if v}

    return updates


def route_after_agent(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def build_graph(checkpointer=None):
    """Bangun graf ReAct. Saat dijalankan via LangGraph Server, checkpointer
    dikelola otomatis oleh server. Untuk pemakaian standalone, suntikkan
    secara eksplisit, mis. build_graph(checkpointer=InMemorySaver()) atau
    PostgresSaver saat fase produksi nanti."""
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", node_agent)
    workflow.add_node("tools", node_tools)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", route_after_agent, ["tools", END])
    workflow.add_edge("tools", "agent")
    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
