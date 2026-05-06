"""Agente com memória de conversação usando LCEL e RunnableWithMessageHistory.

Padrão atual: chain LCEL + ``InMemoryChatMessageHistory`` +
``RunnableWithMessageHistory``. Multi-provider via
:func:`agents.provider.get_llm`.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from agents.provider import Provider, get_llm

# Histórico por session_id (escopo: ciclo de vida do processo)
_store: dict[str, InMemoryChatMessageHistory] = {}


def _get_history(session_id: str) -> InMemoryChatMessageHistory:
    """Retorna (ou cria) o histórico de mensagens para a sessão informada."""
    if session_id not in _store:
        _store[session_id] = InMemoryChatMessageHistory()
    return _store[session_id]


def format_response(result: object) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases."""
    if hasattr(result, "content"):
        result = result.content  # type: ignore[union-attr]
    text = str(result).replace("\n", " ").strip()
    while ".." in text:
        text = text.replace("..", ".")
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def create_memory_agent(provider: Provider = "ollama") -> Callable[[str], str]:
    """Cria o agente com memória multi-turn usando o provider escolhido.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"``.

    Returns:
        Callable que recebe um prompt e devolve a resposta formatada.
        O histórico acumula sob o ``session_id`` ``"streamlit-session"``.
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "Responda em português. Seja direto e breve — no máximo 2 frases."),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )
    llm = get_llm(provider)

    chain_with_history = RunnableWithMessageHistory(
        prompt | llm,
        _get_history,
        input_messages_key="input",
        history_messages_key="history",
    )

    def run(prompt_text: str) -> str:
        result = chain_with_history.invoke(
            {"input": prompt_text},
            config={"configurable": {"session_id": "streamlit-session"}},
        )
        return format_response(result)

    return run
