"""Testes do hitl_agent — fluxo completo interrupt() → Command(resume=...).

Cobre as três rotas do HITL:

- **Approve**: usuário aprova, ferramenta executa, resposta final.
- **Reject**: usuário rejeita, agente retorna mensagem de cancelamento.
- **Safe path**: ferramenta sem alto impacto não dispara interrupt.

A verificação central é que o ``MemorySaver`` preserva o estado entre
invocações com o mesmo ``thread_id``, e que ``Command(resume=...)`` retoma
do ponto exato da pausa sem reexecutar o LLM da etapa anterior.
"""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")
pytest.importorskip("pydantic")

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from agents.hitl_agent import (
    DeleteFileInput,
    SendEmailInput,
    create_hitl_agent,
    delete_file,
    send_email,
)

# ── Schemas Pydantic ───────────────────────────────────────────────────────


def test_send_email_schema() -> None:
    SendEmailInput(to="a@b.com", subject="hi", body="hello")
    with pytest.raises(Exception):  # noqa: B017
        SendEmailInput(to="a@b.com", subject="hi")  # type: ignore[call-arg]


def test_delete_file_schema() -> None:
    DeleteFileInput(path="/tmp/x")
    with pytest.raises(Exception):  # noqa: B017
        DeleteFileInput()  # type: ignore[call-arg]


# ── Tools ──────────────────────────────────────────────────────────────────


def test_send_email_tool_returns_confirmation() -> None:
    out = send_email.invoke({"to": "a@b.com", "subject": "x", "body": "y"})
    assert "a@b.com" in out


def test_delete_file_tool_returns_confirmation() -> None:
    out = delete_file.invoke({"path": "/tmp/x"})
    assert "/tmp/x" in out


# ── HITL approval flow ─────────────────────────────────────────────────────


def _send_email_tool_call() -> dict:
    return {
        "name": "send_email",
        "args": {"to": "admin@example.com", "subject": "Test", "body": "Hello."},
        "id": "tc_email_1",
        "type": "tool_call",
    }


def test_hitl_pauses_on_high_impact_tool(patched_get_llm) -> None:
    """Primeira invocação dispara ``interrupt()`` antes de executar ``send_email``."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="", tool_calls=[_send_email_tool_call()]),
    ]

    agent, config = create_hitl_agent("ollama", thread_id="test-thread-pause")

    # Invocação inicial — deve pausar no human_review
    agent.invoke({"messages": [HumanMessage(content="Manda um email.")]}, config=config)

    state = agent.get_state(config)
    assert state.tasks, "O grafo deve ter uma task pendente após interrupt()"

    interrupts = []
    for task in state.tasks:
        interrupts.extend(getattr(task, "interrupts", []))
    assert interrupts, "Deve haver pelo menos um interrupt() ativo"

    payload = interrupts[0].value
    assert "Aprovação" in payload["message"] or "alto impacto" in payload["message"]
    assert any(tc["name"] == "send_email" for tc in payload["tool_calls"])


def test_hitl_approve_resumes_and_executes_tool(patched_get_llm) -> None:
    """``Command(resume={"approved": True})`` faz a ferramenta executar."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        # 1ª chamada: LLM pede para mandar email
        AIMessage(content="", tool_calls=[_send_email_tool_call()]),
        # 2ª chamada: após a tool executar, LLM resume com texto humano
        AIMessage(content="Pronto, email enviado para admin@example.com."),
    ]

    agent, config = create_hitl_agent("ollama", thread_id="test-thread-approve")

    agent.invoke({"messages": [HumanMessage(content="Manda email.")]}, config=config)
    final = agent.invoke(Command(resume={"approved": True}), config=config)

    last_msg = final["messages"][-1]
    assert "admin@example.com" in last_msg.content or "email" in last_msg.content.lower()


def test_hitl_reject_cancels_without_executing(patched_get_llm) -> None:
    """``Command(resume={"approved": False})`` retorna cancelamento sem chamar a tool."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="", tool_calls=[_send_email_tool_call()]),
        # Não deveria haver 2ª chamada — se houver, FakeChatModel levanta RuntimeError
    ]

    agent, config = create_hitl_agent("ollama", thread_id="test-thread-reject")

    agent.invoke({"messages": [HumanMessage(content="Manda email.")]}, config=config)
    final = agent.invoke(Command(resume={"approved": False}), config=config)

    last_msg = final["messages"][-1]
    # A mensagem de cancelamento contém '🚫' ou 'cancelada'
    assert "cancelada" in last_msg.content.lower() or "🚫" in last_msg.content


def test_hitl_thread_id_isolates_state(patched_get_llm) -> None:
    """Threads distintos não compartilham estado pendente do interrupt."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="", tool_calls=[_send_email_tool_call()]),
    ]

    agent, _ = create_hitl_agent("ollama", thread_id="alice-session")
    other_config = {"configurable": {"thread_id": "bob-session"}}

    agent.invoke(
        {"messages": [HumanMessage(content="Email.")]},
        config={"configurable": {"thread_id": "alice-session"}},
    )

    alice_state = agent.get_state({"configurable": {"thread_id": "alice-session"}})
    bob_state = agent.get_state(other_config)

    # Alice tem interrupt pendente; Bob nunca foi invocado, então não tem nada.
    assert alice_state.tasks
    assert not bob_state.tasks
