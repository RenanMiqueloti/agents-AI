# ADR-0001: LangGraph como framework de orquestração

## Status

Accepted — 2026-05-07.

## Context

O `agents-AI` precisa orquestrar cinco agentes com requisitos heterogêneos: chain LCEL simples, memória multi-turn, tool-use, RAG e Human-in-the-Loop com checkpoint. O ponto de partida em 2024 foi LangChain puro (LCEL + AgentExecutor + ConversationChain), que ficou marcado como deprecated e empurra o usuário para `langgraph` como sucessor recomendado da própria LangChain.

Em 2025–2026 o espaço de frameworks de agente concentrou-se em três opções:
- **LangGraph** — graph-based, estado explícito por nó com reducers, checkpointer pluggable.
- **CrewAI** — abstração de "papéis" (roles) com tarefas declarativas, oculta o estado.
- **AutoGen** — multi-agent conversacional, foco em hand-off entre agentes pares.

CrewAI é o concorrente mais visível para esse repositório porque o público (`AI Engineer mid/senior`) costuma comparar os dois.

## Decision

Adotar **LangGraph** (versão 0.4+) como o framework único de orquestração para todos os agentes deste repositório.

## Consequences

**Vantagens**
- O estado do grafo é um `TypedDict` declarado pelo desenvolvedor; cada nó retorna apenas o delta. O `add_messages` reducer resolve conflitos em execuções paralelas de forma determinística — boa propriedade quando se quer audit trail ou replay.
- O `MemorySaver`/`PostgresSaver` checkpointer permite serializar o grafo inteiro e retomar exatamente do ponto da pausa — base do nosso HITL (ver [ADR-0002](0002-interrupt-vs-polling.md)).
- Continuidade com LCEL: o grafo aceita `Runnable`s nos nós, então as chains existentes (basic, memory, RAG) coexistem com os grafos (tool, hitl) sem reescrita.
- Forte alinhamento com o ecossistema LangChain: `bind_tools`, callbacks (Langfuse, LangSmith), MCP adapters.

**Desvantagens**
- Verbosidade maior que CrewAI em casos simples — declarar `StateGraph`, `TypedDict`, edges e nodes para um fluxo trivial é overkill quando comparado ao `crew.kickoff()`.
- A API ainda é jovem: 0.4 já mudou módulos públicos em relação à 0.3, e devs precisam acompanhar.

## Alternatives considered

**CrewAI**
- *Por quê foi tentador:* DSL super enxuta para definir agentes com papéis e tarefas. Demos rodam em 30 linhas.
- *Por quê foi rejeitado:* a abstração esconde o estado. Quando o requisito vira "preciso pausar para aprovação humana / ver o que cada agente fez no minuto T / refazer apenas o último passo", o framework não dá os hooks. Para um repositório que pretende mostrar `padrões` e não só `protótipos`, a opacidade do CrewAI é o oposto do que se quer mostrar.

**AutoGen**
- *Por quê foi tentador:* multi-agent conversacional é elegante para alguns casos (agentes que negociam entre si).
- *Por quê foi rejeitado:* o foco é hand-off entre agentes pares, não orquestração de um único agente com múltiplas ferramentas. O nosso caso de uso central (HITL antes de side-effects) não mapeia naturalmente.

**LangChain puro (LCEL + AgentExecutor)**
- *Por quê foi rejeitado:* `AgentExecutor` está deprecated; a própria LangChain recomenda `langgraph.prebuilt.create_react_agent`. Ficar em LangChain puro seria construir contra uma API morta.
