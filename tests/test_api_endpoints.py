"""Testes da camada FastAPI em ``api/server.py``.

Os factories (``create_basic_agent`` etc.) são monkeypatched para
devolver callables determinísticos, isolando os endpoints de toda a
stack de LLM.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("langgraph")

from fastapi.testclient import TestClient

from api.server import AgentName, app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def stub_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Substitui os factories por stubs determinísticos.

    Também limpa o ``_agent_cache`` pra que monkeypatch tenha efeito mesmo
    se um teste anterior tiver instanciado o agente real.
    """
    import api.server as server_mod

    server_mod._agent_cache.clear()

    def _stub_factory(label: str) -> Callable[[str], Callable[[str], str]]:
        def _factory(provider: str) -> Callable[[str], str]:
            def _run(prompt: str) -> str:
                return f"[{label}/{provider}] echo: {prompt}"

            return _run

        return _factory

    stubs: dict[AgentName, Callable[[str], Callable[[str], str]]] = {
        AgentName.basic: _stub_factory("basic"),
        AgentName.tool: _stub_factory("tool"),
        AgentName.rag: _stub_factory("rag"),
    }
    monkeypatch.setattr(server_mod, "_FACTORIES", stubs)


# ── /health ────────────────────────────────────────────────────────────────


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ── /agent/{name} happy path ───────────────────────────────────────────────


def test_post_agent_basic(client: TestClient, stub_factories) -> None:
    response = client.post(
        "/agent/basic",
        json={"prompt": "olá", "provider": "ollama"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "basic"
    assert body["provider"] == "ollama"
    assert "echo: olá" in body["response"]


def test_post_agent_tool(client: TestClient, stub_factories) -> None:
    response = client.post(
        "/agent/tool",
        json={"prompt": "soma 1 + 2", "provider": "claude"},
    )
    assert response.status_code == 200
    assert response.json()["agent"] == "tool"


def test_post_agent_rag(client: TestClient, stub_factories) -> None:
    response = client.post(
        "/agent/rag",
        json={"prompt": "receita Q3", "provider": "openai"},
    )
    assert response.status_code == 200
    assert response.json()["agent"] == "rag"


def test_post_agent_default_provider_is_openai(client: TestClient, stub_factories) -> None:
    """``provider`` é opcional; default ``"openai"`` (definido no schema)."""
    response = client.post("/agent/basic", json={"prompt": "x"})
    assert response.status_code == 200
    assert response.json()["provider"] == "openai"


# ── erros e validação ─────────────────────────────────────────────────────


def test_post_unknown_agent_returns_422(client: TestClient) -> None:
    response = client.post(
        "/agent/nonexistent",
        json={"prompt": "x", "provider": "openai"},
    )
    assert response.status_code == 422


def test_post_invalid_provider_returns_422(client: TestClient) -> None:
    response = client.post(
        "/agent/basic",
        json={"prompt": "x", "provider": "gemini"},
    )
    assert response.status_code == 422


def test_post_missing_prompt_returns_422(client: TestClient) -> None:
    response = client.post("/agent/basic", json={"provider": "openai"})
    assert response.status_code == 422


def test_post_factory_value_error_becomes_400(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Se o factory levanta ``ValueError`` (ex: API key faltando), API → 400."""
    import api.server as server_mod

    server_mod._agent_cache.clear()

    def _broken_factory(provider: str) -> Callable[[str], str]:
        raise ValueError("ANTHROPIC_API_KEY não encontrada")

    stubs = {
        AgentName.basic: _broken_factory,
        AgentName.tool: _broken_factory,
        AgentName.rag: _broken_factory,
    }
    monkeypatch.setattr(server_mod, "_FACTORIES", stubs)

    response = client.post("/agent/basic", json={"prompt": "x", "provider": "claude"})
    assert response.status_code == 400
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]


def test_post_factory_unexpected_error_becomes_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Erros inesperados são mapeados pra 500."""
    import api.server as server_mod

    server_mod._agent_cache.clear()

    def _exploding(provider: str) -> Callable[[str], str]:
        def _run(prompt: str) -> str:
            raise RuntimeError("kaboom")

        return _run

    stubs = {
        AgentName.basic: _exploding,
        AgentName.tool: _exploding,
        AgentName.rag: _exploding,
    }
    monkeypatch.setattr(server_mod, "_FACTORIES", stubs)

    response = client.post("/agent/basic", json={"prompt": "x", "provider": "openai"})
    assert response.status_code == 500
    assert "kaboom" in response.json()["detail"]


# ── cache de agente ────────────────────────────────────────────────────────


def test_agent_cache_reuses_same_instance(client: TestClient, stub_factories) -> None:
    """Duas chamadas pro mesmo (name, provider) reusam a mesma instância."""
    import api.server as server_mod

    client.post("/agent/basic", json={"prompt": "1", "provider": "ollama"})
    client.post("/agent/basic", json={"prompt": "2", "provider": "ollama"})

    assert (AgentName.basic, "ollama") in server_mod._agent_cache
    assert len(server_mod._agent_cache) == 1
