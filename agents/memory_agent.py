"""Agente com memória de conversação usando LCEL e RunnableWithMessageHistory.

Substitui o ConversationChain + ConversationBufferMemory deprecated pelo
padrão atual: chain LCEL + InMemoryChatMessageHistory + RunnableWithMessageHistory.
Suporta múltiplos providers via ``agents.provider.get_llm``.
"""
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

from agents.provider import Provider, get_llm

# Armazena histórico por session_id (escopo: ciclo de vida do processo)
_store: dict[str, InMemoryChatMessageHistory] = {}

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Responda em português. Seja direto e breve — no máximo 2 frases."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])


def _get_history(session_id: str) -> InMemoryChatMessageHistory:
    """Retorna (ou cria) o histórico de mensagens para a sessão informada.

    Args:
        session_id: Identificador único da sessão de chat.

    Returns:
        Instância de InMemoryChatMessageHistory para a sessão.
    """
    if session_id not in _store:
        _store[session_id] = InMemoryChatMessageHistory()
    return _store[session_id]


def format_response(text: str) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases.

    Args:
        text: Texto bruto retornado pelo modelo.

    Returns:
        Resposta formatada com ponto final garantido.
    """
    text = text.replace("\n", " ").strip()
    while ".." in text:
        text = text.replace("..", ".")
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if 