"""Agente com memória de conversação usando LCEL e RunnableWithMessageHistory.

Substitui o ConversationChain + ConversationBufferMemory deprecated pelo
padrão atual: chain LCEL + InMemoryChatMessageHistory + RunnableWithMessageHistory.
"""
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# Armazena histórico por session_id (escopo: ciclo de vida do processo)
_store: dict[str, InMemoryChatMessageHistory] = {}


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


_prompt = ChatPromptTemplate.from_messages([
    ("system", "Responda em português. Seja direto e breve — no máximo 2 frases."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

_llm = ChatOllama(model="llama3")

_chain_with_history = RunnableWithMessageHistory(
    _prompt | _llm,
    _get_history,
    input_messages_key="input",
    history_messages_key="history",
)


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
    if not short.endswith("."):
        short += "."
    return short


def create_memory_agent():
    """Retorna uma função que executa o agente com memória de conversação.

    O histórico é mantido em memória durante a sessão do Streamlit.
    Cada chamada acumula contexto sob o session_id 'streamlit-session'.

    Returns:
        Callable[[str], str]: função que recebe um prompt e retorna a resposta.
    """
    def run(prompt_text: str) -> str:
        result = _chain_with_history.invoke(
            {"input": prompt_text},
            config={"configurable": {"session_id": "streamlit-session"}},
        )
        return format_response(result.content)
    return run
