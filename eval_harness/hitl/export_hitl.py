"""
Export HITL tasks for human labeling.
"""
import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import json
from pathlib import Path

from ..runner import run_trial


def load_tasks(suite: str):
    """Load tasks from JSONL file."""
    tasks_file = Path(__file__).parent.parent / "tasks" / f"{suite}.jsonl"
    
    if not tasks_file.exists():
        raise FileNotFoundError(f"Tasks file not found: {tasks_file}")
    
    tasks = []
    with open(tasks_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    
    return tasks


def export_hitl_csv(run_id: str = None, output_file: str = None) -> Path:
    """
    Export HITL tasks to CSV for human labeling.
    
    If run_id is provided, loads existing trial results.
    Otherwise, runs new trials.
    """
    # Load HITL tasks
    tasks = load_tasks("hitl")
    
    # Determine output file
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = Path(__file__).parent.parent / "runs" / f"hitl_export_{Path(__file__).parent.parent.name}.csv"
    
    # Get trial results
    trial_results = []
    
    if run_id:
        # Load from existing run
        run_dir = Path(__file__).parent.parent / "runs" / run_id
        trials_dir = run_dir / "trials"
        
        if not trials_dir.exists():
            raise FileNotFoundError(f"Run directory not found: {run_dir}")
        
        for trial_file in sorted(trials_dir.glob("*.json")):
            with open(trial_file, "r", encoding="utf-8") as f:
                trial_results.append(json.load(f))
    else:
        # Run new trials
        print("Running HITL tasks to generate export...")
        for task_spec in tasks:
            task_id = task_spec["task_id"]
            question = task_spec["question"]
            
            result = run_trial(question)
            
            trial_result = {
                "task_id": task_id,
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "chosen_agent": result["chosen_agent"]
            }
            trial_results.append(trial_result)
    
    # Build CSV rows
    rows = []
    for trial in trial_results:
        task_id = trial["task_id"]
        question = trial["question"]
        answer = trial["answer"]
        
        # Find corresponding task spec for rubric fields
        task_spec = next((t for t in tasks if t["task_id"] == task_id), {})
        rubric_fields = task_spec.get("rubric_fields", [])
        
        # Build sources path (store as JSON string for CSV)
        sources_path = f"trial_{task_id}_sources.json"
        
        # Build row
        row = {
            "task_id": task_id,
            "question": question,
            "system_answer": answer,
            "sources_path": sources_path,
            "trial_json_path": f"{task_id}__t0.json",
        }
        
        # Add rubric fields as columns
        for field in rubric_fields:
            row[f"rubric_{field}"] = ""
        
        # Add human label columns
        row["human_score"] = ""
        row["human_notes"] = ""
        
        rows.append(row)
        
        # Save sources separately
        sources_dir = output_path.parent / "hitl_sources"
        sources_dir.mkdir(exist_ok=True)
        sources_file = sources_dir / sources_path
        with open(sources_file, "w", encoding="utf-8") as f:
            json.dump(trial["sources"], f, indent=2, ensure_ascii=False)
    
    # Write CSV
    if rows:
        fieldnames = ["task_id", "question", "system_answer", "sources_path", "trial_json_path"]
        # Add rubric fields
        if rows:
            rubric_fields = tasks[0].get("rubric_fields", [])
            for field in rubric_fields:
                fieldnames.append(f"rubric_{field}")
        fieldnames.extend(["human_score", "human_notes"])
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    
    print(f"\n✅ HITL export written to: {output_path}")
    print(f"   {len(rows)} tasks exported")
    print(f"   Sources saved to: {output_path.parent / 'hitl_sources'}")
    
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export HITL tasks for human labeling")
    parser.add_argument("--run", type=str, default=None,
                       help="Run ID to load existing trials from (optional)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output CSV file path (default: auto-generated)")
    
    args = parser.parse_args()
    export_hitl_csv(args.run, args.output)


if __name__ == "__main__":
    main()

