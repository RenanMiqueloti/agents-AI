import os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA

def format_response(result):
    if isinstance(result, dict):
        for key in ["response", "result"]:
            if key in result:
                result = result[key]
                break
    result = result.replace("\n", " ").strip()
    sentences = result.split(". ")
    return ". ".join(sentences[:2]) + "."

def create_rag_agent():
    docs_dir = "data/docs"
    all_docs = []
    for file in os.listdir(docs_dir):
        if file.endswith(".txt"):
            loader = TextLoader(os.path.join(docs_dir, file))
            all_docs += loader.load()

    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    texts = text_splitter.split_documents(all_docs)

    embeddings = OllamaEmbeddings(model="llama3")
    db = FAISS.from_documents(texts, embeddings)
    retriever = db.as_retriever()

    qa = RetrievalQA.from_chain_type(
        llm=OllamaLLM(model="llama3"),
        retriever=retriever,
        chain_type="stuff"
    )

    def run(prompt: str):
        response = qa.invoke({"query": prompt})
        return format_response(response)
    return run
