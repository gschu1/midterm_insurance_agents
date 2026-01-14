import json
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import ValidationError, validate

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "hitl_labels.schema.json"


def _load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def export_hitl_pack(tasks: List[Dict[str, Any]], answers: Dict[str, Dict[str, Any]], run_dir: Path) -> Path:
    export_path = run_dir / "hitl_export.jsonl"
    with open(export_path, "w", encoding="utf-8") as f:
        for task in tasks:
            task_id = task["id"]
            answer_entry = answers.get(task_id, {})
            record = {
                "id": task_id,
                "type": task.get("type"),
                "question": task.get("question"),
                "rubric": task.get("rubric"),
                "answer": answer_entry.get("answer"),
                "label_schema": task.get("label_schema"),
                "score_1_to_5": None,
                "verdict": None,
                "comment": "",
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return export_path


def import_labels(labels_path: Path) -> List[Dict[str, Any]]:
    schema = _load_schema()
    records: List[Dict[str, Any]] = []
    with open(labels_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            validate(instance=record, schema=schema)
            records.append(record)
    return records


def score_labels(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"count": 0, "pass_rate": 0.0, "average_score": 0.0}

    total = len(records)
    pass_count = sum(1 for r in records if r.get("verdict") == "pass")
    avg_score = sum(r.get("score_1_to_5", 0) for r in records) / total
    return {
        "count": total,
        "pass_rate": pass_count / total,
        "average_score": avg_score,
    }

