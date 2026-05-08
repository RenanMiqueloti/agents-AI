# Changelog

Todas as mudanças notáveis deste projeto são documentadas aqui.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), e o projeto segue [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Em desenvolvimento na branch `feat/sprint-6` — alvo `v0.5.0`.

### Added
- **ADR-0005:** Streamlit como UI do painel — comparação com Gradio e Reflex em `docs/adr/0005-streamlit-vs-gradio-reflex.md`.
- **`requirements.lock`:** lockfile pinado gerado via `pip-compile`. CI e Docker passam a instalar pelo lockfile; `requirements.txt` continua como fonte de constraints soltos.
- **Coverage badge** no topo do README.

### Changed
- **CI e Docker** instalam dependências via `requirements.lock` em vez de `requirements.txt`.
- **Coverage gate:** `pytest --cov-fail-under=35` (floor 2 pontos abaixo do baseline 37%) bloqueia regressão.
- **CONTRIBUTING.md** documenta o fluxo `requirements.txt` → `pip-compile` → `requirements.lock`.
- **Badges do README:** Python `3.12` → `3.14`, LangGraph `0.4+` → `1.1+`.

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
