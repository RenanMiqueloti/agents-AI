"""Agente com ferramentas usando create_react_agent do LangGraph.

Substitui o initialize_agent + AgentType.ZERO_SHOT_REACT_DESCRIPTION deprecated
pelo padrão atual: create_react_agent do langgraph.prebuilt com @tool decorators.
"""
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent


@tool
def soma(expressao: str) -> float:
    """Soma dois números separados por espaço.

    Args:
        expressao: String com dois números separados por espaço. Ex: '3 4'

    Returns:
        Resultado da soma como float.

    Raises:
        ValueError: Se a expressão não contiver exatamente dois números.
    """
    partes = expressao.strip().split()
    if len(partes) != 2:
        raise ValueError(f"Esperado dois números separados por espaço, recebi: {expressao!r}")
    return float(partes[0]) + float(partes[1])


def format_response(text: str) -> str:
    """Limpa e trunca a resposta para no máximo 2 frases.

    Args:
        text: Texto bruto retornado pelo modelo.

    Returns:
        Resposta formatada com ponto final garantido.
    """
    text = text.replace("\n", " ").strip()
    sentences = text.split(". ")
    short = ". ".join(sentences[:2]).strip()
    if not short.endswith("."):
        short += "."
    return short


def create_tool_agent():
    """Retorna uma função que executa o agente com ferramentas via LangGraph.

    Usa create_react_agent (ReAct loop) com ChatOllama como modelo base
    e a ferramenta 'soma' como exemplo de tool-use local.

    Returns:
        Callable[[str], str]: função que recebe um prompt e retorna a resposta.
    """
    llm = ChatOllama(model="llama3")
    agent = create_react_agent(llm, tools=[soma])

    def run(prompt: str) -> str:
        result = agent.invoke(
            {"messages": [("human", f"Responda em português e seja breve: {prompt}")]}
        )
        last_msg = result["messages"][-1]
        return format_response(last_msg.content)
    return run
