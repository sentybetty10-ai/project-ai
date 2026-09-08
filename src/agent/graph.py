from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, trim_messages
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import RetryPolicy

from src.agent.model import SYSTEM_PROMPT, model
from src.agent.state import AgentState
from src.agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# Estimasi token maksimum yang boleh masuk ke konteks LLM.
# Karakter ÷ 4 adalah pendekatan standar saat tidak ada tokenizer Gemini langsung.
_MAX_TOKENS = 4000

_tool_node = ToolNode(ALL_TOOLS)
model_with_tools = model.bind_tools(ALL_TOOLS)

# RetryPolicy untuk node — aktif hanya jika exception keluar dari node.
# Default retry semua Exception kecuali ValueError/TypeError/SyntaxError.
_retry = RetryPolicy(
    max_attempts=3,
    initial_interval=1.0,
    backoff_factor=2.0,
)


def _count_tokens(messages: list) -> int:
    """Estimasi token berdasarkan panjang karakter ÷ 4."""
    total = 0
    for m in messages:
        content = getattr(m, "content", "") or ""
        if isinstance(content, str):
            total += max(1, len(content) // 4)
        elif isinstance(content, list):
            for c in content:
                if isinstance(c, dict):
                    total += max(1, len(str(c.get("text", ""))) // 4)
    return total


def _history(messages: list) -> list:
    return trim_messages(
        messages,
        strategy="last",
        max_tokens=_MAX_TOKENS,
        token_counter=_count_tokens,
        start_on="human",
        allow_partial=False,
    )


async def node_agent(state: AgentState) -> dict[str, Any]:
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

    # Lempar exception ke atas agar RetryPolicy aktif — JANGAN tangkap Exception umum di sini.
    response = await model_with_tools.ainvoke(messages)

    # Opsi B: LLM tetap jalan, tapi pastikan blok formatted tersalin.
    # Jika formatted ada tapi tidak muncul di response, tambahkan di akhir.
    last_result = state.get("last_result") or {}
    formatted = last_result.get("formatted", "")
    if formatted and isinstance(response.content, str):
        # Cek keberadaan tanda khas blok formatted (huruf "Rp" atau "Rute:")
        if "Rute:" not in response.content and "Rp" not in response.content:
            logger.warning("LLM tidak menyalin blok formatted — ditambahkan ke respons")
            new_content = (response.content.rstrip() + "\n\n" + formatted) if response.content else formatted
            response = AIMessage(content=new_content, id=response.id)

    return {"messages": [response]}


async def node_tools(state: AgentState) -> dict[str, Any]:
    result = await _tool_node.ainvoke(state)
    updates: dict[str, Any] = {"messages": result["messages"]}

    for message in result["messages"]:
        # content_and_artifact: JSON lengkap ada di artifact (hemat token);
        # fallback ke content untuk tool lama tanpa artifact.
        data = getattr(message, "artifact", None)
        if not isinstance(data, dict):
            data = None
        if not data:
            continue
        data_clean = dict(data)
        resolved = data_clean.pop("resolved", None)
        updates["last_result"] = data_clean
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
    workflow.add_node("agent", node_agent, retry_policy=_retry)
    workflow.add_node("tools", node_tools, retry_policy=_retry)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", route_after_agent, ["tools", END])
    workflow.add_edge("tools", "agent")
    return workflow.compile(checkpointer=checkpointer)


graph = build_graph()
