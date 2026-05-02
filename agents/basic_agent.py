"""Agente básico — responde perguntas gerais sem memória nem ferramentas."""
from agents.provider import Provider, get_llm


def format_response(result: object) -> str:
    """Normaliza a saída do LLM para string curta (máx. 2 frases).

    Args:
        result: Saída bruta do LLM (AIMessage, str ou dict).

    Returns:
        Texto limpo terminado em ponto final.
    """
    if hasattr(result, "content"):
        result = result.content  # type: ignore[union-attr]
    if isinstance(result, dict):
        for key in ("response", "result"):
            if key in result:
