"""FastAPI HTTP layer for stateless agents.

Exposes ``basic``, ``tool`` e ``rag`` em endpoints JSON para que o repo
possa ser consumido por serviços que não falam Streamlit. ``memory`` e
``hitl`` ficam fora aqui — o primeiro tem estado por processo (não escala
HTTP), o segundo precisa de streaming + ``Command(resume=...)`` que não
mapeia para um POST simples.

Uso::

    pip install -r requirements.txt
    uvicorn api.server:app --reload    # http://localhost:8000

Endpoints:

- ``GET  /health``                   — liveness simples
- ``POST /agent/{name}``             — name ∈ {basic, tool, rag}; body
  ``{"prompt": str, "provider": "ollama"|"claude"|"openai"}``; retorna
  ``{"response": str, "agent": str, "provider": str}``.

OpenAPI interativa em ``/docs``.

Observação: o cache ``_agent_cache`` é por processo. Sob ``uvicorn`` com
múltiplos workers cada worker tem o próprio cache — aceitável para o
escopo de demonstração; em produção, um agent registry compartilhado
(ou stateless puro) seria a evolução natural.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agents.basic_agent import create_basic_agent
from agents.provider import Provider
from agents.rag_agent import create_rag_agent
from agents.tool_agent import create_tool_agent

app = FastAPI(
    title="agents-AI HTTP API",
    description="Endpoints stateless para os agentes basic, tool e rag.",
    version="0.2.0",
)


class AgentName(StrEnum):
    basic = "basic"
    tool = "tool"
    rag = "rag"


class AgentRequest(BaseModel):
    prompt: str = Field(..., description="Texto enviado ao agente.")
    provider: Provider = Field(
        default="openai",
        description="Provider de LLM (ollama, claude ou openai).",
    )


class AgentResponse(BaseModel):
    response: str
    agent: AgentName
    provider: Provider


_FACTORIES: dict[AgentName, Callable[[Provider], Callable[[str], str]]] = {
    AgentName.basic: create_basic_agent,
    AgentName.tool: create_tool_agent,
    AgentName.rag: create_rag_agent,
}

_agent_cache: dict[tuple[AgentName, Provider], Callable[[str], str]] = {}


def _get_agent(name: AgentName, provider: Provider) -> Callable[[str], str]:
    key = (name, provider)
    if key not in _agent_cache:
        _agent_cache[key] = _FACTORIES[name](provider)
    return _agent_cache[key]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/{name}", response_model=AgentResponse)
def run_agent(name: AgentName, req: AgentRequest) -> AgentResponse:
    """Roda o agente ``name`` com o prompt informado e retorna a resposta.

    O agente é instanciado preguiçosamente na primeira chamada para cada
    par ``(name, provider)`` e cacheado pela vida do processo.
    """
    try:
        agent_fn = _get_agent(name, req.provider)
        answer = agent_fn(req.prompt)
    except ValueError as exc:
        # Provider sem API key, parâmetros inválidos, etc.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AgentResponse(response=answer, agent=name, provider=req.provider)


__all__: list[Any] = ["app"]
