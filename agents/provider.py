"""Fábrica de LLMs por provider.

Suporta três providers:
- ``ollama``  — qwen3:8b local via Ollama (gratuito, sem API key)
- ``claude``  — Claude Haiku 4.5 via Anthropic API (requer ANTHROPIC_API_KEY)
- ``openai``  — GPT-5 mini via OpenAI API (requer OPENAI_API_KEY)

Tracing (opt-in): se ``LANGFUSE_PUBLIC_KEY`` e ``LANGFUSE_SECRET_KEY``
estiverem definidas, :func:`callbacks_config` retorna um ``RunnableConfig``
com o callback Langfuse. Passe-o em todo ``runnable.invoke(..., config=...)``
para emitir spans, custos e tokens.

Usage::

    from agents.provider import callbacks_config, get_llm
    llm = get_llm("claude")
    response = llm.invoke(prompt, config=callbacks_config())
"""

from __future__ import annotations

import os
from typing import Any, Literal

Provider = Literal["ollama", "claude", "openai"]

_OLLAMA_MODEL = "qwen3:8b"
_CLAUDE_MODEL = "claude-haiku-4-5-20251001"
_OPENAI_MODEL = "gpt-5-mini"


def get_llm(provider: Provider = "ollama", temperature: float = 0.0):
    """Retorna um ChatModel LangChain para o provider escolhido.

    Args:
        provider: Um de ``"ollama"``, ``"claude"`` ou ``"openai"``.
        temperature: Temperatura do modelo (0.0 = determinístico).

    Returns:
        Instância de BaseChatModel pronta para uso em chains LCEL.

    Raises:
        ValueError: Se o provider for desconhecido ou a API key estiver ausente.
    """
    if provider == "ollama":
        from langchain_ollama import ChatOllama  # type: ignore[import]

        return ChatOllama(model=_OLLAMA_MODEL, temperature=temperature)

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic  # type: ignore[import]

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY não encontrada. "
                "Crie um arquivo .env com ANTHROPIC_API_KEY=sk-ant-..."
            )
        return ChatAnthropic(
            model=_CLAUDE_MODEL,
            temperature=temperature,
            api_key=api_key,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore[import]

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY não encontrada. Crie um arquivo .env com OPENAI_API_KEY=sk-..."
            )
        return ChatOpenAI(
            model=_OPENAI_MODEL,
            temperature=temperature,
            api_key=api_key,  # type: ignore[arg-type]
        )

    raise ValueError(f"Provider desconhecido: {provider!r}. Use 'ollama', 'claude' ou 'openai'.")


def _build_langfuse_callback() -> Any | None:
    """Constrói o callback Langfuse se credenciais e pacote estiverem disponíveis.

    Returns:
        Instância de ``CallbackHandler`` ou ``None`` se as keys não foram
        fornecidas ou o pacote ``langfuse`` não está instalado.
    """
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return None

    try:
        from langfuse.langchain import CallbackHandler  # type: ignore[import]
    except ImportError:
        try:
            from langfuse.callback import CallbackHandler  # type: ignore[import]
        except ImportError:
            return None

    return CallbackHandler(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
    )


def get_callbacks() -> list:
    """Retorna callbacks LangChain ativos baseados em env vars.

    Atualmente expõe apenas Langfuse. Para adicionar LangSmith, Helicone,
    etc., estenda esta função e o ``_build_*`` helper correspondente.
    """
    callbacks: list = []
    lf = _build_langfuse_callback()
    if lf is not None:
        callbacks.append(lf)
    return callbacks


def callbacks_config() -> dict:
    """Retorna um ``RunnableConfig`` com callbacks ativos (vazio se nenhum).

    Uso típico::

        from agents.provider import callbacks_config, get_llm
        response = get_llm("claude").invoke(prompt, config=callbacks_config())
    """
    cbs = get_callbacks()
    return {"callbacks": cbs} if cbs else {}
