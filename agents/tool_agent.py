"""Agente com ferramentas usando create_react_agent do LangGraph.

Substitui o initialize_agent + AgentType.ZERO_SHOT_REACT_DESCRIPTION deprecated
pelo padrão atual: create_react_agent do langgraph.prebuilt com @tool decorators.
Suporta múltiplos providers via ``agents.provider.get_llm``.
"""
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agents.provider import Provider, get_llm


@tool
def soma(expressao: str) -> float:
    """Soma dois números separados por espaço.

    Args:
        expressao: String com dois números separados por espaço. Ex: '3 4'

    Returns:
        Resultado da soma como float.

    Raises:
        ValueError: Se a expressão não contiver exatamente dois números.
    """
    partes = expressao.strip().split()
    if len(partes) != 2:
        raise ValueError(
            f"Esperado dois números separados por espaço, recebi: {expressao!r}"
        )
    return float(partes[0]) + float(partes[1])


@tool
def data_hoje(dummy: str = "") -> str:  # noqa: ARG00