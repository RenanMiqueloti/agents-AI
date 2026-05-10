# ADR-0007: Migração off-deprecation — `RunnableWithMessageHistory` e `create_react_agent`

## Status

Accepted — 2026-05-08.

## Context

A Sprint 7 começou com dois warnings de deprecation visíveis ao rodar a suíte:

```
LangChainDeprecationWarning: RunnableWithMessageHistory is deprecated.
Use LangGraph's built-in persistence instead.

LangGraphDeprecatedSinceV10: create_react_agent has been moved to
`langchain.agents`. Please update your import to
`from langchain.agents import create_agent`. Deprecated in LangGraph V1.0
to be removed in V2.0.
```

Ambos saíram do código real do `agents-AI`:

- `agents/memory_agent.py` usava `RunnableWithMessageHistory` + `InMemoryChatMessageHistory` + `_store: dict[str, ...]` — o padrão LangChain pré-LangGraph para multi-turn chat.
- `agents/tool_agent.py` usava `langgraph.prebuilt.create_react_agent` — o helper de tool-use que LangGraph considerou suficientemente alinhado com o ecossistema LangChain pra mover de `langgraph.prebuilt` pra `langchain.agents`.

Manter as APIs deprecated em produção carrega dois problemas:

1. **Quebra futura.** `LangGraph V2.0` vai remover `create_react_agent`. `RunnableWithMessageHistory` segue com janela de remoção mais longa, mas a pressão pra migrar está no upstream (a recomendação direta de "use LangGraph persistence" implica que helpers desse caminho não vão receber novas features).
2. **Sinal contraditório com ADR-0001.** O ADR-0001 declara LangGraph como o framework único de orquestração. Manter um agente de memória que usa o ramo "histórico via Runnable wrapper" enfraquece a coerência da escolha.

## Decision

Migrar ambos os agentes para as APIs vigentes na Sprint 7:

1. **`memory_agent.py` → LangGraph persistence**
   - `StateGraph[_MemoryState]` com um único nó (`agent`) e `START → agent → END`.
   - Estado: `messages: Annotated[list[BaseMessage], add_messages]`.
   - System prompt injetado no nó (`SystemMessage` prepended se ausente).
   - `MemorySaver` como checkpointer; `thread_id` (default `"streamlit-session"`)
     como chave da sessão. Em UIs multi-tenant, `main.py` agora gera
     `f"memory-{uuid.uuid4()}"` por sessão Streamlit (mesmo padrão do HITL).

2. **`tool_agent.py` → `langchain.agents.create_agent`**
   - Troca direta de `from langgraph.prebuilt import create_react_agent`
     para `from langchain.agents import create_agent`.
   - `system_prompt` agora é argumento explícito do factory em vez de
     ser concatenado no primeiro `HumanMessage`.
   - Resto da pipeline (Pydantic `args_schema`, `@tool` decorators)
     intocado — a mudança é só no orquestrador.

## Consequences

**Vantagens**

- **Suíte limpa.** Os dois warnings de deprecation desaparecem; a saída
  do `pytest` fica focada em sinais reais.
- **Sobrevida.** As novas APIs são as ancoradas no roadmap de
  LangChain 1.x e LangGraph 1.x; quando V2 sair, este repositório não
  precisa de migração de emergência.
- **Coerência com ADR-0001.** Tanto o agente de memória quanto o de
  ferramentas agora estão de fato em LangGraph (`StateGraph` direto ou
  via helper compilado), validando a decisão original.
- **Multi-tenancy ganha consistência.** O padrão `thread_id` por sessão
  Streamlit, que ADR-0002 introduziu pro HITL, agora se aplica também
  ao memory_agent. Não há mais um `_store: dict` global compartilhado.
- **Compatibilidade.** A assinatura pública (`create_memory_agent(provider)`,
  `create_tool_agent(provider)`) continua compatível — chamadas existentes
  do Streamlit e da API HTTP funcionam sem alteração.

**Desvantagens**

- **Verbosidade no memory_agent.** O StateGraph + nó manual é mais
  código que o `RunnableWithMessageHistory` antigo (~40 linhas vs ~25).
  Em troca, a estrutura fica explícita — `messages` é o estado, `add_messages`
  é o reducer, sem mágica de wrapper.
- **`create_agent` ainda emite alguns warnings transitivos.** Internamente
  ele usa `Pregel.invoke` que tem overload narrow demais — mantemos um
  `# type: ignore[call-overload]` em `tool_agent.run` por isso.
- **Possíveis edge cases em produção.** A migração foi validada pela
  suíte de testes (101 → 132 testes, coverage 79% → 88%) e pelo
  `streamlit run` local, mas a janela de exposição em produção real
  ainda é curta. Eventual regressão precisa de fix rápido.

## Alternatives considered

**Manter as APIs deprecated com `warnings.filterwarnings("ignore")`**

- *Atrativo:* zero esforço imediato.
- *Rejeitado:* esconde sinal verdadeiro. Quando a próxima deprecation
  chegar, ela mistura com as antigas no log. Gestão de tech debt vira
  "tudo silenciado, nada resolvido".

**Adiar pra Sprint 8+**

- *Atrativo:* Sprint 7 já tinha escopo grande (suíte de testes nova).
- *Rejeitado:* o usuário sinalizou explicitamente que queria a tech debt
  resolvida nesta sprint, e a migração se beneficiou diretamente da
  suíte de testes recém-adicionada — qualquer regressão da migração
  seria pega imediatamente pelos testes que validam comportamento dos
  agentes (`test_memory_agent.py`, `test_tool_agent.py`).

**Migrar memory_agent pra `SqliteSaver` em vez de `MemorySaver`**

- *Atrativo:* persistência durável entre reloads do Streamlit (real
  product feature).
- *Rejeitado por ora:* aumenta a superfície de mudança — exigiria gestão
  de path do arquivo SQLite, considerações sobre o filesystem efêmero do
  HF Spaces, e migração coordenada com o HITL agent. Fica como item
  identificado pra Sprint 8.
