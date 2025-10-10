import streamlit as st
from agents.basic_agent import create_basic_agent
from agents.memory_agent import create_memory_agent
from agents.tool_agent import create_tool_agent
from agents.rag_agent import create_rag_agent

# Configuração do dashboard
st.set_page_config(
    page_title="IA Agents",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
# 🤖 IA Agents 
Painel pessoal para explorar diferentes agentes de IA locais.  
Respostas curtas, limpas e diretas, com histórico e comparação entre agentes.
""")

# Inicializa histórico
if "history" not in st.session_state:
    st.session_state.history = []

# Sidebar: escolha do agente
agent_type = st.sidebar.radio(
    "Selecione o agente:",
    ["Básico", "Com Memória", "Com Ferramentas", "RAG (Documentos)", "Comparar Todos"]
)

# Função para criar agente
def get_agent(agent_name):
    if agent_name == "Básico":
        return create_basic_agent()
    elif agent_name == "Com Memória":
        return create_memory_agent()
    elif agent_name == "Com Ferramentas":
        return create_tool_agent()
    elif agent_name == "RAG (Documentos)":
        return create_rag_agent()
    return None

# Input do usuário
prompt = st.text_area(
    "Digite sua pergunta ou comando:",
    placeholder="Ex: Resuma os KPIs financeiros do último trimestre..."
)

# Botão de execução
if st.button("💡 Executar") and prompt.strip():
    with st.spinner("Processando..."):
        try:
            # Adiciona instrução para o modelo responder em português
            prompt_pt = f"Responda em português e seja breve: {prompt}"

            if agent_type != "Comparar Todos":
                agent = get_agent(agent_type)
                output = agent(prompt_pt)
                st.session_state.history.append({"prompt": prompt, agent_type: output})
                st.markdown(f"### Resultado ({agent_type})")
                st.success(output)
            else:
                # Comparar todos os agentes
                agents = {
                    "Básico": create_basic_agent(),
                    "Com Memória": create_memory_agent(),
                    #"Com Ferramentas": create_tool_agent(),
                    "RAG": create_rag_agent()
                }
                outputs = {name: agent(prompt_pt) for name, agent in agents.items()}
                st.session_state.history.append({"prompt": prompt, **outputs})

                # Mostrar resultados lado a lado
                st.markdown("### Comparação entre agentes")
                cols = st.columns(len(outputs))
                for i, (name, out) in enumerate(outputs.items()):
                    with cols[i]:
                        st.subheader(name)
                        st.info(out)
        except Exception as e:
            st.error(f"Erro ao processar: {e}")

# Mostrar histórico
if st.checkbox("📂 Ver histórico"):
    st.markdown("## Histórico de Interações")
    for idx, entry in enumerate(reversed(st.session_state.history), 1):
        st.markdown(f"**{idx}. Pergunta:** {entry['prompt']}")
        for agent_name, response in entry.items():
            if agent_name != "prompt":
                st.markdown(f"- **{agent_name}:** {response}")
        st.markdown("---")
