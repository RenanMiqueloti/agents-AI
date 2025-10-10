from langchain_ollama import OllamaLLM
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool

def format_response(result):
    if isinstance(result, dict):
        for key in ["response", "result"]:
            if key in result:
                result = result[key]
                break
    result = result.replace("\n", " ").strip()
    sentences = result.split(". ")
    return ". ".join(sentences[:2]) + "."

def create_tool_agent():
    def soma(a, b): 
        return float(a) + float(b)

    tools = [
        Tool(
            name="Soma",
            func=lambda x: soma(*x.split()),
            description="Soma dois números separados por espaço"
        )
    ]

    llm = OllamaLLM(model="llama3")
    agent = initialize_agent(
        tools,
        llm,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False
    )

    def run(prompt: str):
        response = agent.run(prompt)
        return format_response(response)
    return run
