# agents/memory_agent.py
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate

# Cria memória global para a sessão
memory = ConversationBufferMemory(memory_key="history", return_messages=True)

# Prompt template compatível com LangChain v0.3+
prompt_template = ChatPromptTemplate.from_template(
    "{history}\nHuman: {input}\nAI:"
)

# Cria a cadeia de conversa
conversation = ConversationChain(
    llm=Ollama(model="llama3"), 
    memory=memory, 
    prompt=prompt_template
)

def format_response(result):
    """Formata a resposta: limpa, curta e em português"""
    # Se for dict, extrai resposta
    if isinstance(result, dict):
        for key in ["response", "result"]:
            if key in result:
                result = result[key]
                break

    # Remove quebras de linha e excesso de espaço
    result = result.replace("\n", " ").strip()

    # Remove pontuação duplicada
    while ".." in result:
        result = result.replace("..", ".")

    # Limita a 2 frases
    sentences = result.split(". ")
    short_response = ". ".join(sentences[:2]).strip()

    # Garante ponto final
    if not short_response.endswith("."):
        short_response += "."

    return short_response

def create_memory_agent():
    """Retorna a função que executa o agente com memória"""
    def run(prompt_text):
        # Força português e respostas curtas
        prompt_pt = f"Responda em português e seja breve: {prompt_text}"
        result = conversation.predict(input=prompt_pt)
        return format_response(result)
    return run
