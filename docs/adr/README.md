# Architecture Decision Records

Cada arquivo deste diretório registra uma decisão técnica do `agents-AI` no formato [Nygard ADR](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions): contexto, decisão, consequências e alternativas consideradas. ADRs são imutáveis depois de publicados — uma decisão revogada vira um novo ADR com status `Superseded by ADR-N`.

| # | Decisão | Status |
|---|---|---|
| [0001](0001-langgraph-vs-crewai.md) | LangGraph como framework de orquestração de agentes | Accepted |
| [0002](0002-interrupt-vs-polling.md) | `interrupt()` para Human-in-the-Loop, em vez de polling | Accepted |
| [0003](0003-mcp-server-and-client.md) | Implementar servidor MCP custom além de consumir | Accepted |
| [0004](0004-faiss-vs-qdrant.md) | FAISS no agente RAG; Qdrant fica em projeto irmão | Accepted |
| [0005](0005-streamlit-vs-gradio-reflex.md) | Streamlit como UI do painel (vs Gradio, Reflex) | Accepted |
| [0006](0006-test-strategy.md) | Estratégia de teste — `FakeChatModel` scriptado + matrix CI | Accepted |
| [0007](0007-api-deprecation-migration.md) | Migração off-deprecation: `RunnableWithMessageHistory` e `create_react_agent` | Accepted |
