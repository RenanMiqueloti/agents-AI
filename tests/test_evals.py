"""Testes do harness de evals — load_dataset, llm_as_judge, build_agents_map."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")
pytest.importorskip("langchain_openai")

from langchain_core.messages import AIMessage

from evals.evaluate import (
    DATASET_PATH,
    llm_as_judge,
    load_dataset,
    make_hitl_adapter,
)

# ── load_dataset ───────────────────────────────────────────────────────────


def test_dataset_file_exists() -> None:
    assert DATASET_PATH.exists()


def test_load_dataset_returns_list_of_dicts() -> None:
    data = load_dataset()
    assert isinstance(data, list)
    assert len(data) > 0
    for entry in data:
        assert "id" in entry
        assert "agent" in entry
        assert "prompt" in entry


def test_dataset_has_expected_agent_categories() -> None:
    """Cobre os 5 agentes + 3 modos do HITL."""
    data = load_dataset()
    agents_used = {entry["agent"] for entry in data}
    expected_subset = {"basic", "tool", "memory", "rag", "hitl_approve", "hitl_reject", "hitl_safe"}
    assert expected_subset.issubset(agents_used)


# ── llm_as_judge ───────────────────────────────────────────────────────────


def test_llm_as_judge_parses_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando o juiz devolve JSON válido, ``llm_as_judge`` retorna o dict parseado."""
    import evals.evaluate as evals_mod
    from tests.fakes import FakeChatModel

    fake = FakeChatModel()
    fake.responses = [
        AIMessage(
            content=json.dumps(
                {
                    "correctness": 5,
                    "helpfulness": 4,
                    "conciseness": 5,
                    "reasoning": "Resposta direta e correta.",
                }
            )
        )
    ]
    monkeypatch.setattr(evals_mod, "ChatOpenAI", lambda **kwargs: fake)

    scores = llm_as_judge("prompt", "answer", "expected")

    assert scores["correctness"] == 5
    assert scores["helpfulness"] == 4
    assert scores["conciseness"] == 5
    assert "direta" in scores["reasoning"]


def test_llm_as_judge_falls_back_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    """JSON inválido → scores zerados + reasoning bruto."""
    import evals.evaluate as evals_mod
    from tests.fakes import FakeChatModel

    fake = FakeChatModel()
    fake.responses = [AIMessage(content="isto não é JSON")]
    monkeypatch.setattr(evals_mod, "ChatOpenAI", lambda **kwargs: fake)

    scores = llm_as_judge("p", "a")

    assert scores["correctness"] == 0
    assert scores["helpfulness"] == 0
    assert scores["conciseness"] == 0
    assert scores["reasoning"] == "isto não é JSON"


def test_llm_as_judge_includes_expected_when_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    """``expected`` aparece no prompt enviado ao juiz."""
    import evals.evaluate as evals_mod
    from tests.fakes import FakeChatModel

    fake = FakeChatModel()
    fake.responses = [
        AIMessage(
            content='{"correctness": 5, "helpfulness": 5, "conciseness": 5, "reasoning": "ok"}'
        )
    ]
    monkeypatch.setattr(evals_mod, "ChatOpenAI", lambda **kwargs: fake)

    llm_as_judge("p", "a", expected="answer should mention X")

    judge_input = fake.calls[0]
    judge_text = " ".join(str(m.content) for m in judge_input)
    assert "answer should mention X" in judge_text


# ── make_hitl_adapter ──────────────────────────────────────────────────────


def test_make_hitl_adapter_returns_callable() -> None:
    fn = make_hitl_adapter("ollama", "approve")
    assert callable(fn)


def test_make_hitl_adapter_safe_path_no_interrupt(patched_get_llm) -> None:
    """``decision='safe'`` com prompt que não dispara tool → resposta normal."""
    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Tudo certo, sem ações de risco.")]

    fn = make_hitl_adapter("ollama", "safe")
    out = fn("Apenas diga olá.")

    assert "certo" in out.lower() or "olá" in out.lower() or "ações" in out.lower()


def test_make_hitl_adapter_approve_executes_tool(patched_get_llm) -> None:
    """``decision='approve'`` retoma com Command(resume) e executa send_email."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "send_email",
                    "args": {"to": "x@y.com", "subject": "s", "body": "b"},
                    "id": "tc_1",
                    "type": "tool_call",
                }
            ],
        ),
        AIMessage(content="Email enviado."),
    ]

    fn = make_hitl_adapter("ollama", "approve")
    out = fn("Manda email.")

    assert "Email" in out or "enviado" in out.lower()


def test_make_hitl_adapter_reject_returns_cancel(patched_get_llm) -> None:
    """``decision='reject'`` produz mensagem de cancelamento."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "send_email",
                    "args": {"to": "x@y.com", "subject": "s", "body": "b"},
                    "id": "tc_1",
                    "type": "tool_call",
                }
            ],
        ),
    ]

    fn = make_hitl_adapter("ollama", "reject")
    out = fn("Manda email.")

    assert "cancelada" in out.lower() or "🚫" in out


def test_make_hitl_adapter_safe_path_flagged_when_tool_fires(patched_get_llm) -> None:
    """``decision='safe'`` com prompt que dispara tool reporta regressão."""
    fake_llm = patched_get_llm
    fake_llm.responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "send_email",
                    "args": {"to": "x@y.com", "subject": "s", "body": "b"},
                    "id": "tc_1",
                    "type": "tool_call",
                }
            ],
        ),
    ]

    fn = make_hitl_adapter("ollama", "safe")
    out = fn("Manda email para teste.")

    assert "FALHA" in out or "regressão" in out.lower()
