"""Testes do agents.provider — get_llm, callbacks, error paths."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

pytest.importorskip("langchain_core")


# ── get_llm ────────────────────────────────────────────────────────────────


def test_get_llm_unknown_provider_raises() -> None:
    from agents.provider import get_llm

    with pytest.raises(ValueError, match="Provider desconhecido"):
        get_llm("gemini")  # type: ignore[arg-type]


def test_get_llm_claude_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.provider import get_llm

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        get_llm("claude")


def test_get_llm_openai_without_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from agents.provider import get_llm

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_llm("openai")


def test_get_llm_claude_constructs_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Com ANTHROPIC_API_KEY definida, a função monta o ChatAnthropic.

    Mockamos a classe pra evitar contato real com a API.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    fake_chat_anthropic = MagicMock(name="ChatAnthropic")
    fake_module = MagicMock()
    fake_module.ChatAnthropic = fake_chat_anthropic
    monkeypatch.setitem(__import__("sys").modules, "langchain_anthropic", fake_module)

    from agents.provider import get_llm

    get_llm("claude", temperature=0.5)

    fake_chat_anthropic.assert_called_once()
    kwargs = fake_chat_anthropic.call_args.kwargs
    assert kwargs["temperature"] == 0.5
    # api_key agora é SecretStr — o conteúdo só sai via .get_secret_value()
    assert kwargs["api_key"].get_secret_value() == "sk-ant-test"
    assert kwargs["model_name"] == "claude-haiku-4-5-20251001"


def test_get_llm_openai_constructs_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")

    fake_chat_openai = MagicMock(name="ChatOpenAI")
    fake_module = MagicMock()
    fake_module.ChatOpenAI = fake_chat_openai
    monkeypatch.setitem(__import__("sys").modules, "langchain_openai", fake_module)

    from agents.provider import get_llm

    get_llm("openai", temperature=0.7)

    fake_chat_openai.assert_called_once()
    kwargs = fake_chat_openai.call_args.kwargs
    assert kwargs["temperature"] == 0.7
    assert kwargs["api_key"].get_secret_value() == "sk-openai-test"
    assert kwargs["model"] == "gpt-5-mini"


def test_get_llm_ollama_constructs(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_chat_ollama = MagicMock(name="ChatOllama")
    fake_module = MagicMock()
    fake_module.ChatOllama = fake_chat_ollama
    monkeypatch.setitem(__import__("sys").modules, "langchain_ollama", fake_module)

    from agents.provider import get_llm

    get_llm("ollama", temperature=0.0)

    fake_chat_ollama.assert_called_once()
    kwargs = fake_chat_ollama.call_args.kwargs
    assert kwargs["temperature"] == 0.0


# ── _build_langfuse_callback ───────────────────────────────────────────────


def test_build_langfuse_callback_returns_none_without_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    from agents.provider import _build_langfuse_callback

    assert _build_langfuse_callback() is None


def test_build_langfuse_callback_with_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """Com keys definidas, tenta importar e instanciar o handler."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")

    fake_handler_cls = MagicMock(name="CallbackHandler")
    fake_handler_cls.return_value = "<handler>"
    fake_langchain_mod = MagicMock()
    fake_langchain_mod.CallbackHandler = fake_handler_cls
    fake_pkg_mod = MagicMock()
    fake_pkg_mod.langchain = fake_langchain_mod
    monkeypatch.setitem(__import__("sys").modules, "langfuse", fake_pkg_mod)
    monkeypatch.setitem(__import__("sys").modules, "langfuse.langchain", fake_langchain_mod)

    from agents.provider import _build_langfuse_callback

    handler = _build_langfuse_callback()
    assert handler == "<handler>"
    fake_handler_cls.assert_called_once()
    kwargs = fake_handler_cls.call_args.kwargs
    assert kwargs["public_key"] == "pk-test"
    assert kwargs["secret_key"] == "sk-test"


def test_build_langfuse_callback_returns_none_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keys presentes mas pacote ``langfuse`` não instalado → None."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")

    # Garante que ambos os caminhos de import (1.x e 2.x) falhem.
    sys_modules = __import__("sys").modules

    class _Importer:
        def __init__(self, blocked: set[str]):
            self.blocked = blocked

        def find_spec(self, name, path=None, target=None):
            if name in self.blocked:
                raise ImportError(name)
            return None

    blocked = {"langfuse.langchain", "langfuse.callback"}
    monkeypatch.delitem(sys_modules, "langfuse.langchain", raising=False)
    monkeypatch.delitem(sys_modules, "langfuse.callback", raising=False)
    # Inject finders que bloqueiam os imports
    import sys as _sys

    monkeypatch.setattr(
        _sys,
        "meta_path",
        [_Importer(blocked), *_sys.meta_path],
    )

    from agents.provider import _build_langfuse_callback

    assert _build_langfuse_callback() is None


# ── get_callbacks ──────────────────────────────────────────────────────────


def test_get_callbacks_empty_when_no_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    from agents.provider import get_callbacks

    assert get_callbacks() == []


def test_get_callbacks_returns_list_when_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    import agents.provider as provider_mod

    monkeypatch.setattr(provider_mod, "_build_langfuse_callback", lambda: "<lf>")

    cbs = provider_mod.get_callbacks()
    assert cbs == ["<lf>"]


# ── callbacks_config (já testado em test_smoke; aqui o ângulo de integração) ──


def test_callbacks_config_merges_with_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """``**callbacks_config()`` em outro dict deve compor sem conflito."""
    import agents.provider as provider_mod

    monkeypatch.setattr(provider_mod, "_build_langfuse_callback", lambda: "<lf>")

    base = {"configurable": {"thread_id": "x"}}
    merged = {**base, **provider_mod.callbacks_config()}

    assert merged["configurable"] == {"thread_id": "x"}
    assert merged["callbacks"] == ["<lf>"]


# ── env hygiene ────────────────────────────────────────────────────────────


def test_provider_module_does_not_leak_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importar o módulo não muda env vars."""
    monkeypatch.setenv("X_SENTINEL_TEST_VAR", "untouched")
    import agents.provider  # noqa: F401

    assert os.environ["X_SENTINEL_TEST_VAR"] == "untouched"
