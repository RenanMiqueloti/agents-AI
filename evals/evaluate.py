"""Harness de evals para o painel agents-AI.

Avalia agentes (basic, tool, memory, rag, hitl) com LLM-as-judge.
Métricas: correctness, helpfulness, conciseness.

Cobertura de HITL via adapters que simulam decisões automáticas:
- ``hitl_approve``: aprova interrupts — testa happy path completo
- ``hitl_reject``: rejeita interrupts — testa cancellation path
- ``hitl_safe``: prompts sem tool call de alto impacto — testa que o
  router NÃO dispara interrupt indevido

Uso:
    python -m evals.evaluate

Requisitos:
    ANTHROPIC_API_KEY ou OPENAI_API_KEY no .env (para o agente avaliado)
    OPENAI_API_KEY (para o juiz LLM)
"""

from __future__ import annotations

import json
import os
import statistics
import uuid
from collections.abc import Callable
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

load_dotenv()

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_PATH = Path(__file__).parent / "results.json"


def load_dataset() -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


def llm_as_judge(prompt: str, answer: str, expected: str | None = None) -> dict:
    """Avalia a resposta do agente em três dimensões.

    Args:
        prompt: Pergunta ou instrução enviada ao agente.
        answer: Resposta gerada pelo agente.
        expected: Temas/valores esperados na resposta.

    Returns:
        Dict com scores de correctness, helpfulness, conciseness e reasoning.
    """
    llm = ChatOpenAI(model="gpt-5-mini", temperature=0)
    expected_section = f"\nExpected: {expected}" if expected else ""

    judge_prompt = f"""You are an expert evaluator of AI agent responses.
Rate the following agent response on three dimensions (1–5 integer scale).

User prompt: {prompt}
Agent response: {answer}{expected_section}

Scoring:
  1 = Very poor | 2 = Poor | 3 = Acceptable | 4 = Good | 5 = Excellent

Dimensions:
  correctness  — Is the answer factually correct and accurate?
  helpfulness  — Does the response actually help the user?
  conciseness  — Is the response appropriately brief without missing key info?

Return valid JSON only:
{{"correctness": <int>, "helpfulness": <int>, "conciseness": <int>, "reasoning": "<one sentence>"}}"""

    response = llm.invoke(judge_prompt)
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "correctness": 0,
            "helpfulness": 0,
            "conciseness": 0,
            "reasoning": response.content,
        }


def make_hitl_adapter(provider: str, decision: str) -> Callable[[str], str]:
    """Adapter síncrono para o agente HITL, simulando decisão automática.

    Args:
        provider: ``"ollama"``, ``"claude"`` ou ``"openai"``.
        decision: ``"approve"`` (aprova interrupts), ``"reject"`` (rejeita)
            ou ``"safe"`` (espera que nenhum interrupt seja disparado — o
            prompt não deve invocar tools de alto impacto).

    Returns:
        Função ``prompt → str`` que executa o agente HITL e simula a decisão
        configurada quando há ``interrupt()``. Cada chamada usa um
        ``thread_id`` único para isolar o estado entre samples do dataset.
    """
    from agents.hitl_agent import create_hitl_agent

    def fn(prompt: str) -> str:
        agent, _ = create_hitl_agent(provider)
        config = {"configurable": {"thread_id": f"eval-{decision}-{uuid.uuid4()}"}}

        replies: list[str] = []
        for event in agent.stream(
            {"messages": [HumanMessage(content=prompt)]},
            config=config,
            stream_mode="values",
        ):
            last = event["messages"][-1]
            if isinstance(last, AIMessage) and last.content:
                replies.append(last.content)

        state = agent.get_state(config)
        pending = bool(state.tasks and any(getattr(t, "interrupts", None) for t in state.tasks))

        if pending and decision in ("approve", "reject"):
            approved = decision == "approve"
            for event in agent.stream(
                Command(resume={"approved": approved}),
                config=config,
                stream_mode="values",
            ):
                last = event["messages"][-1]
                if isinstance(last, AIMessage) and last.content:
                    replies.append(last.content)
        elif pending and decision == "safe":
            replies.append(
                "[FALHA DE EVAL] Prompt classificado como safe mas o agente "
                "disparou interrupt() — possível regressão no router."
            )

        return replies[-1] if replies else "(sem resposta gerada)"

    return fn


def build_agents_map(provider: str) -> dict[str, Callable[[str], str]]:
    """Constrói o dicionário de agentes disponíveis para o eval."""
    from agents.basic_agent import create_basic_agent
    from agents.memory_agent import create_memory_agent
    from agents.rag_agent import create_rag_agent
    from agents.tool_agent import create_tool_agent

    return {
        "basic": create_basic_agent(provider),  # type: ignore[arg-type]
        "tool": create_tool_agent(provider),  # type: ignore[arg-type]
        "memory": create_memory_agent(provider),  # type: ignore[arg-type]
        "rag": create_rag_agent(provider),  # type: ignore[arg-type]
        "hitl_approve": make_hitl_adapter(provider, "approve"),
        "hitl_reject": make_hitl_adapter(provider, "reject"),
        "hitl_safe": make_hitl_adapter(provider, "safe"),
    }


def run_evals(provider: str = "openai") -> list[dict]:
    """Executa o dataset e retorna resultados com scores.

    Args:
        provider: Provider para os agentes (``"ollama"``, ``"claude"``, ``"openai"``).

    Returns:
        Lista de resultados com prompt, answer e scores. Persistidos em
        ``evals/results.json`` com sumário agregado por dimensão.
    """
    agents_map = build_agents_map(provider)
    dataset = load_dataset()
    results = []

    print(f"▶ Rodando {len(dataset)} evals com provider='{provider}'...\n")

    for sample in dataset:
        agent_fn = agents_map.get(sample["agent"])
        if agent_fn is None:
            print(f"[SKIP] Agente desconhecido: {sample['agent']}")
            continue

        try:
            answer = agent_fn(sample["prompt"])
        except Exception as exc:
            answer = f"ERROR: {exc}"

        scores = llm_as_judge(sample["prompt"], answer, sample.get("expected_themes"))

        entry = {
            "id": sample["id"],
            "agent": sample["agent"],
            "prompt": sample["prompt"],
            "answer": answer,
            "scores": scores,
        }
        results.append(entry)

        c = scores["correctness"]
        h = scores["helpfulness"]
        n = scores["conciseness"]
        print(f"[{entry['id']}][{entry['agent']:>13}] C:{c} H:{h} N:{n} — {scores['reasoning']}")

    def avg(key: str) -> float:
        vals = [r["scores"][key] for r in results if r["scores"][key] > 0]
        return round(statistics.mean(vals), 2) if vals else 0.0

    summary = {
        "n": len(results),
        "provider": provider,
        "avg_correctness": avg("correctness"),
        "avg_helpfulness": avg("helpfulness"),
        "avg_conciseness": avg("conciseness"),
    }

    print(f"\nResumo — {summary['n']} evals | provider: {provider}")
    print(f"   Correctness:  {summary['avg_correctness']:.2f} / 5")
    print(f"   Helpfulness:  {summary['avg_helpfulness']:.2f} / 5")
    print(f"   Conciseness:  {summary['avg_conciseness']:.2f} / 5")

    output = {"summary": summary, "results": results}
    RESULTS_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\nResultados salvos em {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Defina OPENAI_API_KEY para o juiz LLM no .env")
    run_evals()
