"""Testes do memory_agent — LangGraph persistence + thread_id."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.memory_agent import create_memory_agent, format_response


def test_format_response_collapses_double_dots() -> None:
    """Output do LLM com ``..`` no final não vira ``...`` redundante."""
    out = format_response("Resposta..")
    assert ".." not in out
    assert out.endswith(".")


def test_memory_agent_first_turn_includes_system_prompt(patched_get_llm) -> None:
    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Oi, sou seu assistente.")]

    agent = create_memory_agent("ollama", thread_id="t-first")
    result = agent("Olá")

    assert "Oi" in result
    assert len(fake_llm.calls) == 1

    # Primeiro turno: system prompt + HumanMessage("Olá")
    msgs = fake_llm.calls[0]
    sys_msgs = [m for m in msgs if isinstance(m, SystemMessage)]
    human_msgs = [m for m in msgs if isinstance(m, HumanMessage)]
    assert len(sys_msgs) == 1
    assert "português" in sys_msgs[0].content.lower()
    assert len(human_msgs) == 1
    assert human_msgs[0].content == "Olá"


def test_memory_agent_second_turn_persists_history(patched_get_llm) -> None:
    """Mesmo ``thread_id`` em duas chamadas → histórico do MemorySaver acumula."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="Oi! Como posso ajudar?"),
        AIMessage(content="Certo, você disse oi."),
    ]

    agent = create_memory_agent("ollama", thread_id="t-persist")
    agent("Olá")
    agent("Lembra que eu disse oi.")

    second_call_msgs = fake_llm.calls[1]
    human_msgs = [m for m in second_call_msgs if isinstance(m, HumanMessage)]
    ai_msgs = [m for m in second_call_msgs if isinstance(m, AIMessage)]

    assert any(m.content == "Olá" for m in human_msgs), "1º turn humano no histórico"
    assert any("Oi!" in str(m.content) for m in ai_msgs), "1ª resposta no histórico"
    assert any(m.content == "Lembra que eu disse oi." for m in human_msgs), "Prompt atual presente"


def test_memory_agent_distinct_thread_ids_isolate(patched_get_llm) -> None:
    """Threads distintos no mesmo agente não compartilham histórico."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="Resposta alice."),
        AIMessage(content="Resposta bob."),
    ]

    alice = create_memory_agent("ollama", thread_id="alice")
    bob = create_memory_agent("ollama", thread_id="bob")

    alice("turn alice")
    bob("turn bob")

    # Bob não deve ver o prompt do alice no histórico.
    bob_call_msgs = fake_llm.calls[1]
    human_msgs = [m for m in bob_call_msgs if isinstance(m, HumanMessage)]
    assert len(human_msgs) == 1
    assert human_msgs[0].content == "turn bob"


def test_memory_agent_separate_factory_calls_fresh_state(patched_get_llm) -> None:
    """Cada chamada a ``create_memory_agent`` cria um MemorySaver novo."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="primeira instância"),
        AIMessage(content="segunda instância"),
    ]

    agent_a = create_memory_agent("ollama", thread_id="same-id")
    agent_a("turno A")

    # Mesmo thread_id, mas factory novo → MemorySaver novo, sem o histórico.
    agent_b = create_memory_agent("ollama", thread_id="same-id")
    agent_b("turno B")

    second_msgs = fake_llm.calls[1]
    human_msgs = [m for m in second_msgs if isinstance(m, HumanMessage)]
    assert len(human_msgs) == 1
    assert human_msgs[0].content == "turno B"
