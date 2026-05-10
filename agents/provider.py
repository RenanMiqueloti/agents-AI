"""Fábrica de LLMs por provider.

Suporta três providers:
- ``ollama``  — modelo local via Ollama (gratuito, sem API key)
- ``claude``  — Claude via Anthropic API (requer ANTHROPIC_API_KEY)
- ``openai``  — GPT via OpenAI API (requer OPENAI_API_KEY)

As chaves e nomes de modelo vêm de :class:`agents.settings.Settings`,
que carrega de ``.env`` automaticamente.

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

from typing import Any, Literal

from agents.settings import get_settings

Provider = Literal["ollama", "claude", "openai"]


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
    settings = get_settings()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.ollama_model, temperature=temperature)

    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        if settings.anthropic_api_key is None:
            raise ValueError(
                "ANTHROPIC_API_KEY não encontrada. "
                "Crie um arquivo .env com ANTHROPIC_API_KEY=sk-ant-..."
            )
        return ChatAnthropic(
            model_name=settings.claude_model,
            temperature=temperature,
            api_key=settings.anthropic_api_key,
            timeout=None,
            stop=None,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if settings.openai_api_key is None:
            raise ValueError(
                "OPENAI_API_KEY não encontrada. Crie um arquivo .env com OPENAI_API_KEY=sk-..."
            )
        return ChatOpenAI(
            model=settings.openai_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Provider desconhecido: {provider!r}. Use 'ollama', 'claude' ou 'openai'.")


def _build_langfuse_callback() -> Any | None:
    """Constrói o callback Langfuse se credenciais e pacote estiverem disponíveis.

    Returns:
        Instância de ``CallbackHandler`` ou ``None`` se as keys não foram
        fornecidas ou o pacote ``langfuse`` não está instalado.
    """
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None

    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        try:
            from langfuse.callback import CallbackHandler
        except ImportError:
            return None

    return CallbackHandler(
        public_key=settings.langfuse_public_key.get_secret_value(),
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        host=settings.langfuse_host,
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
