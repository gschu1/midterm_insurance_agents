# Lesson-19 Eval Harness (Add-on)

This package adds a structured evaluation harness with three suites:

- **Hard tests (code)**: deterministic checks for needle + table questions only
- **LLM-based tests (model)**: rubric-based judging (includes summary)
- **HITL tests (hitl)**: export/import for human grading (includes summary)

## Run the harness

From repo root:

```powershell
python -m eval_harness.run --suite code --k 1
python -m eval_harness.run --suite model --k 1
python -m eval_harness.run --suite hitl --k 1
python -m eval_harness.run --suite all --k 1
```

## Artifacts

Runs are stored under:

```
eval_harness/runs/<run_id>/
```

Each run folder includes:

- `config.json`
- `results_code.json`
- `results_model.json`
- `results_hitl.json`
- `report.json`
- `transcripts/`

## HITL workflow

1. Export a human grading packet:
   ```powershell
   python -m eval_harness.run --suite hitl --k 1
   ```
   This creates `hitl_export.jsonl` in the run folder.

2. Label the file and import:
   ```powershell
   python -m eval_harness.run --suite hitl --k 1 --hitl-labels path\to\labeled.jsonl
   ```
   This produces `hitl_summary.json` and updates the report.

