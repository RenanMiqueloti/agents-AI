"""Servidor MCP customizado para agents-AI.

Expõe ferramentas via Model Context Protocol (MCP) que qualquer
agente compatível pode consumir — incluindo o painel agents-AI.

Ferramentas expostas:
    get_current_datetime  — data e hora atual em ISO 8601
    calculate             — avaliação segura de expressões matemáticas
    search_knowledge      — busca stub no knowledge base (conecte ao seu Qdrant aqui)
    count_tokens          — estimativa de tokens em um texto

Uso:
    python mcp_server.py

O servidor escuta em stdio (transporte padrão MCP).
Configure um cliente MCP (ex: Claude Desktop, LangGraph MCP adapter)
apontando para:
    command: python
    args: ["/path/to/mcp_server.py"]

Dependência:
    pip install mcp

Referência: https://modelcontextprotocol.io/docs/concepts/servers
"""
from __future__ import annotations

import asyncio
import json
import math
from datetime import datetime, timezone

try:
    from mcp import types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False

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
                    "Searches the local knowledge base for documents relevant to a query. "
                    "In production, connect this to your Qdrant/pgvector instance."
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
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent]:

        if name == "get_current_datetime":
            return [
                types.TextContent(
                    type="text",
                    text=datetime.now(tz=timezone.utc).isoformat(),
                )
            ]

        if name == "calculate":
            expression = arguments.get("expression", "").strip()
            # Safe namespace: only math functions, no builtins
            safe_ns = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
            safe_ns.update({"abs": abs, "round": round, "min": min, "max": max})
            try:
                result = eval(expression, {"__builtins__": {}}, safe_ns)  # noqa: S307
                return [types.TextContent(type="text", text=str(result))]
            except Exception as exc:  # noqa: BLE001
                return [types.TextContent(type="text", text=f"Error: {exc}")]

        if name == "search_knowledge":
            query = arguments.get("query", "")
            top_k = int(arguments.get("top_k", 3))
            # ── Stub — substitua pela integração real com Qdrant ──────────
            # Exemplo de integração real:
            #   from qdrant_client import QdrantClient
            #   client = QdrantClient(url=os.getenv("QDRANT_URL"))
            #   results = client.search("docs", query_vector=embed(query), limit=top_k)
            stub = [
                {
                    "rank": i + 1,
                    "text": f"[Placeholder result {i+1} for '{query}'] "
                    "Replace this stub with a real Qdrant query.",
                    "score": round(0.95 - i * 0.1, 2),
                }
                for i in range(top_k)
            ]
            return [types.TextContent(type="text", text=json.dumps(stub, indent=2))]

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
