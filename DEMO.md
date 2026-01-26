## Demo (Windows PowerShell, clean clone → running UI)

This repo is presentation-ready when you follow this flow.

### Preconditions

- You have Python installed on Windows.
- You have an OpenAI key available as `OPENAI_API_KEY` (used by the judge + many eval harness tasks).
- **Canonical venv name is `.venv/`**. If you have an older `venv/` folder from a previous clone, delete it to avoid interpreter confusion.

### 1) Clone and set up (one command)

```powershell
git clone <repository-url>
cd capstone_insurance_claim_agents
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task setup
```

### 2) Sanity check the environment (doctor)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task doctor
```

Expected: prints repo root + `.venv` path and confirms these imports succeed:
- `llama_index`
- `eval_harness`
- `streamlit`

### 3) Start the Streamlit demo

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task streamlit
```

Then open: `http://localhost:8501`

In the UI, you should see tabs including:
- **Single Question (UI)**
- **Eval Harness (Lesson-19)** (code/model/HITL controls + HITL labeling UI)

### 4) Optional CLI demos (copy/paste)

Run the midterm judge:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task judge
```

Run eval harness code suite:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1 -Task eval_code
```

Expected: creates a run dir under `eval_harness/runs/code_*/` with `report.json` and `trials/`.

