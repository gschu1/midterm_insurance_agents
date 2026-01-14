"""
CLI entry point for running evaluations.

Usage:
    python -m eval_harness.run --suite code --k 1
    python -m eval_harness.run --suite model --k 3
    python -m eval_harness.run --suite hitl --k 1
"""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .graders.code_graders import grade_code_task
from .graders.model_judge import model_judge_grader
from .report import generate_detailed_report, print_summary_report
from .runner import run_trial
from .types import TaskSpec, TrialResult


def load_tasks(suite: str):
    """Load tasks from JSONL file."""
    from pathlib import Path
    import json
    
    tasks_file = Path(__file__).parent / "tasks" / f"{suite}.jsonl"
    
    if not tasks_file.exists():
        raise FileNotFoundError(f"Tasks file not found: {tasks_file}")
    
    tasks = []
    with open(tasks_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    
    return tasks


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"




def run_evaluation_suite(suite: str, k: int = 1, limit: int = None) -> Path:
    """
    Run an evaluation suite.
    
    Args:
        suite: "code", "model", or "hitl"
        k: Number of trials per task
        limit: Limit number of tasks (for testing)
    
    Returns:
        Path to run directory
    """
    # Create run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = f"{suite}_{timestamp}"
    run_dir = Path(__file__).parent / "runs" / run_id
    trials_dir = run_dir / "trials"
    trials_dir.mkdir(parents=True, exist_ok=True)
    
    # Load tasks
    tasks = load_tasks(suite)
    if limit:
        tasks = tasks[:limit]
    
    print(f"\nRunning {suite} suite with {len(tasks)} tasks, k={k} trials per task")
    print(f"Run directory: {run_dir}\n")
    
    git_commit = get_git_commit()
    
    # Run trials
    for task_spec in tasks:
        task_id = task_spec["task_id"]
        question = task_spec["question"]
        
        print(f"Task {task_id}: {question[:60]}...")
        
        for trial_idx in range(k):
            # Run trial
            result = run_trial(question)
            
            # Grade based on suite type
            code_grade = None
            model_judge_grade = None
            
            if suite == "code":
                code_grade = grade_code_task(
                    task_spec,
                    result["answer"],
                    result["sources"],
                    task_spec.get("ground_truth")
                )
            elif suite == "model":
                # Check for API key before running
                import os
                from dotenv import load_dotenv
                load_dotenv()
                if not os.getenv("OPENAI_API_KEY"):
                    print("  ⚠️  OPENAI_API_KEY not set - skipping model judge")
                    model_judge_grade = {
                        "passed": False,
                        "uncertainty_flag": True,
                        "evidence": "API key not available",
                        "failure_reason": "Missing OPENAI_API_KEY"
                    }
                else:
                    model_judge_grade_result = model_judge_grader(
                        question,
                        result["answer"],
                        result["sources"],
                        task_spec.get("ground_truth"),
                        task_spec.get("rubric")
                    )
                    model_judge_grade = {
                        "passed": model_judge_grade_result.passed,
                        "score": model_judge_grade_result.score,
                        "evidence": model_judge_grade_result.evidence,
                        "uncertainty_flag": model_judge_grade_result.uncertainty_flag,
                        "failure_reason": model_judge_grade_result.failure_reason,
                        "details": model_judge_grade_result.details
                    }
            
            # Create trial result
            trial_result = {
                "task_id": task_id,
                "suite": suite,
                "trial_index": trial_idx,
                "timestamp": datetime.now().isoformat(),
                "git_commit": git_commit,
                "question": question,
                "input_payload": {},
                "answer": result["answer"],
                "chosen_agent": result["chosen_agent"],
                "sources": result["sources"],
                "outcome_checks": {},
                "code_grade": code_grade,
                "model_judge_grade": model_judge_grade,
                "hitl_label": None,
                "model_metadata": {}
            }
            
            # Save trial JSON
            trial_file = trials_dir / f"{task_id}__t{trial_idx}.json"
            with open(trial_file, "w", encoding="utf-8") as f:
                json.dump(trial_result, f, indent=2, ensure_ascii=False)
            
            # Print quick status
            if suite == "code" and code_grade:
                status = "PASS" if code_grade.get("overall_passed") else "FAIL"
                print(f"  Trial {trial_idx}: {status}")
            elif suite == "model" and model_judge_grade:
                passed = model_judge_grade.get("passed", False)
                uncertain = model_judge_grade.get("uncertainty_flag", False)
                status = "PASS" if passed else ("UNCERTAIN" if uncertain else "FAIL")
                print(f"  Trial {trial_idx}: {status} (score: {model_judge_grade.get('score', 'N/A')})")
    
    # Generate and print report
    print_summary_report(run_dir, suite)
    
    # Save detailed report
    detailed_report = generate_detailed_report(run_dir, suite)
    report_file = run_dir / "report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(detailed_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n[OK] Detailed report saved to: {report_file}")
    
    return run_dir


def main():
    parser = argparse.ArgumentParser(description="Run evaluation harness")
    parser.add_argument("--suite", choices=["code", "model", "hitl"], required=True,
                       help="Evaluation suite to run")
    parser.add_argument("--k", type=int, default=1,
                       help="Number of trials per task (default: 1 for code/hitl, 3 for model)")
    parser.add_argument("--limit", type=int, default=None,
                       help="Limit number of tasks (for testing)")
    
    args = parser.parse_args()
    
    # Set default k for model suite
    if args.suite == "model" and args.k == 1:
        args.k = 3
    
    run_evaluation_suite(args.suite, args.k, args.limit)


if __name__ == "__main__":
    main()

