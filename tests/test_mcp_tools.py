"""Testes do servidor MCP — cada tool unitariamente.

As tools são funções async registradas via ``@server.call_tool()``. O
teste invoca-as diretamente com ``asyncio.run`` em vez de simular o
protocolo MCP completo, mantendo o teste rápido e isolado.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock

import pytest

pytest.importorskip("mcp")

import mcp_server


def _run(coro):
    """Helper: roda uma coroutine sincronamente em pytest sem pytest-asyncio."""
    return asyncio.run(coro)


# ── get_current_datetime ───────────────────────────────────────────────────


def test_get_current_datetime_returns_iso8601() -> None:
    result = _run(mcp_server.call_tool("get_current_datetime", {}))
    assert len(result) == 1
    text = result[0].text
    assert "T" in text  # ISO 8601 separator
    assert "+00:00" in text or text.endswith("Z")


# ── calculate ──────────────────────────────────────────────────────────────


def test_calculate_basic_arithmetic() -> None:
    result = _run(mcp_server.call_tool("calculate", {"expression": "2 + 2"}))
    assert result[0].text == "4"


def test_calculate_supports_sqrt() -> None:
    result = _run(mcp_server.call_tool("calculate", {"expression": "sqrt(144)"}))
    assert "12" in result[0].text


def test_calculate_supports_math_functions() -> None:
    result = _run(mcp_server.call_tool("calculate", {"expression": "log(100)"}))
    text = result[0].text
    assert text.startswith("4.6")  # ln(100) ≈ 4.605


def test_calculate_blocks_builtins() -> None:
    """``__builtins__`` desabilitado, então ``open`` ou ``exec`` falham."""
    result = _run(mcp_server.call_tool("calculate", {"expression": "open('x')"}))
    assert "Error" in result[0].text


def test_calculate_invalid_expression() -> None:
    result = _run(mcp_server.call_tool("calculate", {"expression": "isto não é math"}))
    assert "Error" in result[0].text


# ── count_tokens ───────────────────────────────────────────────────────────


def test_count_tokens_returns_estimate_and_word_count() -> None:
    result = _run(mcp_server.call_tool("count_tokens", {"text": "uma duas três quatro cinco"}))
    text = result[0].text
    assert "tokens" in text
    assert "5 words" in text


def test_count_tokens_empty_text() -> None:
    result = _run(mcp_server.call_tool("count_tokens", {"text": ""}))
    text = result[0].text
    assert "0 words" in text


# ── search_knowledge ───────────────────────────────────────────────────────


def test_search_knowledge_with_mocked_vectorstore(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vectorstore mockado retorna 1 resultado, função formata em JSON."""
    from langchain_core.documents import Document

    fake_vs = MagicMock()
    fake_vs.similarity_search_with_score.return_value = [
        (Document(page_content="receita Q3 R$ 15M", metadata={"source": "exemplo.txt"}), 0.42),
    ]

    monkeypatch.setattr(mcp_server, "_get_vectorstore", lambda: fake_vs)

    result = _run(mcp_server.call_tool("search_knowledge", {"query": "receita"}))
    payload = json.loads(result[0].text)

    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["text"] == "receita Q3 R$ 15M"
    assert payload[0]["source"] == "exemplo.txt"
    assert payload[0]["rank"] == 1


def test_search_knowledge_respects_top_k(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_vs = MagicMock()
    fake_vs.similarity_search_with_score.return_value = []
    monkeypatch.setattr(mcp_server, "_get_vectorstore", lambda: fake_vs)

    _run(mcp_server.call_tool("search_knowledge", {"query": "x", "top_k": 5}))

    fake_vs.similarity_search_with_score.assert_called_once_with("x", k=5)


def test_search_knowledge_returns_error_json_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Se o vectorstore falha, a tool devolve um JSON com chave ``error``."""

    def _broken() -> None:
        raise RuntimeError("embedding model download failed")

    monkeypatch.setattr(mcp_server, "_get_vectorstore", _broken)

    result = _run(mcp_server.call_tool("search_knowledge", {"query": "x"}))
    payload = json.loads(result[0].text)
    assert "error" in payload
    assert "embedding" in payload["error"]


# ── unknown tool ───────────────────────────────────────────────────────────


def test_unknown_tool_name_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        _run(mcp_server.call_tool("nope_tool", {}))


# ── list_tools metadata ────────────────────────────────────────────────────


def test_list_tools_returns_four_tools() -> None:
    tools = _run(mcp_server.list_tools())
    names = {t.name for t in tools}
    assert names == {"get_current_datetime", "calculate", "search_knowledge", "count_tokens"}


# ── _get_vectorstore caching ───────────────────────────────────────────────


def test_get_vectorstore_caches_after_first_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Segunda chamada reutiliza o vectorstore construído na primeira."""
    builds = {"count": 0}
    sentinel = object()

    def _fake_build() -> object:
        builds["count"] += 1
        return sentinel

    monkeypatch.setattr(mcp_server, "_build_vectorstore", _fake_build)
    monkeypatch.setattr(mcp_server, "_vectorstore", None)
    monkeypatch.setattr(mcp_server, "_vectorstore_error", None)

    assert mcp_server._get_vectorstore() is sentinel
    assert mcp_server._get_vectorstore() is sentinel
    assert builds["count"] == 1


def test_get_vectorstore_caches_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Falha na 1ª build é cacheada — não tenta construir de novo."""
    builds = {"count": 0}

    def _fake_failing_build() -> object:
        builds["count"] += 1
        raise FileNotFoundError("data/docs ausente")

    monkeypatch.setattr(mcp_server, "_build_vectorstore", _fake_failing_build)
    monkeypatch.setattr(mcp_server, "_vectorstore", None)
    monkeypatch.setattr(mcp_server, "_vectorstore_error", None)

    with pytest.raises(RuntimeError, match="Failed to build"):
        mcp_server._get_vectorstore()
    with pytest.raises(RuntimeError, match="Failed to build"):
        mcp_server._get_vectorstore()

    # Segunda chamada surface o erro cacheado sem retentar.
    assert builds["count"] == 1


def test_build_vectorstore_missing_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """``_build_vectorstore`` com diretório inexistente levanta FileNotFoundError."""
    monkeypatch.setattr(mcp_server, "_DOCS_DIR", tmp_path / "nonexistent")

    with pytest.raises(FileNotFoundError, match="not found"):
        mcp_server._build_vectorstore()


def test_build_vectorstore_empty_dir(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Diretório existe mas sem .txt → ValueError."""
    empty_dir = tmp_path / "empty_docs"
    empty_dir.mkdir()
    monkeypatch.setattr(mcp_server, "_DOCS_DIR", empty_dir)

    with pytest.raises(ValueError, match=r"No \.txt"):
        mcp_server._build_vectorstore()
