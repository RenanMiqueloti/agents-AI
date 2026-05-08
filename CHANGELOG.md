# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), e o projeto segue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Em desenvolvimento na branch `feat/sprint-7` — alvo `v0.6.0`.

### Added
- **`tests/fakes.py`:** `FakeChatModel` (scripted), `FakeEmbeddings` (determinísticas via hash) e `make_fake_retriever`. Substituem providers reais sem mock granular.
- **`tests/conftest.py`:** fixtures `fake_llm`, `patched_get_llm`, `reset_memory_store`.
- **Suíte de testes de comportamento** cobrindo todos os agentes, MCP server, API e harness de evals: `test_basic_agent.py`, `test_memory_agent.py`, `test_tool_agent.py`, `test_rag_agent.py`, `test_hitl_agent.py`, `test_mcp_tools.py`, `test_api_endpoints.py`, `test_evals.py`.
- **Job mypy no CI** sobre `agents/`, `api/` e `mcp_server.py`.
- **CI matrix Python 3.11/3.12/3.13** num job de compatibilidade adicional (job locked continua em 3.14 com `requirements.lock`).
- **`.pre-commit-config.yaml`** com ruff + ruff-format + mypy + checks padrão.
- **ADR-0006:** estratégia de teste com `FakeChatModel` scriptado + matrix CI.

### Changed
- **Coverage gate:** `--cov-fail-under` de `35` → `70` no job locked. Baseline real medido localmente: 79%.
- **CI restruturado** em quatro jobs: `lint`, `mypy`, `test-locked` (3.14 + lock + cov gate 70) e `test-compat` (matrix 3.11/3.12/3.13 com `requirements.txt` solto).
- **README:** badge de coverage 79% (yellowgreen) e seção "Design decisions" linka ADR-0006.
- **CONTRIBUTING.md** documenta pre-commit + mypy.

### Tech debt registrado (não corrigido nesta sprint)
- `agents/memory_agent.py` usa `RunnableWithMessageHistory` deprecated em LangChain 1.x. Migração natural: LangGraph persistence.
- `agents/tool_agent.py` usa `langgraph.prebuilt.create_react_agent` deprecated em LangGraph 1.0. Caminho oficial: `from langchain.agents import create_agent`.

## [0.5.0] — pendente de PR #17

Sprint 6 (PR #17, ainda em revisão). Será movida pra `[0.5.0]` quando o PR for mergeado.

## [0.4.0] — 2026-05-08

### Changed
- **Deps Python (majors):** `langchain-core` `>=0.3.0` → `>=1.3.3`, `langgraph` `>=0.4.0` → `>=1.1.10`, `langchain-text-splitters` `>=0.3.0` → `>=1.1.2`.
- **Deps Python (minors):** `fastapi` `>=0.115.0` → `>=0.136.1`, `faiss-cpu` `>=1.8.0` → `>=1.13.2`.
- **Runtime Python:** `python:3.12-slim` → `python:3.14-slim` no `Dockerfile`. `python-version` no CI também subiu para `3.14`.
- **GitHub Actions:** `actions/checkout@v4` → `@v6` e `actions/setup-python@v5` → `@v6`.

Sprint 5 consolidou 8 PRs do Dependabot (#8–#15) em um PR único (#16) para evitar conflitos em cadeia em `requirements.txt` e `ci.yml`.

## [0.3.0] — 2026-05-07

### Added
- **Sprint 3 (PR #6):** Tracing Langfuse end-to-end no agente HITL (cobre execução inicial e `Command(resume=...)` após `interrupt()`).
- **Sprint 3 (PR #6):** 4 ADRs no formato Nygard em `docs/adr/` (LangGraph vs CrewAI, `interrupt()` vs polling, MCP server além de cliente, FAISS vs Qdrant).
- **Sprint 3 (PR #6):** `.github/dependabot.yml` cobrindo pip (semanal), github-actions (mensal) e docker (mensal).
- **Sprint 4 (PR #7):** `CHANGELOG.md` neste formato.
- **Sprint 4 (PR #7):** `CONTRIBUTING.md` com guia de contribuição.
- **Sprint 4 (PR #7):** `.github/PULL_REQUEST_TEMPLATE.md` e `.github/ISSUE_TEMPLATE/` (bug + feature, blank issues desabilitadas).
- **Sprint 4 (PR #7):** CI gera relatório de cobertura em XML (artifact `coverage.xml`, retenção 14 dias).
- **Sprint 4 (PR #7):** Cobertura unitária do `callbacks_config()` e do endpoint `/health` da API.

### Changed
- Seção "Design decisions" do README virou bullets que linkam para os ADRs.

## [0.2.0] — 2026-05-07

### Added
- **Docker:** `Dockerfile` multi-stage (python:3.12-slim, non-root, healthcheck) + `docker-compose.yml` com serviço `ollama` opcional via `--profile ollama`.
- **API HTTP:** `api/server.py` (FastAPI) com `GET /health` e `POST /agent/{basic,tool,rag}`. OpenAPI em `/docs`.
- **Pydantic schemas** para args das ferramentas: `SomaInput`, `DataHojeInput`, `SendEmailInput`, `DeleteFileInput`.
- **MCP `search_knowledge` real** — FAISS in-memory + `nomic-embed-text` sobre `data/docs/` (lazy init, error contracts em JSON).
- **Eval dataset expandido** de 5 para 25 samples cobrindo `basic`, `tool`, `memory`, `rag` e HITL (approve/reject/safe).
- **Langfuse opt-in** para `basic`, `memory`, `tool` e `rag` via `agents.provider.callbacks_config()`.
- **Walkthrough de deploy** no Hugging Face Spaces no README.

### Changed
- **Models:** Claude `3-5-haiku-20241022` → `claude-haiku-4-5-20251001`; OpenAI `gpt-4o-mini` → `gpt-5-mini`; Ollama `llama3` → `qwen3:8b`; embeddings RAG `llama3` → `nomic-embed-text`.
- **README:** tagline mais sóbria, novo bloco "Visão geral", diagrama mermaid de arquitetura, Quick start subiu na página, Estrutura desce para o final.
- **HITL:** `thread_id` agora vem do `st.session_state` por usuário Streamlit; default `"hitl-demo-1"` continua válido apenas para o demo CLI.

### Fixed
- HITL no Streamlit não compartilha mais estado entre sessões simultâneas (era bug ao usar `thread_id` hardcoded `"hitl-demo-1"`).
- Tool `data_hoje` reaparece em `tool_agent.py` (estava ausente apesar de prometida no README).

## [0.1.0] — 2026-05-05

### Added
- Estrutura inicial do repositório com 5 agentes em `agents/`: `basic`, `memory`, `tool`, `rag` e `hitl`.
- Servidor MCP customizado em `mcp_server.py` com 4 ferramentas via stdio.
- Painel Streamlit em `main.py` com seleção de provider e modo "Comparar Todos".
- Harness de evals com LLM-as-judge em `evals/evaluate.py`.
- CI GitHub Actions com `ruff` (lint + format) e `pytest` (smoke tests).
- `pyproject.toml` configurando ruff, pytest e mypy.

[Unreleased]: https://github.com/RenanMiqueloti/agents-AI/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/RenanMiqueloti/agents-AI/releases/tag/v0.4.0
[0.3.0]: https://github.com/RenanMiqueloti/agents-AI/releases/tag/v0.3.0
[0.2.0]: https://github.com/RenanMiqueloti/agents-AI/releases/tag/v0.2.0
[0.1.0]: https://github.com/RenanMiqueloti/agents-AI/releases/tag/v0.1.0
