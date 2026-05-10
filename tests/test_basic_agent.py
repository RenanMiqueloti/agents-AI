"""Testes do basic_agent — formatação de saída e fluxo invoke."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")

from langchain_core.messages import AIMessage

from agents.basic_agent import create_basic_agent, format_response

# ── format_response ───────────────────────────────────────────────────────


def test_format_response_str_passthrough() -> None:
    assert format_response("Olá, mundo.") == "Olá, mundo."


def test_format_response_adds_missing_period() -> None:
    assert format_response("Olá, mundo") == "Olá, mundo."


def test_format_response_truncates_to_two_sentences() -> None:
    text = "Primeira frase. Segunda frase. Terceira frase. Quarta frase."
    out = format_response(text)
    assert "Terceira" not in out
    assert "Quarta" not in out
    assert out.endswith(".")


def test_format_response_aimessage() -> None:
    out = format_response(AIMessage(content="Resposta direta."))
    assert out == "Resposta direta."


def test_format_response_dict_with_response_key() -> None:
    out = format_response({"response": "valor"})
    assert out == "valor."


def test_format_response_dict_with_result_key() -> None:
    out = format_response({"result": "valor 2"})
    assert out == "valor 2."


def test_format_response_collapses_newlines() -> None:
    out = format_response("Linha um.\nLinha dois.")
    assert "\n" not in out
    assert "Linha um" in out


# ── create_basic_agent ─────────────────────────────────────────────────────


def test_create_basic_agent_invokes_llm_with_prompt(patched_get_llm) -> None:
    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Resposta do fake.")]

    agent = create_basic_agent("ollama")
    result = agent("Qual é a capital da França?")

    assert result == "Resposta do fake."
    assert len(fake_llm.calls) == 1


def test_create_basic_agent_uses_format_response(patched_get_llm) -> None:
    """A saída do agente passa por ``format_response`` (truncamento + ponto)."""
    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Frase 1. Frase 2. Frase 3 que some")]

    agent = create_basic_agent("ollama")
    result = agent("teste")

    assert "Frase 3" not in result
    assert result.endswith(".")


def test_create_basic_agent_preserves_provider_signature() -> None:
    """Factory aceita os três provider strings sem erro de tipo (estático)."""
    import contextlib

    for provider in ("ollama", "claude", "openai"):
        # Sem mock e sem .env: ValueError esperado se a key falta; ImportError se a lib do provider está ausente.
        with contextlib.suppress(ValueError, ImportError):
            create_basic_agent(provider)  # type: ignore[arg-type]
