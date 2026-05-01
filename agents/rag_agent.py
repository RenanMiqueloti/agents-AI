"""Agente RAG usando LCEL chain — sem RetrievalQA deprecated.

Substitui RetrievalQA.from_chain_type + langchain.vectorstores pelo padrão atual:
LCEL chain (retrieve → prompt → llm → parse) com langchain_community.vectorstores.
"""
import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


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

    Args:
        docs_dir: Caminho para o diretório com os documentos.

    Returns:
        Lista de Document objects carregados.

    Raises:
        FileNotFoundError: Se o diretório não existir.
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Diretório de documentos não encontrado: {docs_dir!r}")
    docs = []
    for fname in os.listdir(docs_dir):
        if fname.endswith(".txt"):
            loader = TextLoader(os.path.join(docs_dir, fname), encoding="utf-8")
            docs.extend(loader.load())
    return docs


def create_rag_agent():
    """Retorna uma função que consulta documentos locais via LCEL RAG chain.

    Pipeline: carregar docs → chunkar → embedar (Ollama) → indexar (FAISS)
    → retriever top-3 → prompt → ChatOllama → StrOutputParser.

    Returns:
        Callable[[str], str]: função que recebe uma pergunta e retorna a resposta.
    """
    docs = _load_docs()
    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)

    embeddings = OllamaEmbeddings(model="llama3")
    db = FAISS.from_documents(chunks, embeddings)
    retriever = db.as_retriever(search_kwargs={"k": 3})

    prompt = ChatPromptTemplate.from_template(
        "Contexto:\n{context}\n\n"
        "Pergunta: {question}\n\n"
        "Responda em português, de forma breve e direta, usando apenas o contexto acima. "
        "Se a resposta não estiver no contexto, diga que não sabe."
    )
    llm = ChatOllama(model="llama3")

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    def run(prompt_text: str) -> str:
        response = rag_chain.invoke(prompt_text)
        return format_response(response)
    return run
