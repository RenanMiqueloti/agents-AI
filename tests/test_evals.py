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


# ── build_agents_map ───────────────────────────────────────────────────────


def test_build_agents_map_returns_seven_entries(
    patched_get_llm, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``build_agents_map`` instancia 4 agentes diretos + 3 adapters HITL."""
    import agents.rag_agent as rag_mod
    from tests.fakes import FakeEmbeddings

    monkeypatch.setattr(rag_mod, "HuggingFaceEmbeddings", lambda model_name=None: FakeEmbeddings())

    from evals.evaluate import build_agents_map

    agents_map = build_agents_map("ollama")

    assert set(agents_map.keys()) == {
        "basic",
        "tool",
        "memory",
        "rag",
        "hitl_approve",
        "hitl_reject",
        "hitl_safe",
    }
    for fn in agents_map.values():
        assert callable(fn)


# ── run_evals (smoke end-to-end com tudo mockado) ──────────────────────────


def test_run_evals_writes_results_file(
    patched_get_llm,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Roda ``run_evals`` contra dataset minúsculo com judge mockado."""
    import json as _json

    import evals.evaluate as evals_mod
    from tests.fakes import FakeChatModel

    tiny_dataset = [
        {
            "id": "tiny-1",
            "agent": "basic",
            "prompt": "Olá!",
            "expected_themes": "saudação",
        }
    ]
    fake_dataset_path = tmp_path / "tiny_dataset.json"
    fake_dataset_path.write_text(_json.dumps(tiny_dataset), encoding="utf-8")
    fake_results_path = tmp_path / "tiny_results.json"

    # Patch HuggingFaceEmbeddings — build_agents_map instancia rag_agent que precisa de embeddings.
    import agents.rag_agent as rag_mod
    from tests.fakes import FakeEmbeddings as _FakeEmb

    monkeypatch.setattr(rag_mod, "HuggingFaceEmbeddings", lambda model_name=None: _FakeEmb())

    monkeypatch.setattr(evals_mod, "DATASET_PATH", fake_dataset_path)
    monkeypatch.setattr(evals_mod, "RESULTS_PATH", fake_results_path)

    fake_llm = patched_get_llm
    fake_llm.responses = [AIMessage(content="Olá! Como posso ajudar?")]

    judge_fake = FakeChatModel()
    judge_fake.responses = [
        AIMessage(
            content='{"correctness": 4, "helpfulness": 5, "conciseness": 5, "reasoning": "ok"}'
        )
    ]
    monkeypatch.setattr(evals_mod, "ChatOpenAI", lambda **kwargs: judge_fake)

    results = evals_mod.run_evals(provider="ollama")

    assert len(results) == 1
    entry = results[0]
    assert entry["id"] == "tiny-1"
    assert entry["agent"] == "basic"
    assert entry["scores"]["correctness"] == 4

    assert fake_results_path.exists()
    payload = _json.loads(fake_results_path.read_text(encoding="utf-8"))
    assert payload["summary"]["n"] == 1
    assert payload["summary"]["provider"] == "ollama"
    assert payload["summary"]["avg_correctness"] == 4
    assert len(payload["results"]) == 1


def test_run_evals_skips_unknown_agent(
    patched_get_llm,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dataset com agent desconhecido faz skip sem quebrar."""
    import json as _json

    import evals.evaluate as evals_mod
    from tests.fakes import FakeChatModel

    tiny_dataset = [{"id": "skip-me", "agent": "nonexistent_agent", "prompt": "x"}]
    fake_dataset_path = tmp_path / "skip_dataset.json"
    fake_dataset_path.write_text(_json.dumps(tiny_dataset), encoding="utf-8")
    fake_results_path = tmp_path / "skip_results.json"

    # Patch HuggingFaceEmbeddings — build_agents_map instancia rag_agent que precisa de embeddings.
    import agents.rag_agent as rag_mod
    from tests.fakes import FakeEmbeddings as _FakeEmb

    monkeypatch.setattr(rag_mod, "HuggingFaceEmbeddings", lambda model_name=None: _FakeEmb())

    monkeypatch.setattr(evals_mod, "DATASET_PATH", fake_dataset_path)
    monkeypatch.setattr(evals_mod, "RESULTS_PATH", fake_results_path)

    judge_fake = FakeChatModel()
    monkeypatch.setattr(evals_mod, "ChatOpenAI", lambda **kwargs: judge_fake)

    results = evals_mod.run_evals(provider="ollama")

    assert results == []
    captured = capsys.readouterr()
    assert "SKIP" in captured.out or "desconhecido" in captured.out


def test_run_evals_handles_agent_exception(
    patched_get_llm,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Se o agente levanta, ``run_evals`` registra ``ERROR: ...`` na resposta."""
    import json as _json

    import evals.evaluate as evals_mod
    from tests.fakes import FakeChatModel

    tiny_dataset = [{"id": "boom", "agent": "basic", "prompt": "x"}]
    fake_dataset_path = tmp_path / "boom_dataset.json"
    fake_dataset_path.write_text(_json.dumps(tiny_dataset), encoding="utf-8")
    fake_results_path = tmp_path / "boom_results.json"

    # Patch HuggingFaceEmbeddings — build_agents_map instancia rag_agent que precisa de embeddings.
    import agents.rag_agent as rag_mod
    from tests.fakes import FakeEmbeddings as _FakeEmb

    monkeypatch.setattr(rag_mod, "HuggingFaceEmbeddings", lambda model_name=None: _FakeEmb())

    monkeypatch.setattr(evals_mod, "DATASET_PATH", fake_dataset_path)
    monkeypatch.setattr(evals_mod, "RESULTS_PATH", fake_results_path)

    # patched_get_llm tem responses=[] → FakeChatModel levanta RuntimeError ao invocar
    judge_fake = FakeChatModel()
    judge_fake.responses = [
        AIMessage(
            content='{"correctness": 1, "helpfulness": 1, "conciseness": 1, "reasoning": "erro"}'
        )
    ]
    monkeypatch.setattr(evals_mod, "ChatOpenAI", lambda **kwargs: judge_fake)

    results = evals_mod.run_evals(provider="ollama")

    assert len(results) == 1
    assert results[0]["answer"].startswith("ERROR:")
