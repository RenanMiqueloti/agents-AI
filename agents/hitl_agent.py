"""Agente com Human-in-the-Loop via interrupt() do LangGraph.

Demonstra o padrão interrupt() — o agente pausa antes de executar
ferramentas de alto impacto (ex: enviar e-mail, deletar arquivo) e aguarda
aprovação explícita. O estado é preservado via MemorySaver (checkpointing),
e a execução retoma do ponto exato após a decisão.

Padrão demonstrado: LangGraph interrupt() + Command(resume=...) + MemorySaver.

Referência: LangGraph Docs — Human-in-the-loop
https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/
"""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from agents.provider import Provider, get_llm


# ── Ferramentas de alto impacto (requerem aprovação) ─────────────────────


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Envia um e-mail (simulado). Requer aprovação humana antes de executar.

    Args:
        to: Endereço de e-mail do destinatário.
        subject: Assunto do e-mail.
        body: Corpo do e-mail em texto simples.

    Returns:
        Confirmação de envio simulado.
    """
    return f"✉️ E-mail enviado para {to} | Assunto: {subject}"


@tool
def delete_file(path: str) -> str:
    """Deleta um arquivo (simulado). Requer aprovação humana.

    Args:
        path: Caminho completo do arquivo a deletar.

    Returns:
        Confirmação de deleção simulada.
    """
    return f"🗑️ Arquivo '{path}' deletado (simulado)."


# Ferramentas que exigem revisão antes de executar
HIGH_IMPACT_TOOLS = {"send_email", "delete_file"}

# ── State ─────────────────────────────────────────────────────────────────


class HITLState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ── Graph nodes ───────────────────────────────────────────────────────────


def make_agent_node(llm_with_tools):
    """Nó principal: invoca o LLM com as ferramentas disponíveis."""

    def agent_node(state: HITLState) -> HITLState:
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    return agent_node


def should_interrupt(state: HITLState) -> str:
    """Router: verifica se o próximo tool call precisa de aprovação humana.

    Returns:
        ``"human_review"`` se a ferramenta é de alto impacto,
        ``"tools"`` caso contrário, ``END`` se não há tool call.
    """
    last = state["messages"][-1]
    if not hasattr(last, "tool_calls") or not last.tool_calls:
        return END  # type: ignore[return-value]
    if any(tc["name"] in HIGH_IMPACT_TOOLS for tc in last.tool_calls):
        return "human_review"
    return "tools"


def human_review_node(state: HITLState):
    """Nó de revisão: pausa com interrupt() e aguarda decisão humana.

    O interrupt() serializa o estado atual via checkpointer e retorna
    a execução ao chamador. A retomada acontece via Command(resume=...).
    """
    last = state["messages"][-1]
    tool_calls_info = [
        {"name": tc["name"], "args": tc["args"]}
        for tc in getattr(last, "tool_calls", [])
    ]

    # ── PAUSA — o grafo aguarda aqui até Command(resume=...) ──────────────
    decision = interrupt(
        {
            "message": "⚠️ Aprovação necessária para ferramentas de alto impacto.",
            "tool_calls": tool_calls_info,
        }
    )
    # ─────────────────────────────────────────────────────────────────────

    if decision.get("approved"):
        return Command(goto="tools")

    return Command(
        goto=END,
        update={
            "messages": [AIMessage(content="🚫 Ação cancelada pelo usuário.")]
        },
    )


# ── Graph factory ─────────────────────────────────────────────────────────


def create_hitl_agent(provider: Provider = "ollama") -> tuple:
    """Cria o agente HITL compilado com MemorySaver para checkpointing.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"``.

    Returns:
        Tupla (compiled_graph, thread_config) — thread_config deve ser
        passado em cada chamada para manter o estado entre retomadas.
    """
    tools = [send_email, delete_file]
    llm = get_llm(provider).bind_tools(tools)
    checkpointer = MemorySaver()

    graph = StateGraph(HITLState)
    graph.add_node("agent", make_agent_node(llm))
    graph.add_node("human_review", human_review_node)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_interrupt)
    graph.add_edge("tools", "agent")

    compiled = graph.compile(checkpointer=checkpointer, interrupt_before=[])
    thread_config = {"configurable": {"thread_id": "hitl-demo-1"}}

    return compiled, thread_config


# ── Demo CLI ──────────────────────────────────────────────────────────────


def run_hitl_demo(provider: Provider = "ollama") -> None:
    """Demo interativo do agente HITL no terminal."""
    agent, config = create_hitl_agent(provider)

    prompt = (
        "Send an email to admin@example.com with subject 'Weekly Report' "
        "and body 'All systems nominal.'"
    )
    print(f"🔒 HITL Agent — requer aprovação para ações de alto impacto")
    print(f"\n> {prompt}\n")

    # Primeira execução — o agente vai pausar no interrupt()
    for event in agent.stream(
        {"messages": [HumanMessage(content=prompt)]},
        config=config,
        stream_mode="values",
    ):
        last_msg = event["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.content:
            print(f"Agente: {last_msg.content}")

    # Verificar se está aguardando aprovação
    state = agent.get_state(config)
    if state.tasks and hasattr(state.tasks[0], "interrupts") and state.tasks[0].interrupts:
        interrupt_val = state.tasks[0].interrupts[0].value
        print(f"\n{interrupt_val['message']}")
        for tc in interrupt_val.get("tool_calls", []):
            print(f"  → {tc['name']}({tc['args']})")

        approve = input("\nAprovar? (s/n): ").strip().lower() == "s"
        print("✅ Aprovado — retomando..." if approve else "❌ Rejeitado — cancelando...")

        # Retomar o grafo com a decisão
        for event in agent.stream(
            Command(resume={"approved": approve}),
            config=config,
            stream_mode="values",
        ):
            last_msg = event["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                print(f"Agente: {last_msg.content}")


if __name__ == "__main__":
    run_hitl_demo("ollama")
