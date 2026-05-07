"""Agente com ferramentas usando ``create_react_agent`` do LangGraph.

Padrão atual: ``create_react_agent`` do ``langgraph.prebuilt`` com
``@tool`` decorators. Multi-provider via :func:`agents.provider.get_llm`.

Ferramentas expostas:
- :func:`soma` — soma dois números.
- :func:`data_hoje` — data/hora UTC atual em ISO 8601.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.provider import Provider, get_llm


@tool
def soma(expressao: str) -> float:
    """Soma dois números separados por espaço.

    Args:
        expressao: String com dois números separados por espaço. Ex: ``'3 4'``.

    Returns:
        Resultado da soma como float.

    Raises:
        ValueError: Se a expressão não contiver exatamente dois números.
    """
    partes = expressao.strip().split()
    if len(partes) != 2:
        raise ValueError(f"Esperado dois números separados por espaço, recebi: {expressao!r}")
    return float(partes[0]) + float(partes[1])


@tool
def data_hoje(_unused: str = "") -> str:
    """Retorna a data e hora UTC atual em ISO 8601.

    Use esta ferramenta quando o usuário perguntar a data atual, dia da semana
    ou hora — não tente adivinhar a partir do conhecimento de treino.

    Args:
        _unused: Argumento não utilizado (alguns LLMs exigem assinatura com
            pelo menos um parâmetro mesmo quando a ferramenta não precisa).

    Returns:
        Data/hora ISO 8601 com timezone, ex: ``'2026-05-07T12:34:56+00:00'``.
    """
    return datetime.now(tz=UTC).isoformat()


def format_response(result: object) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases."""
    if hasattr(result, "content"):
        result = result.content  # type: ignore[union-attr]
    text = str(result).replace("\n", " ").strip()
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def create_tool_agent(provider: Provider = "ollama") -> Callable[[str], str]:
    """Cria o agente ReAct com ferramentas usando o provider escolhido.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"``.

    Returns:
        Callable que recebe um prompt e devolve a resposta formatada.
    """
    llm = get_llm(provider)
    agent = create_react_agent(llm, tools=[soma, data_hoje])

    def run(prompt: str) -> str:
        result = agent.invoke(
            {"messages": [("human", f"Responda em português e seja breve: {prompt}")]}
        )
        last_msg = result["messages"][-1]
        return format_response(last_msg)

    return run
