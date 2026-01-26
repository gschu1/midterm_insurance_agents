"""
Import human-labeled HITL tasks and compute agreement metrics.
"""
import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def import_hitl_labels(csv_file: str, run_id: str) -> Path:
    """
    Import labeled CSV and store labels, compute agreement.
    
    Args:
        csv_file: Path to labeled CSV
        run_id: Run ID to associate labels with
    
    Returns:
        Path to saved labels JSON
    """
    csv_path = Path(csv_file)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Load labels from CSV
    labels = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            task_id = row["task_id"]
            human_score = row.get("human_score", "").strip()
            human_notes = row.get("human_notes", "").strip()
            
            # Parse score (could be numeric or pass/fail)
            passed = False
            if human_score:
                try:
                    score_val = float(human_score)
                    passed = score_val >= 4.0  # Threshold for pass
                except ValueError:
                    # Try pass/fail strings
                    if human_score.lower() in ["pass", "true", "yes", "1"]:
                        passed = True
            
            label = {
                "task_id": task_id,
                "human_score": human_score,
                "human_notes": human_notes,
                "passed": passed,
                "run_id": run_id
            }
            labels.append(label)
    
    # Load corresponding trial results to compare with model judge
    run_dir = Path(__file__).parent.parent / "runs" / run_id
    trials_dir = run_dir / "trials"
    
    agreements = []
    for label in labels:
        task_id = label["task_id"]
        
        # Find trial result
        trial_file = trials_dir / f"{task_id}__t0.json"
        if trial_file.exists():
            with open(trial_file, "r", encoding="utf-8") as f:
                trial = json.load(f)
            
            # Compare with model judge if available
            model_judge = trial.get("model_judge_grade")
            if model_judge:
                model_passed = model_judge.get("passed", False)
                human_passed = label["passed"]
                agreement = model_passed == human_passed
                
                agreements.append({
                    "task_id": task_id,
                    "human_passed": human_passed,
                    "model_passed": model_passed,
                    "agreement": agreement
                })
    
    # Compute agreement rate
    agreement_rate = 0.0
    if agreements:
        agreement_rate = sum(1 for a in agreements if a["agreement"]) / len(agreements)
    
    # Save labels
    labels_dir = Path(__file__).parent / "labels"
    labels_dir.mkdir(exist_ok=True)
    labels_file = labels_dir / f"{run_id}.json"
    
    output = {
        "run_id": run_id,
        "labels": labels,
        "agreements": agreements,
        "agreement_rate": agreement_rate,
        "total_labels": len(labels),
        "total_agreements": len(agreements)
    }
    
    with open(labels_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Update trial results with HITL labels
    for label in labels:
        task_id = label["task_id"]
        trial_file = trials_dir / f"{task_id}__t0.json"
        if trial_file.exists():
            with open(trial_file, "r", encoding="utf-8") as f:
                trial = json.load(f)
            
            trial["hitl_label"] = {
                "passed": label["passed"],
                "human_score": label["human_score"],
                "human_notes": label["human_notes"]
            }
            
            with open(trial_file, "w", encoding="utf-8") as f:
                json.dump(trial, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Labels imported and saved to: {labels_file}")
    print(f"   Total labels: {len(labels)}")
    print(f"   Agreement rate (vs model judge): {agreement_rate:.3f} ({len(agreements)} comparisons)")
    
    return labels_file


def main():
    parser = argparse.ArgumentParser(description="Import human-labeled HITL tasks")
    parser.add_argument("--file", type=str, required=True,
                       help="Path to labeled CSV file")
    parser.add_argument("--run", type=str, required=True,
                       help="Run ID to associate labels with")
    
    args = parser.parse_args()
    import_hitl_labels(args.file, args.run)


if __name__ == "__main__":
    main()

