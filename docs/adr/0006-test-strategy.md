# ADR-0006: Estratégia de teste — `FakeChatModel` scriptado + matrix CI

## Status

Accepted — 2026-05-08.

## Context

Até a Sprint 6 a suíte de testes tinha cobertura de 37% e era majoritariamente smoke (parsing AST + factories importáveis com `pytest.importorskip`). Isso pegava regressões grosseiras (commit truncado) mas não validava comportamento — qualquer mudança no fluxo de um agente, no router HITL ou no harness de evals podia passar verde.

Para um repo que demonstra padrões de engenharia em torno de agentes LLM, a ausência de teste de comportamento é incoerente. A pergunta era *como* testar agentes LLM sem:

1. **Network calls reais** — caros, flaky, exigem keys em CI.
2. **Mocking pesado** — mock granular do `BaseChatModel` com `Mock(spec=...)` quebra ao primeiro upgrade do langchain-core.
3. **Fixtures com gravação** (VCR) — frágeis a mudanças de prompt e versão de modelo.

## Decision

Adotar **`FakeChatModel`** — um `BaseChatModel` real do LangChain com fila de respostas scriptadas — como o substituto canônico de LLMs nos testes. Combinar com:

- **`FakeEmbeddings`** determinísticas (hash MD5 → 8 floats) para testar pipelines RAG sem Ollama.
- **`make_fake_retriever`** para curto-circuitar a busca vetorial quando o teste quer focar em `prompt | llm | parser`.
- **CI matrix** Python 3.11/3.12/3.13/3.14 garantindo que o floor declarado em `pyproject.toml` (`>=3.11`) é real.
- **Job mypy** dedicado, separado de lint e test, para que falha de tipo não esconda lint nem teste.
- **Coverage gate** começando em 50% (~13 pontos acima do baseline 37%) e subindo com a maturidade da suíte.

## Consequences

**Vantagens**

- **Determinismo total.** A mesma sequência de `responses` produz a mesma execução, então o teste afirma comportamento sem ruído de modelo.
- **Custo zero em CI.** Nenhum teste consome token de Anthropic, OpenAI ou Ollama. As env vars `OPENAI_API_KEY=dummy` e `ANTHROPIC_API_KEY=dummy` no workflow são suficientes pra evitar `ValueError` em factories que só validam presença da key.
- **Cobertura de fluxo HITL real.** O `MemorySaver` é o de verdade; o teste invoca `agent.invoke(initial)`, lê `state.tasks[0].interrupts`, e retoma com `Command(resume={"approved": True})`. Não é simulação — é o fluxo real com LLM scriptado.
- **`bind_tools` no-op.** O `FakeChatModel.bind_tools` devolve `self`, mantendo a fila intacta. As respostas já carregam `tool_calls` quando relevante; reproduzir o re-prompting de schemas que `bind_tools` faz no real não tem valor pra teste.
- **Compatibilidade longeva.** Como `FakeChatModel` é um subclass de `BaseChatModel`, ele segue a evolução da API. Quando o langchain-core 2.x sair, o teste continua válido enquanto a interface central (`_generate`, `invoke`) for estável.

**Desvantagens**

- **Não detecta regressão de prompt.** Se um agente passar a montar mal o prompt, mas a estrutura geral (msgs sequência, tipos) ficar igual, o teste passa. Mitigação parcial: o atributo `FakeChatModel.calls` permite asserções em `[m.content for m in calls[i]]` — mas só se o teste explicitamente o fizer.
- **Não detecta regressão semântica do modelo de verdade.** Se o `qwen3:8b` começar a alucinar em um cenário específico, só o eval LLM-as-judge pega isso. Por isso o harness `evals/evaluate.py` continua sendo a outra metade da rede de segurança.
- **CI compatibility matrix custa minutos.** 4 jobs paralelos × 3 a 4 versões Python = mais minutos consumidos. Aceitável em repo público (Actions é free) mas precisa ser revisitado se virar privado.

## Alternatives considered

**`unittest.mock.Mock(spec=BaseChatModel)`**

- *Atrativo:* mock genérico, sem código novo no repo.
- *Rejeitado:* `BaseChatModel` tem dezenas de métodos internos que `langgraph` chama (ex: `_combine_llm_outputs`, `astream_events`). Configurar todos via `Mock` é frágil — primeira mudança de API quebra. Subclass real é mais robusta.

**`langchain_core.language_models.FakeMessagesListChatModel`**

- *Atrativo:* já existe em `langchain-core`, gratuito.
- *Rejeitado:* é estritamente "lista de respostas em ordem" sem suporte a `bind_tools` que mantém o estado. Quando se invoca `bind_tools(tools)` nele, o resultado não preserva a fila do mesmo jeito. Para tool agents e HITL, precisaríamos override mesmo assim. Migrar para o helper oficial fica como evolução natural se a API dele incluir `bind_tools` no-op no futuro.

**VCR / pytest-recording**

- *Atrativo:* gravar uma execução real e replicar nos testes seguintes.
- *Rejeitado:* fixtures gravadas dependem do exato prompt + modelo + versão. Qualquer atualização (modelo, hyperparams, system prompt) invalida tudo. Manutenção alta, valor relativo baixo para um portfólio que muda rápido.

**Testes de integração com Ollama em CI**

- *Atrativo:* coverage realista, sem mocking.
- *Rejeitado:* requer GitHub Actions Ollama setup + pull de modelo (~5GB de download por job × matrix = inviável). Mantemos cobertura via `evals/evaluate.py` que roda manualmente.
