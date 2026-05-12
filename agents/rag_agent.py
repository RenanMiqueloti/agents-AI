"""Agente RAG usando LCEL chain — sem RetrievalQA deprecated.

Pipeline: carregar docs → chunkar → embedar → indexar (FAISS) → retriever
top-3 → prompt → LLM → ``StrOutputParser``.

Embeddings: ``sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2``
via ``langchain-huggingface`` (384 dim, multilingual, ~120MB, roda em CPU
sem dependência externa). Chat model: configurável via
:func:`agents.provider.get_llm` (ollama / claude / openai).
"""

from __future__ import annotations

import os
from collections.abc import Callable

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter

from agents.provider import Provider, callbacks_config, get_llm

_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def format_response(result: object) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases."""
    if hasattr(result, "content"):
        result = result.content
    text = str(result).replace("\n", " ").strip()
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def _load_docs(docs_dir: str = "data/docs") -> list[Document]:
    """Carrega todos os arquivos .txt do diretório informado.

    Raises:
        FileNotFoundError: Se o diretório não existir.
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Diretório de documentos não encontrado: {docs_dir!r}")
    docs: list[Document] = []
    for fname in os.listdir(docs_dir):
        if fname.endswith(".txt"):
            loader = TextLoader(os.path.join(docs_dir, fname), encoding="utf-8")
            docs.extend(loader.load())
    return docs


def create_rag_agent(provider: Provider = "ollama") -> Callable[[str], str]:
    """Constrói o agente RAG com retriever FAISS e o LLM do provider escolhido.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"`` para o chat
            model. Os embeddings rodam localmente via sentence-transformers,
            sem dependência de serviço externo.

    Returns:
        Callable que recebe uma pergunta e devolve a resposta formatada.
    """
    docs = _load_docs()
    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name=_EMBEDDING_MODEL)
    db = FAISS.from_documents(chunks, embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_template(
        "Contexto:\n{context}\n\n"
        "Pergunta: {question}\n\n"
        "Responda em português, de forma breve e direta, usando apenas o contexto acima. "
        "Se a resposta não estiver no contexto, diga que não sabe."
    )
    llm = get_llm(provider)

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser()
    )

    def run(prompt_text: str) -> str:
        response = rag_chain.invoke(prompt_text, config=callbacks_config())
        return format_response(response)

    return run
