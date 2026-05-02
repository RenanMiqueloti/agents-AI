"""Fábrica de LLMs por provider.

Suporta três providers:
- ``ollama``  — modelo local via Ollama (gratuito, sem API key)
- ``claude``  — Claude 3.5 Haiku via Anthropic API (requer ANTHROPIC_API_KEY)
- ``openai``  — GPT-4o-mini via OpenAI API (requer OPENAI_API_KEY)

Usage::

    from agents.provider import get_llm
    llm = get_llm("claude")
"""
import os
from typing import Literal

Provider = Literal["ollama", "claude", "openai"]

_OLLAMA_MODEL = "llama3"
_CLAUDE_MODEL = "claude-3-5-haiku-20241022"
_OPENAI_MODEL = "gpt-4o-mini"


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
                "OPENAI_API_KEY não encontrada. "
                "Crie um arquivo .env com OPENAI_API_KEY=sk-..."
            )
        return ChatOpenAI(
            model=_OPENAI_MODEL,
            temperature=temperature,
            api_key=api_key,
        )

    raise ValueError(
        f"Provider desconhecido: {provider!r}. "
        "Use 'ollama', 'claude' ou 'openai'."
    )
