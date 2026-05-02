"""Agente RAG usando LCEL chain — sem RetrievalQA deprecated.

Substitui RetrievalQA.from_chain_type + langchain.vectorstores pelo padrão atual:
LCEL chain (retrieve → prompt → llm → parse) com langchain_community.vectorstores.

Embeddings: sempre via Ollama (llama3) — independente do provider do chat model.
Chat model: configurável via ``agents.provider.get_llm`` (ollama / claude / openai).
"""
import os

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import CharacterTextSplitter

from agents.provider import Provider, get_llm


def format_response(text: str) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases.

    Args:
        text: Texto bruto retornado pelo modelo.

    Returns:
        Resposta formatada com ponto final garantido.
    """
    text = text.replace("\n", " ").strip()
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def _load_docs(docs_dir: str = "data/docs") -> list:
    """Carrega todos os arquivos .txt do diretório informado.

    A