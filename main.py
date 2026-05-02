import os

import streamlit as st
from dotenv import load_dotenv

from agents.basic_agent import create_basic_agent
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
    ["Básico", "Com Memória", "Com Ferramentas", "RAG (Documentos)", "Comparar Todos"],
)

# Aviso de API key ausente
if provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
    st.sidebar.warning("⚠️ ANTHROPIC_API_KEY não encontrada no .env")
elif provider == "openai" and not os.getenv("OPENAI_API_KEY"):
    st.sidebar.warning("⚠️ OPENAI_API_KEY não encontrada no .env")

# ---------------------------------------------------------------------------
# Histórico
# ---------------------------------------------------------------------------
if "history" not in st.session_state:
    st.session_state.history = []

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
# Input e execução
# ---------------------------------------------------------------------------
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
     