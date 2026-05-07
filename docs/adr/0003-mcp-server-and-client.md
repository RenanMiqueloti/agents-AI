# ADR-0003: Implementar um servidor MCP custom, além de consumir

## Status

Accepted — 2026-05-07.

## Context

O Model Context Protocol (MCP) emergiu em 2024–2025 como o padrão dominante para conectar LLMs a fontes de contexto e ferramentas externas — Anthropic publicou o spec, e em 2026 já existem clientes MCP nativos em Claude Desktop, Claude Code, Cursor e a maioria dos frameworks de agente.

A pergunta de projeto era simples: este repositório deveria

(a) **Apenas consumir MCP** — usar `MultiServerMCPClient` do LangGraph para conectar a servidores MCP existentes (filesystem, github, slack, etc.); ou
(b) **Implementar também um servidor MCP** — expor as próprias ferramentas via stdio para que clientes externos possam chamá-las.

Os dois lados do protocolo ensinam coisas diferentes: o lado cliente é orquestração e prompt design, o lado servidor é design de tool surface (input schema, error contracts, discovery).

## Decision

Implementar ambos os lados. O `mcp_server.py` é o foco principal — expõe quatro ferramentas (`get_current_datetime`, `calculate`, `search_knowledge`, `count_tokens`) via stdio, conectável a qualquer cliente MCP. O lado cliente fica representado pelo `tool_agent` (que consome tools internas via LangGraph) e pelo guia em README de como conectar `mcp_server.py` ao Claude Desktop.

## Consequences

**Vantagens**
- O repo demonstra **os dois lados do protocolo** num único checkout. Quem quer entender MCP em profundidade vê discovery (`list_tools`), execução (`call_tool`) e content typing (`TextContent`), além do consumo via cliente.
- A `search_knowledge` real (FAISS sobre `data/docs/`) prova que o servidor faz **mais que demos** — entrega busca semântica funcional, com error contract estruturado em JSON quando a dependência (Ollama) está fora.
- Forte alinhamento com a tendência 2026 do mercado: clientes MCP estão em quase todos os IDEs/agentes; servidores customizados são o trabalho que cada empresa precisa fazer para expor a base interna.

**Desvantagens**
- Mais superfície para manter — qualquer mudança no spec MCP precisa ser refletida em duas pontas.
- Overlap parcial com o `tool_agent` (ambos expõem ferramentas). A separação foi feita para deixar claro: `tool_agent` é tool calling **dentro** do agente, `mcp_server.py` é tool surface **fora** do agente.

## Alternatives considered

**Apenas consumir MCP via cliente**
- *Por quê foi tentador:* foco mais restrito, menos código, alinha com o caso de uso típico de uma equipe interna ("já temos servidor X, queremos consumir").
- *Por quê foi rejeitado:* o lado cliente é commodity, encontrado em qualquer template de agente. O lado servidor é a parte rara que distingue um repo "demonstra padrões" de um repo "demonstra integrações".

**Servidor MCP via HTTP/SSE em vez de stdio**
- *Por quê foi tentador:* HTTP é universalmente acessível, SSE entrega streaming.
- *Por quê foi rejeitado:* o escopo do repo é demonstração local. stdio é o transporte mais simples (basta `command + args`), e suporta perfeitamente os principais clientes (Claude Desktop, Claude Code). Migrar para HTTP fica como evolução quando houver necessidade de deploy compartilhado.

## References

- [Model Context Protocol — spec](https://modelcontextprotocol.io/)
- Implementação servidor: [`mcp_server.py`](../../mcp_server.py)
- Configuração no Claude Desktop: ver seção `Servidor MCP` do [README](../../README.md)
