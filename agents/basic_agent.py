from langchain_ollama import OllamaLLM

def format_response(result):
    if isinstance(result, dict):
        for key in ["response", "result"]:
            if key in result:
                result = result[key]
                break
    result = result.replace("\n", " ").strip()
    sentences = result.split(". ")
    return ". ".join(sentences[:2]) + "."

def create_basic_agent():
    llm = OllamaLLM(model="llama3")  # modelo gratuito local
    def run(prompt: str):
        response = llm.invoke(prompt)
        return format_response(response)
    return run
