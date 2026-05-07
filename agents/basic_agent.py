"""Agente básico — responde perguntas gerais sem memória nem ferramentas.

Multi-provider via :func:`agents.provider.get_llm`. O chat model retorna
``AIMessage``; ``format_response`` aceita tanto ``AIMessage`` quanto
``str`` ou ``dict`` para compatibilidade com diferentes backends.
"""

from __future__ import annotations

from collections.abc import Callable

from agents.provider import Provider, callbacks_config, get_llm


def format_response(result: object) -> str:
    """Normaliza a saída do LLM para string curta (máx. 2 frases).

    Args:
        result: Saída bruta do LLM (``AIMessage``, ``str`` ou ``dict``).

    Returns:
        Texto limpo terminado em ponto final.
    """
    if hasattr(result, "content"):
        result = result.content  # type: ignore[union-attr]
    if isinstance(result, dict):
        for key in ("response", "result"):
            if key in result:
                result = result[key]
                break
    text = str(result).replace("\n", " ").strip()
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def create_basic_agent(provider: Provider = "ollama") -> Callable[[str], str]:
    """Retorna um callable que invoca o LLM do provider escolhido.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"``.

    Returns:
        Função que recebe um prompt em texto e devolve a resposta formatada.
    """
    llm = get_llm(provider)

    def run(prompt: str) -> str:
        response = llm.invoke(prompt, config=callbacks_config())
        return format_response(response)

    return run
