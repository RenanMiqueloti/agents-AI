"""Testes do rag_agent — chain LCEL com retriever mockado e LLM grounded."""

from __future__ import annotations

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("langgraph")
pytest.importorskip("faiss")

from langchain_core.documents import Document

from agents.rag_agent import _load_docs, format_response

# ── format_response ────────────────────────────────────────────────────────


def test_rag_format_response_passthrough() -> None:
    assert format_response("Resposta direta.") == "Resposta direta."


def test_rag_format_response_truncates() -> None:
    out = format_response("Frase 1. Frase 2. Frase 3.")
    assert "Frase 3" not in out


# ── _load_docs ─────────────────────────────────────────────────────────────


def test_load_docs_existing_dir() -> None:
    """O diretório real ``data/docs`` tem pelo menos um .txt."""
    docs = _load_docs()
    assert len(docs) > 0
    assert all(isinstance(d, Document) for d in docs)


def test_load_docs_missing_dir_raises() -> None:
    with pytest.raises(FileNotFoundError):
        _load_docs("path/que/nao/existe")


# ── create_rag_agent end-to-end (com fake LLM e fake embeddings) ───────────


def test_create_rag_agent_invokes_chain(
    monkeypatch: pytest.MonkeyPatch, patched_get_llm, fake_embeddings
) -> None:
    """A chain RAG completa roda com embeddings determinísticas e LLM mockado.

    O teste injeta ``FakeEmbeddings`` no lugar de ``OllamaEmbeddings``,
    constrói o índice FAISS sobre os docs reais de ``data/docs/`` e
    verifica que a resposta final passou pelo ``format_response``.
    """
    import agents.rag_agent as rag_mod

    monkeypatch.setattr(rag_mod, "OllamaEmbeddings", lambda model=None: fake_embeddings)

    fake_llm = patched_get_llm
    fake_llm.responses = ["A receita do Q3 foi de R$ 15.2 milhões."]

    agent = rag_mod.create_rag_agent("ollama")
    result = agent("Qual a receita do Q3?")

    assert "15.2" in result or "milhões" in result
    assert result.endswith(".")
    # A LLM recebeu o prompt LCEL com contexto + pergunta
    assert len(fake_llm.calls) == 1
