"""Dashboard Streamlit — IA Agents com múltiplos providers e padrões de produção."""
import os

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command

from agents.basic_agent import create_basic_agent
from agents.hitl_agent import create_hitl_agent
from agents.memory_agent import create_memory_agent
from agents.provider import Provider
from agents.rag_agent import create_rag_agent
from agents.tool_agent import create_tool_agent

load_dotenv()

# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IA Agents",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
# 🤖 IA Agents
Painel pessoal para explorar e comparar agentes de IA com diferentes providers.
Respostas curtas, limpas e diretas — com histórico e comparação lado a lado.
"""
)

# ---------------------------------------------------------------------------
# Sidebar — provider e tipo de agente
# ---------------------------------------------------------------------------
st.sidebar.header("Configuração")

provider: Provider = st.sidebar.selectbox(  # type: ignore[assignment]
    "🔌 Provider",
    options=["ollama", "claude", "openai"],
    help=(
        "**ollama** — local, gratuito, requer Ollama instalado\n\n"
        "**claude** — Anthropic API (ANTHROPIC_API_KEY no .env)\n\n"
        "**openai** — OpenAI API (OPENAI_API_KEY no .env)"
    ),
)

agent_type: str = st.sidebar.radio(
    "🤖 Agente",
    [
        "Básico",
        "Com Memória",
        "Com Ferramentas",
        "RAG (Documentos)",
        "HITL (Human-in-the-Loop)",
        "Comparar Todos",
    ],
)

# Aviso de API key ausente
if provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
    st.sidebar.warning("⚠️ ANTHROPIC_API_KEY não encontrada no .env")
elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
    st.sidebar.warning("⚠️ OPENAI_API_KEY não encontrada no .env")

if agent_type == "HITL (Human-in-the-Loop)":
    st.sidebar.info(
        "**Human-in-the-Loop**\n\n"
        "O agente pausa antes de executar ações de alto impacto "
        "(enviar e-mail, deletar arquivo) e aguarda sua aprovação.\n\n"
        "Padrão: `interrupt()` + `MemorySaver` do LangGraph."
    )

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# Estado HITL: armazena o grafo compilado, config e status de aprovação pendente
if "hitl_agent" not in st.session_state:
    st.session_state.hitl_agent = None
if "hitl_config" not in st.session_state:
    st.session_state.hitl_config = None
if "hitl_pending" not in st.session_state:
    st.session_state.hitl_pending = None  # dict com info do interrupt ou None


# ---------------------------------------------------------------------------
# Fábrica de agentes
# ---------------------------------------------------------------------------


def get_agent(agent_name: str, prov: Provider):
    """Instancia o agente escolhido com o provider configurado."""
    if agent_name == "Básico":
        return create_basic_agent(prov)
    if agent_name == "Com Memória":
        return create_memory_agent(prov)
    if agent_name == "Com Ferramentas":
        return create_tool_agent(prov)
    if agent_name == "RAG (Documentos)":
        return create_rag_agent(prov)
    return None


# ---------------------------------------------------------------------------
# UI HITL — fluxo separado
# ---------------------------------------------------------------------------


def render_hitl_section(prov: Provider) -> None:
    """Renderiza o painel HITL com suporte a interrupt → aprovação → resume."""

    st.subheader("🔒 Agente HITL — Human-in-the-Loop")
    st.caption(
        "Demonstra `interrupt()` do LangGraph: o agente pausa antes de ações "
        "de alto impacto e aguarda aprovação explícita. Estado preservado via "
        "`MemorySaver` (checkpointing)."
    )

    # Exemplos de prompt pré-definidos
    with st.expander("💡 Exemplos de prompt", expanded=False):
        st.markdown(
            "- `Send an email to admin@example.com with subject 'Relatório' and body 'OK'`\n"
            "- `Delete the file /tmp/old_report.csv`\n"
            "- `What is 2 + 2?`  ← ferramenta segura, sem interrupt"
        )

    hitl_prompt = st.text_area(
        "Comando para o agente HITL:",
        placeholder="Ex: Send an email to ceo@company.com with subject 'Alerta crítico'...",
        key="hitl_prompt_input",
    )

    col_run, col_reset = st.columns([1, 4])
    with col_run:
        run_clicked = st.button("▶️ Executar", key="hitl_run")
    with col_reset:
        if st.button("🔄 Reset agente", key="hitl_reset"):
            st.session_state.hitl_agent = None
            st.session_state.hitl_config = None
            st.session_state.hitl_pending = None
            st.rerun()

    # ── Execução inicial ─────────────────────────────────────────────────
    if run_clicked and hitl_prompt.strip():
        # Cria (ou recria) o agente
        agent, config = create_hitl_agent(prov)
        st.session_state.hitl_agent = agent
        st.session_state.hitl_config = config
        st.session_state.hitl_pending = None

        messages = []
        with st.spinner("Processando…"):
            for event in agent.stream(
                {"messages": [HumanMessage(content=hitl_prompt)]},
                config=config,
                stream_mode="values",
            ):
                last = event["messages"][-1]
                if isinstance(last, AIMessage) and last.content:
                    messages.append(last.content)

        # Verifica se há interrupt pendente
        state = agent.get_state(config)
        interrupt_info = None
        if state.tasks:
            for task in state.tasks:
                if hasattr(task, "interrupts") and task.interrupts:
                    interrupt_info = task.interrupts[0].value
                    break

        if interrupt_info:
            st.session_state.hitl_pending = interrupt_info
        else:
            for msg in messages:
                st.success(msg)

        st.rerun()

    # ── Aprovação pendente ───────────────────────────────────────────────
    if st.session_state.hitl_pending and st.session_state.hitl_agent:
        pending = st.session_state.hitl_pending
        agent = st.session_state.hitl_agent
        config = st.session_state.hitl_config

        st.warning(pending.get("message", "⚠️ Aprovação necessária"))

        tool_calls = pending.get("tool_calls", [])
        if tool_calls:
            st.markdown("**Ações solicitadas:**")
            for tc in tool_calls:
                args_str = ", ".join(f"`{k}={v}`" for k, v in tc["args"].items())
                st.markdown(f"- `{tc['name']}({args_str})`")

        col_approve, col_reject = st.columns(2)

        with col_approve:
            if st.button("✅ Aprovar", type="primary", key="hitl_approve"):
                with st.spinner("Retomando execução…"):
                    messages = []
                    for event in agent.stream(
                        Command(resume={"approved": True}),
                        config=config,
                        stream_mode="values",
                    ):
                        last = event["messages"][-1]
                        if isinstance(last, AIMessage) and last.content:
                            messages.append(last.content)

                st.session_state.hitl_pending = None
                for msg in messages:
                    st.success(f"✅ {msg}")
                st.rerun()

        with col_reject:
            if st.button("❌ Rejeitar", key="hitl_reject"):
                with st.spinner("Cancelando…"):
                    messages = []
                    for event in agent.stream(
                        Command(resume={"approved": False}),
                        config=config,
                        stream_mode="values",
                    ):
                        last = event["messages"][-1]
                        if isinstance(last, AIMessage) and last.content:
                            messages.append(last.content)

                st.session_state.hitl_pending = None
                for msg in messages:
                    st.error(msg)
                st.rerun()


# ---------------------------------------------------------------------------
# Input e execução — agentes padrão
# ---------------------------------------------------------------------------

if agent_type == "HITL (Human-in-the-Loop)":
    render_hitl_section(provider)

else:
    prompt = st.text_area(
        "Digite sua pergunta ou comando:",
        placeholder="Ex: Resuma os KPIs financeiros do último trimestre...",
    )

    if st.button("💡 Executar") and prompt.strip():
        with st.spinner(f"Processando com **{provider}**..."):
            try:
                prompt_pt = f"Responda em português e seja breve: {prompt}"

                if agent_type != "Comparar Todos":
                    agent = get_agent(agent_type, provider)
                    output = agent(prompt_pt)
                    st.session_state.history.append(
                        {"role": "user", "content": prompt, "agent": agent_type}
                    )
                    st.session_state.history.append(
                        {"role": "assistant", "content": output, "agent": agent_type}
                    )
                    st.success(output)

                else:
                    cols = st.columns(4)
                    agents_to_compare = [
                        ("Básico", create_basic_agent(provider)),
                        ("Com Memória", create_memory_agent(provider)),
                        ("Com Ferramentas", create_tool_agent(provider)),
                        ("RAG (Documentos)", create_rag_agent(provider)),
                    ]
                    for col, (name, ag) in zip(cols, agents_to_compare):
                        with col:
                            st.markdown(f"**{name}**")
                            result = ag(prompt_pt)
                            st.write(result)

            except Exception as exc:  # noqa: BLE001
                st.error(f"Erro: {exc}")

    # Histórico de mensagens
    if st.session_state.history:
        st.divider()
        st.subheader("📜 Histórico")
        for entry in reversed(st.session_state.history[-10:]):
            role_icon = "🧑" if entry["role"] == "user" else "🤖"
            st.markdown(
                f"{role_icon} **{entry['role'].title()}** "
                f"<small>({entry.get('agent', '')})</small>",
                unsafe_allow_html=True,
            )
            st.write(entry["content"])
