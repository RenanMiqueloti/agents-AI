# agents-AI

Painel Streamlit para explorar e comparar agentes de IA com suporte a múltiplos providers: **Ollama** (local/gratuito), **Claude** (Anthropic) e **OpenAI**.

O projeto demonstra padrões de produção com LangChain 0.3+: LCEL chains, `create_react_agent` do LangGraph, RAG sem APIs deprecated e abstração de provider.

![dashboard](dashboard_principal.png)

## Agentes disponíveis

| Agente | Descrição | Padrão |
|---|---|---|
| Básico | Responde perguntas gerais | LCEL chain simples |
| Com Memória | Mantém contexto da conversa | `RunnableWithMessageHistory` |
| Com Ferramentas | Executa tools (soma, data atual) | `create_react_agent` (LangGraph) |
| RAG | Consulta documentos em `data/docs/` | LCEL RAG chain + FAISS |

## Providers suportados

| Provider | Modelo | Requer |
|---|---|---|
| `ollama` | llama3 | [Ollama](https://ollama.ai) instalado |
| `claude` | claude-3-5-haiku-20241022 | `ANTHROPIC_API_KEY` no `.env` |
| `openai` | gpt-4o-mini | `OPENAI_API_KEY` no `.env` |

## Stack

- Python 3.10+, Streamlit
- LangChain 0.3+ (LCEL), LangGraph 0.4+ (`create_react_agent`)
- LangChain-Anthropic / LangChain-OpenAI / LangChain-Ollama
- FAISS (índice vetorial local)

## Estrutura

```text
.
├── main.py                  # dashboard Streamlit
├── agents/
│   ├── provider.py          # fábrica de LLMs por provider
│   ├── basic_agent.py
│   ├── memory_agent.py
│   ├── tool_agent.py        # LangGraph ReAct + tools
│   └── rag_agent.py         # LCEL RAG chain
├── data/docs/               # coloque seus .txt aqui para o agente RAG
└── requirements.txt
```

## Como executar

```bash
git clone https://github.com/RenanMiqueloti/agents-AI.git
cd agents-AI
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crie um `.env` com as chaves que for usar (opcional para Ollama):

```env
ANTHROPIC_API_KEY=sk-ant-...   # para