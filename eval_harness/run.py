import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from eval_harness.adapter import answer_question
from eval_harness.graders.code_graders import GradeResult, grade_answer
from eval_harness.graders.hitl import export_hitl_pack, import_labels, score_labels
from eval_harness.graders.llm_judge import judge_answer
from dotenv import load_dotenv

RUNS_DIR = Path(__file__).resolve().parent / "runs"
TASKS_DIR = Path(__file__).resolve().parent / "tasks"


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _ensure_dirs(run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    transcripts = run_dir / "transcripts"
    transcripts.mkdir(parents=True, exist_ok=True)
    return transcripts


def _store_transcript(transcripts_dir: Path, task_id: str, payload: Dict[str, Any]) -> Path:
    path = transcripts_dir / f"{task_id}.json"
    _write_json(path, payload)
    return path


def _require_openai_key() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set. Create a .env file before running model suite.")


def run_code_suite(tasks: List[Dict[str, Any]], run_dir: Path) -> Dict[str, Any]:
    transcripts_dir = _ensure_dirs(run_dir)
    results: List[Dict[str, Any]] = []
    passed = 0

    for task in tasks:
        question = task["question"]
        response = answer_question(question)
        answer = response.get("answer", "")
        grade: GradeResult = grade_answer(answer, task.get("expected", {}))
        transcript_path = _store_transcript(
            transcripts_dir,
            task["id"],
            {"question": question, "answer": answer, "chosen_agent": response.get("chosen_agent")},
        )
        result = {
            "id": task["id"],
            "type": task["type"],
            "question": question,
            "answer": answer,
            "pass": grade.passed,
            "reason": grade.reason,
            "normalized_answer": grade.normalized_answer,
            "normalized_expected": grade.normalized_expected,
            "expected": task.get("expected"),
            "transcript_path": str(transcript_path),
        }
        if grade.passed:
            passed += 1
        results.append(result)

    summary = {
        "suite": "code",
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }
    _write_json(run_dir / "results_code.json", summary)
    return summary


def run_model_suite(tasks: List[Dict[str, Any]], run_dir: Path, k: int) -> Dict[str, Any]:
    _require_openai_key()
    transcripts_dir = _ensure_dirs(run_dir)
    model = os.getenv("EVAL_HARNESS_MODEL", "gpt-3.5-turbo")

    results: List[Dict[str, Any]] = []
    pass_at_1 = 0
    pass_at_k = 0
    score_sum = 0.0
    score_count = 0

    for task in tasks:
        question = task["question"]
        response = answer_question(question)
        answer = response.get("answer", "")
        transcript_path = _store_transcript(
            transcripts_dir,
            task["id"],
            {"question": question, "answer": answer, "chosen_agent": response.get("chosen_agent")},
        )

        trials: List[Dict[str, Any]] = []
        for _ in range(max(k, 1)):
            judged = judge_answer(
                question=question,
                answer=answer,
                rubric=task["rubric"],
                must_allow_insufficient=task.get("must_allow_insufficient_evidence", True),
                model=model,
            )
            parsed = judged.get("parsed") or {}
            trial = {
                "valid_json": judged["valid_json"],
                "raw": judged["raw"],
                "error": judged["error"],
            }
            if judged["valid_json"]:
                trial.update(parsed)
                score = parsed.get("score_1_to_5")
                if isinstance(score, int):
                    score_sum += score
                    score_count += 1
            trials.append(trial)

        trial_passes = [t.get("verdict") == "pass" for t in trials if t.get("valid_json")]
        pass_first = bool(trial_passes[0]) if trial_passes else False
        pass_any = any(trial_passes)
        if pass_first:
            pass_at_1 += 1
        if pass_any:
            pass_at_k += 1

        results.append(
            {
                "id": task["id"],
                "type": task["type"],
                "question": question,
                "answer": answer,
                "rubric": task["rubric"],
                "must_allow_insufficient_evidence": task.get("must_allow_insufficient_evidence", True),
                "trials": trials,
                "pass_at_1": pass_first,
                "pass_at_k": pass_any,
                "transcript_path": str(transcript_path),
            }
        )

    average_score = score_sum / score_count if score_count else 0.0
    summary = {
        "suite": "model",
        "total": len(results),
        "k": k,
        "pass_at_1": pass_at_1,
        "pass_at_k": pass_at_k,
        "average_score": average_score,
        "results": results,
    }
    _write_json(run_dir / "results_model.json", summary)
    return summary


def run_hitl_suite(
    tasks: List[Dict[str, Any]],
    run_dir: Path,
    labels_path: Optional[Path],
) -> Dict[str, Any]:
    transcripts_dir = _ensure_dirs(run_dir)
    answers: Dict[str, Dict[str, Any]] = {}
    for task in tasks:
        response = answer_question(task["question"])
        answers[task["id"]] = {
            "answer": response.get("answer", ""),
            "chosen_agent": response.get("chosen_agent"),
        }
        _store_transcript(
            transcripts_dir,
            task["id"],
            {"question": task["question"], "answer": response.get("answer", "")},
        )

    export_path = export_hitl_pack(tasks, answers, run_dir)
    summary: Dict[str, Any] = {
        "suite": "hitl",
        "total": len(tasks),
        "export_path": str(export_path),
        "imported": False,
        "summary": None,
        "results": None,
    }

    if labels_path:
        labeled_records = import_labels(labels_path)
        metrics = score_labels(labeled_records)
        _write_json(run_dir / "hitl_summary.json", metrics)
        summary.update(
            {
                "imported": True,
                "summary": metrics,
                "results": labeled_records,
            }
        )

    _write_json(run_dir / "results_hitl.json", summary)
    return summary


def build_report(
    run_dir: Path,
    code_summary: Optional[Dict[str, Any]],
    model_summary: Optional[Dict[str, Any]],
    hitl_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    report = {
        "run_id": run_dir.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "code": code_summary,
        "model": model_summary,
        "hitl": hitl_summary,
    }
    _write_json(run_dir / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Lesson-19 evaluation harness runner")
    parser.add_argument("--suite", choices=["code", "model", "hitl", "all"], default="all")
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--hitl-labels", type=str, default=None)
    args = parser.parse_args()

    run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        run_dir / "config.json",
        {"suite": args.suite, "k": args.k, "hitl_labels": args.hitl_labels},
    )

    code_summary = None
    model_summary = None
    hitl_summary = None

    if args.suite in {"code", "all"}:
        code_tasks = _load_jsonl(TASKS_DIR / "code.jsonl")
        code_summary = run_code_suite(code_tasks, run_dir)

    if args.suite in {"model", "all"}:
        model_tasks = _load_jsonl(TASKS_DIR / "model.jsonl")
        model_summary = run_model_suite(model_tasks, run_dir, k=args.k)

    if args.suite in {"hitl", "all"}:
        hitl_tasks = _load_jsonl(TASKS_DIR / "hitl.jsonl")
        labels_path = Path(args.hitl_labels) if args.hitl_labels else None
        hitl_summary = run_hitl_suite(hitl_tasks, run_dir, labels_path)

    report = build_report(run_dir, code_summary, model_summary, hitl_summary)

    print("Lesson-19 Eval Harness complete.")
    if code_summary:
        print(f"Hard tests (code): {code_summary['total']} total, {code_summary['passed']} passed.")
    if model_summary:
        print(
            "LLM tests (model): "
            f"{model_summary['total']} total, pass@1 {model_summary['pass_at_1']}, pass@{model_summary['k']} {model_summary['pass_at_k']}."
        )
    if hitl_summary:
        print(f"HITL tests: {hitl_summary['total']} total. Export: {hitl_summary['export_path']}")
        if hitl_summary.get("imported"):
            print("HITL labels imported and scored.")
    print(f"Run artifacts: {run_dir}")
    print(f"Report: {run_dir / 'report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

