# ADR-0004: FAISS no agente RAG; Qdrant fica em projeto irmão

## Status

Accepted — 2026-05-07.

## Context

O `agents-AI` tem um agente RAG (`rag_agent.py`) e o `mcp_server.py::search_knowledge`, ambos precisam de busca vetorial sobre os documentos em `data/docs/`. Em paralelo, o autor mantém um repositório irmão — `rag-chatbot` — focado em RAG com retrieval híbrido (BM25 + denso), re-ranking e corpus dinâmico. A questão é qual vector store usar em cada um.

Opções principais:

- **FAISS** — biblioteca embeddable, rodando no mesmo processo, sem serviço externo.
- **Qdrant** — vector database completo, com filtros, sharding, persistência, payload arbitrário.
- **pgvector** — extensão do Postgres; bom quando já há Postgres na stack.
- **Weaviate / Milvus / Pinecone** — outras alternativas full-database.

## Decision

**`agents-AI` usa FAISS in-memory** para o agente RAG e para o `search_knowledge` do MCP server. Qdrant continua sendo a escolha do projeto irmão [`rag-chatbot`](https://github.com/RenanMiqueloti/rag-chatbot). A separação é intencional — não é "FAISS para tudo".

## Consequences

**Vantagens**
- **Quick-start em um único `pip install`**. Sem `docker compose` extra, sem container Qdrant, sem persistência a configurar. Quem clona o repo consegue rodar o RAG localmente em minutos.
- **Embeddings sem serviço externo** — `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` roda em CPU dentro do próprio processo, sem Ollama nem API paga. Modelo (~120MB) baixa do Hugging Face Hub na primeira chamada e fica cacheado.
- **Determinismo da indexação** — o índice é construído no startup, não há estado externo a sincronizar.
- **Deploy em HF Spaces free** — sem dependência de daemon Ollama, o RAG agent funciona idêntico no painel hospedado.
- O caso de uso aqui (corpus estático em `data/docs/`, índice em memória, sem filtros nem TTL) é exatamente onde FAISS brilha.

**Desvantagens**
- **Sem persistência** — reinício do processo reconstrói o índice (custo de embeddings).
- **Sem filtros estruturados** — qualquer caso que precise filtrar por metadados (data, tag, owner) sai do escopo aqui.
- **Sem retrieval híbrido** — FAISS faz só busca densa. Para BM25 + denso + re-ranking, é melhor um sistema dedicado.

## Alternatives considered

**Qdrant para ambos os repositórios**
- *Por quê foi tentador:* unificar a stack vetorial reduz coisas a aprender.
- *Por quê foi rejeitado:* introduziria dependência de serviço externo num repo cuja proposta é demonstração simples e local. O custo de adicionar Qdrant ao quick-start (compose extra, container rodando, persistência) supera o benefício para o caso de uso.

**pgvector**
- *Por quê foi tentador:* familiar para quem já usa Postgres, pluggable em apps existentes.
- *Por quê foi rejeitado:* mesma razão que Qdrant — adiciona um serviço externo. Faria sentido se o repo já tivesse Postgres por outra razão.

**Sem RAG, focar só em agentes**
- *Por quê foi tentador:* RAG é tema grande e tem repo próprio (`rag-chatbot`).
- *Por quê foi rejeitado:* o agente RAG aqui é **simples** — serve para mostrar o pattern LCEL com retrieval e como ele se compara aos outros agentes no painel "Comparar Todos". Não compete com o `rag-chatbot`, complementa.

## References

- [FAISS — Facebook AI Similarity Search](https://faiss.ai/)
- Implementação: [`agents/rag_agent.py`](../../agents/rag_agent.py), [`mcp_server.py`](../../mcp_server.py)
- Projeto irmão para RAG: [`rag-chatbot`](https://github.com/RenanMiqueloti/rag-chatbot)
