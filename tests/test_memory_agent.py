"""Testes do memory_agent — acúmulo de histórico entre turns."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")

from langchain_core.messages import AIMessage, HumanMessage

from agents.memory_agent import create_memory_agent, format_response


def test_format_response_collapses_double_dots() -> None:
    """Output do LLM com ``..`` no final não vira ``...`` redundante."""
    out = format_response("Resposta..")
    assert ".." not in out
    assert out.endswith(".")


def test_memory_agent_first_turn_has_empty_history(patched_get_llm, reset_memory_store) -> None:
    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Oi, sou seu assistente.")]

    agent = create_memory_agent("ollama")
    result = agent("Olá")

    assert "Oi" in result
    assert len(fake_llm.calls) == 1

    # Primeira chamada: só o sistema + o prompt humano (history vazio).
    msgs = fake_llm.calls[0]
    human_msgs = [m for m in msgs if isinstance(m, HumanMessage)]
    assert len(human_msgs) == 1
    assert human_msgs[0].content == "Olá"


def test_memory_agent_second_turn_includes_first_in_history(
    patched_get_llm, reset_memory_store
) -> None:
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="Oi! Como posso ajudar?"),
        AIMessage(content="Certo, vou anotar."),
    ]

    agent = create_memory_agent("ollama")
    agent("Olá")
    agent("Lembra que eu disse oi.")

    # Na segunda chamada, o histórico deve conter o turno anterior.
    second_call_msgs = fake_llm.calls[1]
    human_msgs = [m for m in second_call_msgs if isinstance(m, HumanMessage)]
    ai_msgs = [m for m in second_call_msgs if isinstance(m, AIMessage)]

    assert any(m.content == "Olá" for m in human_msgs), "Primeiro turno deve aparecer no histórico"
    assert any("Oi!" in str(m.content) for m in ai_msgs), (
        "Resposta anterior deve aparecer no histórico"
    )
    assert any(m.content == "Lembra que eu disse oi." for m in human_msgs), "Prompt atual presente"


def test_memory_agent_isolates_between_store_resets(patched_get_llm, reset_memory_store) -> None:
    """Após ``reset_memory_store``, a história começa do zero."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(content="Primeira."),
        AIMessage(content="Segunda."),
    ]

    agent = create_memory_agent("ollama")
    agent("turn 1")

    # Reset manual simulado dentro do mesmo teste — emula nova "sessão"
    reset_memory_store.clear()

    agent("turn 2")

    second_call_msgs = fake_llm.calls[1]
    # Após reset, o histórico não deve ter o turn 1
    human_msgs = [m for m in second_call_msgs if isinstance(m, HumanMessage)]
    assert len(human_msgs) == 1
    assert human_msgs[0].content == "turn 2"
