"""Agente com ferramentas usando ``create_react_agent`` do LangGraph.

Padrão atual: ``create_react_agent`` do ``langgraph.prebuilt`` com
``@tool`` decorators e schemas Pydantic. Multi-provider via
:func:`agents.provider.get_llm`.

Ferramentas expostas:
- :func:`soma` — soma dois números (``SomaInput``).
- :func:`data_hoje` — data/hora UTC atual em ISO 8601 (sem args).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from agents.provider import Provider, callbacks_config, get_llm


class SomaInput(BaseModel):
    """Argumentos validados para a ferramenta :func:`soma`."""

    a: float = Field(..., description="Primeiro número.")
    b: float = Field(..., description="Segundo número.")


class DataHojeInput(BaseModel):
    """Sem argumentos — :func:`data_hoje` não precisa de input."""


@tool("soma", args_schema=SomaInput)
def soma(a: float, b: float) -> float:
    """Soma dois números.

    Use esta ferramenta quando o usuário pedir uma soma — não tente
    calcular mentalmente. O Pydantic valida que ``a`` e ``b`` são
    números antes da execução, então strings não-numéricas levantam
    erro automaticamente.
    """
    return a + b


@tool("data_hoje", args_schema=DataHojeInput)
def data_hoje() -> str:
    """Retorna a data e hora UTC atual em ISO 8601.

    Use esta ferramenta quando o usuário perguntar a data atual, dia da
    semana ou hora — não tente adivinhar a partir do conhecimento de
    treino.
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
            {"messages": [("human", f"Responda em português e seja breve: {prompt}")]},
            config=callbacks_config(),
        )
        last_msg = result["messages"][-1]
        return format_response(last_msg)

    return run
