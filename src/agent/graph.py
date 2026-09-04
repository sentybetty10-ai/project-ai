import logging

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from src.agent.model import SYSTEM_PROMPT, model
from src.agent.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

tools = ALL_TOOLS
node_tools = ToolNode(tools)
model_with_tools = model.bind_tools(tools)


def node_agent(state: MessagesState):
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    try:
        response = model_with_tools.invoke(messages)
    except Exception as e:
        logger.error("LLM invoke error: %s", e)
        response = AIMessage(
            content=f"Maaf, terjadi gangguan saat memproses permintaan. Silakan coba lagi. ({type(e).__name__})"
        )

    return {"messages": [response]}


def route_after_agent(state: MessagesState):
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


workflow = StateGraph(MessagesState)

workflow.add_node("agent", node_agent)
workflow.add_node("tools", node_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", route_after_agent, ["tools", END])
workflow.add_edge("tools", "agent")

graph = workflow.compile()
