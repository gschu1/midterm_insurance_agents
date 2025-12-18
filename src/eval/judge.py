import json
import os
import re
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


def normalize_text(text: str) -> str:
    """
    Normalize text for exact matching: lowercase, remove punctuation, normalize whitespace.
    """
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    # Normalize whitespace
    text = ' '.join(text.split())
    return text


def compute_exact_match(system_answer: str, ground_truth: str) -> bool:
    """
    Compute exact match (0 or 1) after normalization.
    """
    norm_system = normalize_text(system_answer)
    norm_ground = normalize_text(ground_truth)
    return norm_system == norm_ground


def compute_context_hit(context_text: str, ground_truth: str) -> bool:
    """
    Check if the retrieved context contains the ground-truth substring (after normalization).
    """
    norm_context = normalize_text(context_text)
    norm_ground = normalize_text(ground_truth)
    # Check if ground truth (or key parts) appear in context
    # For short ground truths, check exact substring
    if len(norm_ground) < 20:
        return norm_ground in norm_context
    # For longer ground truths, check if key words/phrases appear
    ground_words = set(norm_ground.split())
    context_words = set(norm_context.split())
    # Require at least 70% of ground truth words to appear
    if len(ground_words) > 0:
        overlap = len(ground_words & context_words) / len(ground_words)
        return overlap >= 0.7
    return False


def judge_case(
    client: OpenAI,
    question: str,
    ground_truth: str,
    system_answer: str,
    context_text: str,
) -> Dict[str, Any]:
    """
    Call an LLM-as-a-judge to score:
    - correctness: 1–5 (renamed to llm_correctness)
    - relevance:   1–5
    - recall:      1–5

    Also computes:
    - exact_match: 0 or 1 (boolean)
    - context_hit: 0 or 1 (boolean)

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
            "llm_correctness": None,
            "relevance_score": None,
            "recall_score": None,
            "correctness_explanation": content,
            "relevance_explanation": "",
            "recall_explanation": "",
        }
    
    # Rename correctness_score to llm_correctness for clarity
    if "correctness_score" in data:
        data["llm_correctness"] = data.pop("correctness_score")
    if "correctness_explanation" in data:
        data["llm_correctness_explanation"] = data.pop("correctness_explanation")
    
    # Compute exact_match and context_hit
    data["exact_match"] = 1 if compute_exact_match(system_answer, ground_truth) else 0
    data["context_hit"] = 1 if compute_context_hit(context_text, ground_truth) else 0

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
        llm_corr = judge_result.get('llm_correctness', judge_result.get('correctness_score', 'N/A'))
        print(
            f"Metrics: llm_correctness={llm_corr}, "
            f"exact_match={judge_result.get('exact_match', 0)}, "
            f"context_hit={judge_result.get('context_hit', 0)}"
        )

    # Compute simple averages for all metrics
    scored = [r for r in results if r.get("llm_correctness") is not None or r.get("correctness_score") is not None]
    
    # Initialize averages
    avg_llm_corr = 0.0
    avg_rel = 0.0
    avg_rec = 0.0
    avg_exact = 0.0
    avg_context = 0.0
    
    if scored:
        # Handle both old and new field names
        llm_scores = [r.get("llm_correctness") or r.get("correctness_score") for r in scored]
        valid_llm_scores = [s for s in llm_scores if s is not None]
        avg_llm_corr = sum(valid_llm_scores) / len(valid_llm_scores) if valid_llm_scores else 0.0
        avg_rel = sum(r.get("relevance_score", 0) for r in scored) / len(scored) if scored else 0.0
        avg_rec = sum(r.get("recall_score", 0) for r in scored) / len(scored) if scored else 0.0
    
    if results:
        avg_exact = sum(r.get("exact_match", 0) for r in results) / len(results)
        avg_context = sum(r.get("context_hit", 0) for r in results) / len(results)

    print("\n" + "=" * 80)
    print("Summary Metrics (averages over all test cases):")
    print(f"{'Metric':<20} {'Value':<10}")
    print("-" * 30)
    print(f"{'llm_correctness':<20} {avg_llm_corr:<10.2f}")
    print(f"{'exact_match':<20} {avg_exact:<10.2f}")
    print(f"{'context_hit':<20} {avg_context:<10.2f}")
    if scored:
        print(f"{'relevance_score':<20} {avg_rel:<10.2f}")
        print(f"{'recall_score':<20} {avg_rec:<10.2f}")
    
    # Write eval_report.json
    report_path = PROJECT_ROOT / "eval" / "eval_report.json"
    summary = {
        "total_cases": len(results),
        "averages": {
            "llm_correctness": avg_llm_corr,
            "exact_match": avg_exact,
            "context_hit": avg_context,
            "relevance_score": avg_rel,
            "recall_score": avg_rec,
        },
        "results": results,
    }
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Evaluation report written to: {report_path}")


if __name__ == "__main__":
    run_evaluation()
