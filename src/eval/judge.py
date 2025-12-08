import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

# Make sure we can import modules from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from indexing import get_query_engines  # noqa: E402
from agents.summarizer_agent import SummarizationAgent  # noqa: E402
from agents.needle_agent import NeedleAgent  # noqa: E402
from agents.manager import ManagerAgent  # noqa: E402


def build_manager() -> ManagerAgent:
    """Instantiate all agents and return the manager."""
    engines = get_query_engines()
    summarizer = SummarizationAgent(engines["summary_engine"])
    needle = NeedleAgent(engines["needle_engine"])
    return ManagerAgent(summarizer, needle)


def load_test_cases() -> List[Dict[str, Any]]:
    tests_path = PROJECT_ROOT / "eval" / "test_cases.json"
    with open(tests_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_judge_client() -> OpenAI:
    load_dotenv()
    # OPENAI_API_KEY is read from environment; same as the main system.
    return OpenAI()


def judge_case(
    client: OpenAI,
    question: str,
    ground_truth: str,
    system_answer: str,
    context_text: str,
) -> Dict[str, Any]:
    """
    Call an LLM-as-a-judge to score:
    - correctness: 1–5
    - relevance:   1–5
    - recall:      1–5

    Returns a dict with scores and explanations.
    """
    system_prompt = (
        "You are an impartial evaluator for a question-answering system over an "
        "insurance claim. You will receive:\n"
        "- the user question\n"
        "- the ground truth answer\n"
        "- the system's answer\n"
        "- the retrieved context\n\n"
        "Evaluate three dimensions on a scale from 1 to 5 (integers):\n"
        "1) correctness_score: how factually correct the system's answer is "
        "compared to the ground truth.\n"
        "2) relevance_score: how relevant the retrieved context is to the question.\n"
        "3) recall_score: whether the retrieved context contains the key information "
        "needed to answer the question.\n\n"
        "Return ONLY a JSON object with the following keys:\n"
        "{\n"
        "  \"correctness_score\": int,\n"
        "  \"relevance_score\": int,\n"
        "  \"recall_score\": int,\n"
        "  \"correctness_explanation\": str,\n"
        "  \"relevance_explanation\": str,\n"
        "  \"recall_explanation\": str\n"
        "}\n"
    )

    user_content = (
        f"Question: {question}\n\n"
        f"Ground truth answer: {ground_truth}\n\n"
        f"System answer: {system_answer}\n\n"
        f"Retrieved context:\n{context_text}\n"
    )

    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
    )

    content = resp.choices[0].message.content
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: wrap the raw content if parsing fails.
        data = {
            "correctness_score": None,
            "relevance_score": None,
            "recall_score": None,
            "correctness_explanation": content,
            "relevance_explanation": "",
            "recall_explanation": "",
        }

    return data


def run_evaluation():
    tests = load_test_cases()
    manager = build_manager()
    client = build_judge_client()

    results: List[Dict[str, Any]] = []

    for case in tests:
        q = case["question"]
        gt = case["ground_truth"]

        print("\n" + "=" * 80)
        print(f"Test {case['id']} – {case['type']}")
        print(f"Q: {q}")

        system_result = manager.answer(q)
        system_answer = system_result["answer"]

        # Concatenate retrieved context snippets
        sources = system_result.get("sources", [])
        context_text = "\n\n---\n\n".join(
            s.get("text", "") for s in sources if s.get("text")
        )

        judge_result = judge_case(
            client,
            question=q,
            ground_truth=gt,
            system_answer=system_answer,
            context_text=context_text,
        )

        # Merge and print
        record = {
            "id": case["id"],
            "type": case["type"],
            "question": q,
            "ground_truth": gt,
            "system_answer": system_answer,
            **judge_result,
        }
        results.append(record)

        print(f"System answer: {system_answer}")
        print(
            f"Scores: correctness={judge_result['correctness_score']}, "
            f"relevance={judge_result['relevance_score']}, "
            f"recall={judge_result['recall_score']}"
        )

    # Compute simple averages
    scored = [r for r in results if r["correctness_score"] is not None]
    if scored:
        avg_corr = sum(r["correctness_score"] for r in scored) / len(scored)
        avg_rel = sum(r["relevance_score"] for r in scored) / len(scored)
        avg_rec = sum(r["recall_score"] for r in scored) / len(scored)

        print("\n" + "=" * 80)
        print("Average scores over all test cases:")
        print(f"- Correctness: {avg_corr:.2f}")
        print(f"- Relevance:   {avg_rel:.2f}")
        print(f"- Recall:      {avg_rec:.2f}")


if __name__ == "__main__":
    run_evaluation()
