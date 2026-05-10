"""Testes do tool_agent — react loop, dispatch de ferramentas, schemas Pydantic."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")
pytest.importorskip("pydantic")

from langchain_core.messages import AIMessage

from agents.tool_agent import (
    DataHojeInput,
    SomaInput,
    create_tool_agent,
    data_hoje,
    soma,
)

# ── Schemas Pydantic ───────────────────────────────────────────────────────


def test_soma_input_requires_two_floats() -> None:
    SomaInput(a=1.0, b=2.0)
    with pytest.raises(Exception):  # noqa: B017
        SomaInput(a=1.0)  # type: ignore[call-arg]


def test_soma_input_coerces_int_to_float() -> None:
    parsed = SomaInput(a=1, b=2)  # type: ignore[arg-type]
    assert parsed.a == 1.0
    assert parsed.b == 2.0


def test_data_hoje_input_takes_no_args() -> None:
    DataHojeInput()  # válido sem argumentos


# ── Ferramentas ────────────────────────────────────────────────────────────


def test_soma_tool_basic() -> None:
    assert soma.invoke({"a": 3, "b": 4}) == 7.0


def test_soma_tool_negative_numbers() -> None:
    assert soma.invoke({"a": -2.5, "b": 1.5}) == -1.0


def test_data_hoje_returns_iso8601_with_tz() -> None:
    """``data_hoje`` deve retornar ISO 8601 com timezone (UTC)."""
    out = data_hoje.invoke({})
    assert "T" in out  # ISO 8601: YYYY-MM-DDTHH:MM:SS+00:00
    assert "+00:00" in out or out.endswith("Z")


# ── react agent loop ───────────────────────────────────────────────────────


def test_create_tool_agent_dispatches_soma(patched_get_llm) -> None:
    """O agente recebe tool_calls do LLM, executa e devolve resposta final."""
    fake_llm = patched_get_llm

    # 1ª chamada: LLM decide chamar soma(a=10, b=20)
    # 2ª chamada (após tool result): LLM responde com content humano
    fake_llm.responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "soma",
                    "args": {"a": 10, "b": 20},
                    "id": "tc_1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content="A soma é 30."),
    ]

    agent = create_tool_agent("ollama")
    result = agent("Quanto é 10 + 20?")

    assert "30" in result
    # O LLM deve ter sido chamado pelo menos 2x: pré-tool + pós-tool
    assert len(fake_llm.calls) >= 2


def test_create_tool_agent_no_tool_call(patched_get_llm) -> None:
    """Se o LLM não chamar nenhuma ferramenta, o react agent retorna direto."""
    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Olá, posso ajudar?")]

    agent = create_tool_agent("ollama")
    result = agent("Apenas oi")

    assert "Olá" in result or "ajudar" in result
    assert len(fake_llm.calls) == 1
