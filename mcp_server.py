"""Servidor MCP customizado para agents-AI.

Expõe ferramentas via Model Context Protocol (MCP) que qualquer
agente compatível pode consumir — incluindo o painel agents-AI.

Ferramentas expostas:
    get_current_datetime  — data e hora atual em ISO 8601
    calculate             — avaliação segura de expressões matemáticas
    search_knowledge      — busca semântica em data/docs/ (FAISS + nomic-embed-text)
    count_tokens          — estimativa de tokens em um texto

Uso:
    python mcp_server.py

O servidor escuta em stdio (transporte padrão MCP).
Configure um cliente MCP (ex: Claude Desktop, LangGraph MCP adapter)
apontando para:
    command: python
    args: ["/path/to/mcp_server.py"]

Dependências:
    pip install -r requirements.txt
    ollama pull nomic-embed-text   # para search_knowledge

Referência: https://modelcontextprotocol.io/docs/concepts/servers
"""

from __future__ import annotations

import asyncio
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False


# ── Knowledge base (FAISS over data/docs/) ────────────────────────────────

_DOCS_DIR = Path(__file__).parent / "data" / "docs"
_EMBEDDING_MODEL = "nomic-embed-text"

# Lazy-initialized on the first ``search_knowledge`` call so a missing
# Ollama daemon doesn't prevent the rest of the server from starting.
_vectorstore: Any = None
_vectorstore_error: str | None = None


def _build_vectorstore() -> Any:
    """Indexa data/docs/*.txt com FAISS e nomic-embed-text."""
    from langchain_community.document_loaders import TextLoader
    from langchain_community.vectorstores import FAISS
    from langchain_ollama import OllamaEmbeddings
    from langchain_text_splitters import CharacterTextSplitter

    if not _DOCS_DIR.is_dir():
        raise FileNotFoundError(f"Knowledge base directory not found: {_DOCS_DIR}")

    documents = []
    for txt_path in sorted(_DOCS_DIR.glob("*.txt")):
        documents.extend(TextLoader(str(txt_path), encoding="utf-8").load())

    if not documents:
        raise ValueError(f"No .txt documents found in {_DOCS_DIR}")

    splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(documents)

    embeddings = OllamaEmbeddings(model=_EMBEDDING_MODEL)
    return FAISS.from_documents(chunks, embeddings)


def _get_vectorstore() -> Any:
    """Returns the cached vectorstore, building it on first access."""
    global _vectorstore, _vectorstore_error
    if _vectorstore is not None:
        return _vectorstore
    if _vectorstore_error is not None:
        # Surface the original failure rather than retrying every call.
        raise RuntimeError(_vectorstore_error)
    try:
        _vectorstore = _build_vectorstore()
    except Exception as exc:
        _vectorstore_error = (
            f"Failed to build knowledge base: {exc}. "
            f"Ensure Ollama is running and `ollama pull {_EMBEDDING_MODEL}` is done, "
            f"and that {_DOCS_DIR} contains .txt documents."
        )
        raise RuntimeError(_vectorstore_error) from exc
    return _vectorstore


# ── Server definition ─────────────────────────────────────────────────────

if _MCP_AVAILABLE:
    server = Server("agents-ai-mcp-server")

    # ── Tool definitions ──────────────────────────────────────────────────

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="get_current_datetime",
                description="Returns the current UTC date and time in ISO 8601 format.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            types.Tool(
                name="calculate",
                description=(
                    "Safely evaluates a mathematical expression. "
                    "Supports +, -, *, /, ** (power), sqrt(), log(), pi, e, etc. "
                    "Example: 'sqrt(144) + log(100)'"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "Mathematical expression to evaluate.",
                        }
                    },
                    "required": ["expression"],
                },
            ),
            types.Tool(
                name="search_knowledge",
                description=(
                    "Semantic search over the local knowledge base in data/docs/. "
                    "Uses FAISS in-memory + nomic-embed-text via Ollama. "
                    "Drop new .txt files in data/docs/ to extend the corpus; the index "
                    "is built lazily on the first call."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language search query.",
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 3).",
                            "default": 3,
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="count_tokens",
                description="Estimates the number of tokens in a text using a simple word-based heuristic.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to count tokens for.",
                        }
                    },
                    "required": ["text"],
                },
            ),
        ]

    # ── Tool implementations ──────────────────────────────────────────────

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if name == "get_current_datetime":
            return [
                types.TextContent(
                    type="text",
                    text=datetime.now(tz=UTC).isoformat(),
                )
            ]

        if name == "calculate":
            expression = arguments.get("expression", "").strip()
            # Safe namespace: only math functions, no builtins
            safe_ns = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
            safe_ns.update({"abs": abs, "round": round, "min": min, "max": max})
            try:
                result = eval(expression, {"__builtins__": {}}, safe_ns)
                return [types.TextContent(type="text", text=str(result))]
            except Exception as exc:
                return [types.TextContent(type="text", text=f"Error: {exc}")]

        if name == "search_knowledge":
            query = arguments.get("query", "")
            top_k = int(arguments.get("top_k", 3))

            try:
                vs = _get_vectorstore()
                results = vs.similarity_search_with_score(query, k=top_k)
            except Exception as exc:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": str(exc)},
                            indent=2,
                            ensure_ascii=False,
                        ),
                    )
                ]

            formatted = [
                {
                    "rank": i + 1,
                    "text": doc.page_content,
                    "score": round(float(score), 4),  # FAISS distance — lower is closer
                    "source": doc.metadata.get("source", "unknown"),
                }
                for i, (doc, score) in enumerate(results)
            ]
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(formatted, indent=2, ensure_ascii=False),
                )
            ]

        if name == "count_tokens":
            text = arguments.get("text", "")
            # Heurística: ~0.75 tokens por palavra (aproximação GPT tokenizer)
            word_count = len(text.split())
            estimated = int(word_count / 0.75)
            return [
                types.TextContent(
                    type="text",
                    text=f"~{estimated} tokens ({word_count} words)",
                )
            ]

        raise ValueError(f"Unknown tool: {name!r}")

    # ── Entry point ───────────────────────────────────────────────────────

    async def _main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    if __name__ == "__main__":
        asyncio.run(_main())

else:
    if __name__ == "__main__":
        print("⚠️  MCP SDK não encontrado. Instale com: pip install mcp")
        print("Servidor não iniciado.")
