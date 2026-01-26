"""
Report generation: aggregates metrics and prints screenshot-friendly summary.
"""
import json
from pathlib import Path
from typing import Any, Dict, List

from .types import TrialResult


def load_trial_results(run_dir: Path) -> List[Dict[str, Any]]:
    """Load all trial JSON files from a run directory."""
    trials_dir = run_dir / "trials"
    if not trials_dir.exists():
        return []
    
    results = []
    for trial_file in sorted(trials_dir.glob("*.json")):
        try:
            with open(trial_file, "r", encoding="utf-8") as f:
                results.append(json.load(f))
        except Exception as e:
            print(f"Warning: Failed to load {trial_file}: {e}")
    
    return results


def compute_metrics(trial_results: List[Dict[str, Any]], suite: str) -> Dict[str, Any]:
    """
    Compute pass@1, pass@k, and pass^k metrics.
    
    Args:
        trial_results: List of trial dicts (loaded from JSON)
        suite: "code", "model", or "hitl"
    
    Returns:
        Dict with metrics
    """
    # Group by task_id
    by_task: Dict[str, List[Dict[str, Any]]] = {}
    for trial in trial_results:
        task_id = trial.get("task_id")
        if task_id:
            if task_id not in by_task:
                by_task[task_id] = []
            by_task[task_id].append(trial)
    
    # Compute per-task pass rates
    task_passes = {}
    for task_id, trials in by_task.items():
        # Sort by trial_index
        trials_sorted = sorted(trials, key=lambda t: t.get("trial_index", 0))
        
        # Determine if task passed
        if suite == "code":
            # Code: check code_grade.overall_passed
            passes = [
                t.get("code_grade", {}).get("overall_passed", False)
                for t in trials_sorted
            ]
        elif suite == "model":
            # Model: check model_judge_grade.passed and not uncertainty_flag
            passes = [
                t.get("model_judge_grade", {}).get("passed", False) and
                not t.get("model_judge_grade", {}).get("uncertainty_flag", False)
                for t in trials_sorted
            ]
        elif suite == "hitl":
            # HITL: check hitl_label.passed
            passes = [
                t.get("hitl_label", {}).get("passed", False)
                for t in trials_sorted
            ]
        else:
            passes = [False] * len(trials_sorted)
        
        task_passes[task_id] = passes
    
    # Compute metrics
    total_tasks = len(by_task)
    if total_tasks == 0:
        return {
            "pass_at_1": 0.0,
            "pass_at_k": 0.0,
            "pass_all_k": 0.0,
            "total_tasks": 0,
            "total_trials": 0
        }
    
    # pass@1: fraction of tasks that pass on first trial
    pass_at_1 = sum(1 for passes in task_passes.values() if len(passes) > 0 and passes[0]) / total_tasks
    
    # pass@k: fraction of tasks that pass on at least one trial
    pass_at_k = sum(1 for passes in task_passes.values() if any(passes)) / total_tasks
    
    # pass^k: fraction of tasks that pass on ALL trials
    pass_all_k = sum(1 for passes in task_passes.values() if all(passes) and len(passes) > 0) / total_tasks
    
    total_trials = sum(len(trials) for trials in by_task.values())
    
    return {
        "pass_at_1": pass_at_1,
        "pass_at_k": pass_at_k,
        "pass_all_k": pass_all_k,
        "total_tasks": total_tasks,
        "total_trials": total_trials,
        "k": max((len(trials) for trials in by_task.values()), default=1)
    }


def print_summary_report(run_dir: Path, suite: str) -> None:
    """Print a screenshot-friendly summary table."""
    trial_results = load_trial_results(run_dir)
    metrics = compute_metrics(trial_results, suite)
    
    print("\n" + "=" * 80)
    print(f"Evaluation Summary - {suite.upper()} Suite")
    print("=" * 80)
    print(f"\nRun directory: {run_dir}")
    print(f"\nMetrics:")
    print(f"{'Metric':<20} {'Value':<15}")
    print("-" * 35)
    print(f"{'pass@1':<20} {metrics['pass_at_1']:<15.3f}")
    print(f"{'pass@k':<20} {metrics['pass_at_k']:<15.3f}")
    print(f"{'pass^k':<20} {metrics['pass_all_k']:<15.3f}")
    print(f"{'total_tasks':<20} {metrics['total_tasks']:<15}")
    print(f"{'total_trials':<20} {metrics['total_trials']:<15}")
    print(f"{'k (trials per task)':<20} {metrics['k']:<15}")
    print("\n" + "=" * 80)


def generate_detailed_report(run_dir: Path, suite: str) -> Dict[str, Any]:
    """Generate a detailed JSON report."""
    trial_results = load_trial_results(run_dir)
    metrics = compute_metrics(trial_results, suite)
    
    return {
        "suite": suite,
        "run_dir": str(run_dir),
        "metrics": metrics,
        "trials": trial_results
    }

