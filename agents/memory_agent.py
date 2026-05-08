"""Agente com memória multi-turn usando LangGraph persistence.

Padrão atual (LangChain 1.x / LangGraph 1.x): ``StateGraph`` com
``MemorySaver`` checkpointer + ``thread_id`` por sessão. Substitui o
``RunnableWithMessageHistory`` deprecated.

Multi-provider via :func:`agents.provider.get_llm`. O ``thread_id``
default ``"streamlit-session"`` é mantido por compatibilidade com o
painel single-user; em UIs multi-tenant, derive o ``thread_id`` da
sessão (mesma estratégia já usada pelo HITL — ver ADR-0002).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agents.provider import Provider, callbacks_config, get_llm


class _MemoryState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


_SYSTEM_PROMPT = "Responda em português. Seja direto e breve — no máximo 2 frases."


def format_response(result: object) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases."""
    if hasattr(result, "content"):
        result = result.content
    text = str(result).replace("\n", " ").strip()
    while ".." in text:
        text = text.replace("..", ".")
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def create_memory_agent(
    provider: Provider = "ollama",
    thread_id: str = "streamlit-session",
) -> Callable[[str], str]:
    """Cria o agente com memória multi-turn via LangGraph persistence.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"``.
        thread_id: Identificador da thread no ``MemorySaver``. Em UIs
            multi-tenant, **derive este valor da sessão** (ver ADR-0002).
            O default ``"streamlit-session"`` é adequado pra demo
            single-user.

    Returns:
        Callable que recebe um prompt e devolve a resposta formatada.
        O histórico acumula sob o ``thread_id`` informado.
    """
    llm = get_llm(provider)

    def _agent_node(state: _MemoryState) -> _MemoryState:
        # System prompt sempre presente; LangGraph não tem ChatPromptTemplate aqui,
        # então prependamos a instrução manualmente quando ainda não foi enviada.
        msgs = state["messages"]
        if not msgs or not isinstance(msgs[0], SystemMessage):
            msgs = [SystemMessage(content=_SYSTEM_PROMPT), *msgs]
        response = llm.invoke(msgs)
        return {"messages": [response]}

    graph = StateGraph(_MemoryState)
    graph.add_node("agent", _agent_node)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)

    compiled = graph.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": thread_id}}

    def run(prompt_text: str) -> str:
        merged_config = {**config, **callbacks_config()}
        result = compiled.invoke(  # type: ignore[call-overload]
            {"messages": [HumanMessage(content=prompt_text)]},
            config=merged_config,
        )
        last_msg = result["messages"][-1]
        return format_response(last_msg)

    return run
