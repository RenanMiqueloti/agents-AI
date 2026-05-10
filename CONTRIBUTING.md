# Contribuindo com agents-AI

Obrigado pelo interesse. Este guia cobre como subir o ambiente, rodar os checks, e abrir uma contribuição que se encaixa no estilo do repositório.

## Ambiente de desenvolvimento

Requisitos:

- Python **3.12** (mínimo: 3.11)
- [Ollama](https://ollama.ai) (opcional — necessário para rodar o agente RAG e o `mcp_server.search_knowledge` localmente)
- Docker + Docker Compose (opcional — só se for rodar a versão containerizada)

```bash
git clone https://github.com/RenanMiqueloti/agents-AI.git
cd agents-AI
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.lock                     # versões pinadas (CI usa esta)
pip install ruff pytest pytest-cov                   # ferramentas de dev
```

`requirements.txt` lista as dependências com constraints soltos (`>=`); `requirements.lock` é gerado por `pip-compile` e pina toda a árvore. CI e Docker instalam pelo lockfile. Para adicionar ou subir uma dependência, edite `requirements.txt` e regenere:

```bash
pip install pip-tools
pip-compile --output-file=requirements.lock requirements.txt
```

Para rodar o painel Streamlit ou os evals localmente, copie [`.env.example`](.env.example) para `.env` e preencha as keys dos providers que for usar.

## Rodando os checks antes do PR

O CI tem quatro jobs: `lint`, `mypy`, `test-locked` (3.14 com `requirements.lock`) e `test-compat` (matrix 3.11/3.12/3.13 com `requirements.txt` solto). Os comandos equivalentes rodam localmente como:

```bash
ruff check .
ruff format --check .
mypy agents api mcp_server.py
pytest -v --cov=. --cov-fail-under=50 tests/
```

Pra rodar tudo de uma vez via pre-commit:

```bash
pip install pre-commit
pre-commit install         # instala o hook git
pre-commit run --all-files
```

Os testes usam `tests/fakes.py` (FakeChatModel scriptado) — não há network call em CI. A maior parte ainda usa `pytest.importorskip` para deps pesadas (`langgraph`, `faiss`, `mcp`, `fastapi`); na ausência de `requirements.lock` instalado, esses testes pulam ao invés de falhar.

## Abrindo um Pull Request

1. **Branch feature.** Sempre saia do `main` atualizado e crie uma branch com prefixo apropriado:
   - `feat/...` — nova feature
   - `fix/...` — correção de bug
   - `docs/...` — documentação
   - `chore/...` — config, tooling, manutenção
   - `refactor/...` — mudanças que não afetam comportamento
   - `test/...` — só testes
2. **Conventional Commits.** Mensagens no formato `tipo(escopo): descrição`. O escopo é opcional mas recomendado quando ajuda (`feat(api):`, `fix(hitl-ui):`, `docs(adr):`).
3. **Um commit, uma ideia.** Commits granulares facilitam o code review. PRs grandes são bem-vindos quando squash & merge resolve.
4. **Descrição do PR.** Cubra _What_ (o que mudou), _Why_ (por que mudou) e _How to test_ (como verificar que funciona). O template de PR já tem essa estrutura.
5. **Vincule a issue** (se houver) com `Closes #N` no corpo do PR.

## Code style

- **Ruff** com configuração em [`pyproject.toml`](pyproject.toml): `line-length = 100`, double quotes, target `py312`.
- **Type hints** em assinaturas públicas; uso de `from __future__ import annotations` é encorajado.
- **Docstrings** em PT-BR para módulos e funções públicas; comentários inline também em PT-BR. Mensagens de commit e PR em inglês para consistência com o histórico do GitHub.
- **Tools `@tool` do LangChain** devem usar `args_schema=BaseModel` (Pydantic) — ver [`agents/tool_agent.py`](agents/tool_agent.py) como referência.

## Reportando bugs e sugerindo features

Use os templates em **[Issues → New Issue](https://github.com/RenanMiqueloti/agents-AI/issues/new/choose)**:

- **Bug report** — descreva o que aconteceu, o que era esperado, e como reproduzir.
- **Feature request** — descreva o caso de uso e por que o repo atual não o cobre.

Issues em branco estão desabilitadas para que cada relato comece com o mínimo de contexto.

## Decisões arquiteturais

Mudanças que afetam o desenho do sistema (escolha de framework, protocolo, vector store, etc.) devem vir acompanhadas de um **ADR** em [`docs/adr/`](docs/adr/). O formato é o de [Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions): _Status_, _Context_, _Decision_, _Consequences_, _Alternatives considered_.

## Licença

Contribuições são licenciadas sob a [MIT License](LICENSE), a mesma do projeto.
