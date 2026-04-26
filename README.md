# Agents AI Dashboard

Painel pessoal em Streamlit para testar e comparar agentes de IA locais. O projeto foi montado como um laboratorio pratico para explorar comportamentos diferentes de agentes usando Ollama, LangChain e documentos locais.

## O que o projeto faz

- executa uma interface web local com Streamlit
- permite alternar entre diferentes tipos de agente
- mantem historico das interacoes na sessao
- compara respostas de varios agentes lado a lado
- consulta documentos locais com um fluxo simples de RAG

## Tipos de agentes

- Basico: responde perguntas gerais
- Com memoria: reaproveita o contexto da conversa atual
- Com ferramentas: executa operacoes simples via tools
- RAG: consulta documentos em `data/docs/`
- Comparar todos: mostra respostas em paralelo

## Stack

- Python
- Streamlit
- LangChain
- Ollama
- Llama 3
- FAISS

## Estrutura do repositorio

```text
.
|-- main.py
|-- agents/
|   |-- basic_agent.py
|   |-- memory_agent.py
|   |-- rag_agent.py
|   `-- tool_agent.py
|-- data/
|   `-- docs/
|       `-- exemplo.txt
|-- dashboard_principal.png
|-- comparacao_agentes.png
|-- rag_agentes.png
`-- requirements.txt
```

## Como executar

### Pre-requisitos

- Python 3.10+
- Ollama instalado
- um modelo local disponivel no Ollama, como `llama3`

### Passos

```bash
git clone https://github.com/RenanMiqueloti/agents-AI.git
cd agents-AI
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
ollama pull llama3
streamlit run main.py
```

Depois disso, abra `http://localhost:8501`.

## Como usar

1. Escolha o tipo de agente na barra lateral.
2. Digite uma pergunta ou comando.
3. Clique em `Executar`.
4. Se quiser comparar abordagens, use `Comparar Todos`.
5. Ative o historico para revisar interacoes anteriores.

## Arquivos visuais

- `dashboard_principal.png`
- `comparacao_agentes.png`
- `rag_agentes.png`

## Status

Projeto funcional como ambiente de estudo e experimentacao. O foco aqui e exploracao de agentes locais, nao produto final.
