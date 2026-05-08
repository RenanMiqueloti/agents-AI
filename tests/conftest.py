"""Fixtures compartilhadas pelos testes.

Padrão: a cada teste, uma instância nova de ``FakeChatModel`` com a fila
vazia. O teste preenche ``responses`` antes de invocar o agente, e
opcionalmente lê ``calls`` para asserções de prompt.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.fakes import FakeChatModel, FakeEmbeddings


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Limpa o LRU cache de ``get_settings`` em cada teste.

    Sem isso, a primeira leitura de env var é congelada e ``monkeypatch.setenv``
    não tem efeito em chamadas subsequentes a ``get_settings()``.
    """
    from agents.settings import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fake_llm() -> FakeChatModel:
    """``FakeChatModel`` com fila vazia, pronto pra ser preenchido."""
    return FakeChatModel()


@pytest.fixture
def fake_embeddings() -> FakeEmbeddings:
    """``FakeEmbeddings`` determinísticas — sem dependência de Ollama."""
    return FakeEmbeddings()


@pytest.fixture
def patched_get_llm(
    monkeypatch: pytest.MonkeyPatch, fake_llm: FakeChatModel
) -> Iterator[FakeChatModel]:
    """Substitui ``agents.provider.get_llm`` por uma função que retorna ``fake_llm``.

    Use quando o teste invoca um factory (``create_basic_agent``,
    ``create_tool_agent``, etc.) que internamente chama ``get_llm``. O
    fake é compartilhado: o teste preenche ``fake_llm.responses``, o
    factory pega o fake, o teste roda e verifica.
    """
    import agents.basic_agent as basic_mod
    import agents.hitl_agent as hitl_mod
    import agents.memory_agent as memory_mod
    import agents.provider as provider_mod
    import agents.rag_agent as rag_mod
    import agents.tool_agent as tool_mod

    def _fake_get_llm(provider: str = "ollama", temperature: float = 0.0) -> FakeChatModel:
        return fake_llm

    monkeypatch.setattr(provider_mod, "get_llm", _fake_get_llm)
    monkeypatch.setattr(basic_mod, "get_llm", _fake_get_llm)
    monkeypatch.setattr(memory_mod, "get_llm", _fake_get_llm)
    monkeypatch.setattr(tool_mod, "get_llm", _fake_get_llm)
    monkeypatch.setattr(rag_mod, "get_llm", _fake_get_llm)
    monkeypatch.setattr(hitl_mod, "get_llm", _fake_get_llm)

    yield fake_llm
