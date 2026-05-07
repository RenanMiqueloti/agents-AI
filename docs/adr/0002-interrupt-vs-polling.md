# ADR-0002: `interrupt()` para Human-in-the-Loop, em vez de polling

## Status

Accepted — 2026-05-07.

## Context

O agente `hitl` precisa pausar antes de executar ferramentas de alto impacto (`send_email`, `delete_file`) e aguardar uma decisão humana. O fluxo conceitual é:

```
prompt → LLM → tool_call(send_email) → ❓ aguardar humano → execute / cancel → resposta final
```

O ponto de pausa pode ser implementado de duas formas radicalmente diferentes:

1. **Polling externo:** o agente roda até detectar que o próximo passo é uma tool de alto impacto, salva o estado parcial em algum lugar (DB, fila), e retorna. Um job externo periodicamente verifica se há aprovação registrada e re-invoca o agente do começo, agora com a aprovação no contexto.
2. **`interrupt()` nativo do LangGraph:** o nó `human_review` chama `interrupt(payload)`, que serializa o grafo completo via checkpointer e devolve o controle ao chamador. Quando este chama `agent.stream(Command(resume=value))`, o grafo retoma exatamente do mesmo ponto, com o valor injetado no lugar do `interrupt()`.

## Decision

Usar **`interrupt()` + `MemorySaver`** (em produção: `PostgresSaver`) como o mecanismo de pausa do HITL. Polling fica documentado como anti-pattern para este caso de uso.

## Consequences

**Vantagens**
- A retomada acontece **do ponto exato** — o LLM não é re-invocado para "lembrar" o contexto, o tool_call já está no estado serializado, e a resposta humana entra como o valor de retorno do `interrupt()`. Custo zero de tokens redundantes.
- O estado é **um único objeto serializável**. Em produção, trocar `MemorySaver` por `PostgresSaver` ou `SqliteSaver` é uma linha; nada no código do grafo muda.
- O fluxo é **observável** — o checkpointer guarda cada transição, então conseguimos reconstruir "o que o agente sabia em cada passo".
- Trace por `thread_id`: cada usuário (Streamlit session, request HTTP, Slack thread) recebe um id próprio, isolando estados pendentes.

**Desvantagens**
- Acoplamento com LangGraph — sair do framework significa reescrever o mecanismo. Tradeoff aceito ao escolher LangGraph como único framework ([ADR-0001](0001-langgraph-vs-crewai.md)).
- O checkpointer precisa ser configurado em produção: `MemorySaver` perde estado ao reiniciar o processo. Mitigação: `PostgresSaver` para qualquer deploy real.

## Alternatives considered

**Polling com fila externa**
- *Por quê foi tentador:* arquiteturas de aprovação tradicionalmente seguem esse padrão (workflow engines tipo Camunda, Temporal).
- *Por quê foi rejeitado:* exigiria estado externo, re-execução parcial do grafo a cada checagem (custo de tokens), e perderia o ganho de observabilidade do checkpointer. Para um agente que decide entre ferramentas em tempo "humano" (segundos a minutos), o overhead é injustificável.

**WebSocket / SSE com pausa cooperativa**
- *Por quê foi tentador:* streaming bidirecional é o caminho natural para UIs reativas.
- *Por quê foi rejeitado:* não é alternativa, é complementar — o `interrupt()` é o mecanismo de pausa, e a UI usa SSE/WebSocket apenas para entregar a notificação. No nosso caso, Streamlit já cuida disso via `st.rerun()` após receber a aprovação.

## References

- [LangGraph: Human-in-the-Loop concepts](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)
- Implementação: [`agents/hitl_agent.py`](../../agents/hitl_agent.py)
