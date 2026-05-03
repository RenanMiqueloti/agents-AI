"""Harness de evals para o painel agents-AI.

Avalia agentes individuais (basic, tool, memory) com LLM-as-judge.
Métricas: correctness, helpfulness, conciseness.

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
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

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
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
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


def run_evals(provider: str = "openai") -> list[dict]:
    """Executa o dataset e retorna resultados com scores.

    Args:
        provider: Provider a usar para os agentes (``"ollama"``, ``"claude"``, ``"openai"``).

    Returns:
        Lista de resultados com prompt, answer e scores.
    """
    from agents.basic_agent import create_basic_agent
    from agents.memory_agent import create_memory_agent
    from agents.tool_agent import create_tool_agent

    agents_map = {
        "basic": create_basic_agent(provider),  # type: ignore[arg-type]
        "tool": create_tool_agent(provider),    # type: ignore[arg-type]
        "memory": create_memory_agent(provider), # type: ignore[arg-type]
    }

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
        except Exception as exc:  # noqa: BLE001
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
        print(f"[{entry['id']}][{entry['agent']}] C:{c} H:{h} N:{n} — {scores['reasoning']}")

    # Aggregate
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

    print(f"\n📊 Resumo — {summary['n']} evals | provider: {provider}")
    print(f"   Correctness:  {summary['avg_correctness']:.2f} / 5")
    print(f"   Helpfulness:  {summary['avg_helpfulness']:.2f} / 5")
    print(f"   Conciseness:  {summary['avg_conciseness']:.2f} / 5")

    output = {"summary": summary, "results": results}
    RESULTS_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"\n💾 Resultados salvos em {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("⚠️  Defina OPENAI_API_KEY para o juiz LLM no .env")
    run_evals()
