# ADR-0005: Streamlit como UI do painel

## Status

Accepted — 2026-05-08.

## Context

O `agents-AI` precisa de uma UI que mostre os cinco agentes lado a lado, mantenha estado por sessão (especialmente o `thread_id` do HITL — ver [ADR-0002](0002-interrupt-vs-polling.md)) e permita iteração rápida enquanto o repo evolui.

Em 2026 o espaço de "framework Python pra UI de demo de IA" tem três opções práticas:

- **Streamlit** — re-run do script a cada interação, widgets de alto nível, `st.session_state` como ponte entre runs.
- **Gradio** — abstração `Interface(fn, inputs, outputs)` ou blocos compostos; integração nativa com Hugging Face Spaces.
- **Reflex** — Python compilado pra React, estado reativo de verdade, requer toolchain de bundle.

Há também o caminho de FastAPI + frontend custom (React/Vue), mas pra um painel de portfólio o overhead de manter dois projetos não compensa.

## Decision

Adotar **Streamlit** como UI única do painel, com `st.session_state` pra estado por sessão e `st.sidebar` pra controles globais (provider, agente, fluxo HITL).

## Consequences

**Vantagens**

- **Iteração rápida.** Single-file, hot-reload em ~1s, sem build. O painel sai de "ideia" pra "rodando" sem cerimônia.
- **Layout matcha o caso de uso.** Sidebar fixa pra controles + área principal pra conversa é o esqueleto natural do `st.sidebar` + `st.container`. Os 5 agentes coexistem como abas/seções sem código de roteamento.
- **`st.session_state` resolve o HITL.** Depois do fix da Sprint 2 (UUID por sessão Streamlit), threads do HITL ficam isoladas entre usuários simultâneos sem código adicional de auth.
- **Reconhecimento.** Recrutadores e revisores de portfólio em IA reconhecem Streamlit instantaneamente. Padrão de fato no espaço.
- **Deploy free** em Hugging Face Spaces (ver README) e Streamlit Community Cloud — ambos sem custo pra repositório público.

**Desvantagens**

- **Re-run completo a cada interação.** Tudo fora do `st.session_state` é recomputado. Isso obriga disciplina (ex: `@st.cache_resource` em construtores caros, evitar instanciar agente dentro do loop principal).
- **Customização visual limitada.** CSS via `st.markdown(unsafe_allow_html=True)` ou componentes externos; não dá pra reproduzir uma UI premium sem fricção.
- **Streaming de tokens é hack.** A API nativa de stream existe (`st.write_stream`), mas o re-run do script torna o controle granular menos elegante que num frontend de verdade.

## Alternatives considered

**Gradio**

- *Atrativo:* embed direto em Hugging Face Spaces com URL de iframe; "função em, UI fora" é elegante quando o caso é `predict(x) -> y`.
- *Rejeitado:* este painel não é uma única função. Tem sidebar com seleção de provider e agente, modo "comparar todos os providers" e bloco HITL com aprovação/rejeição. O `gr.Blocks` consegue, mas o estado por sessão e a sidebar dão mais trabalho que o equivalente em Streamlit. Perde o atrativo principal sem ganhar nada.

**Reflex (ex-Pynecone)**

- *Atrativo:* estado reativo de verdade, sem re-run global. Componentização limpa.
- *Rejeitado:* requer Node.js no build, ecossistema ainda pequeno, learning curve maior. Pra um painel de portfólio que vai ser visto por humanos checando "como o autor estrutura código de IA", o ganho de DX não compensa o overhead de tooling.

**FastAPI + React (ou Next.js)**

- *Atrativo:* controle total, separação clara back/front, escala pra produto de verdade.
- *Rejeitado:* dobra o tamanho do repositório e desvia do foco (a parte interessante é a orquestração dos agentes, não o frontend). A API HTTP em `api/server.py` (Sprint 2) já existe pra quem quiser plugar um frontend próprio depois.
