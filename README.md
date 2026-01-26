# Capstone – Insurance Claim Agents

A production-ready RAG + multi-agent system for insurance claim Q&A, demonstrating hierarchical indexing, agent-based routing, MCP (Model Context Protocol) integration, and comprehensive evaluation. Built as a capstone project with both original midterm evaluation and an additive Lesson 19 eval harness.

## What This Is

This project implements a multi-agent insurance claim Q&A system over a synthetic motor insurance claim. It demonstrates:

- **Multi-granularity indexing**: Hierarchical chunking (1024/512/128 tokens) with AutoMergingRetriever
- **Agent-based routing**: Heuristic router directing questions to specialized agents (summary vs. needle)
- **MCP integration**: Real Model Context Protocol server + client for date arithmetic (with legacy fallback)
- **Table-aware retrieval**: Structured markdown table indexing with row-level metadata
- **Dual evaluation paths**:
  - Original midterm judge (`src/eval/judge.py`) with LLM-as-judge metrics
  - Add-on Lesson 19 eval harness (`eval_harness/`) with code/model/HITL suites
- **Optional Streamlit UI**: Grader-friendly dashboard for demos and evaluations

**No-drift guarantee**: The eval harness and Streamlit UI are purely additive; they do not modify any existing app logic, agents, indexing, or MCP code.

---

## Quickstart (Windows PowerShell)

### 1. Clone and Setup

```powershell
git clone <repository-url>
cd capstone_insurance_claim_agents
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

**Optional UI dependencies:**
```powershell
pip install -r requirements-ui.txt
```

### 3. Configure API Key

Create `.env` in the project root:
```
OPENAI_API_KEY=sk-...
```

**Security note**: Never commit `.env` or show API keys in screenshots/recordings.

---

## Demo Options

### CLI Interactive Mode

**Legacy mode (default):**
```powershell
python .\src\main.py
```

**Strict real MCP mode (grader-proof):**
```powershell
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="0"
python .\src\main.py
```

**Comfort mode (real MCP with fallback):**
```powershell
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="1"
python .\src\main.py
```

**Debug mode (show source node metadata):**
```powershell
$env:DEBUG_SOURCES="1"
python .\src\main.py
```

### Streamlit UI (Optional)

```powershell
streamlit run streamlit_app.py
```

The UI provides:
- **Run Quick Demo Questions**: Copy recommended questions for screen recording
- **Single Question (UI)**: Ask a single question via subprocess wrapper
- **Run Evaluation (Judge)**: Execute evaluation and view results
- **Artifacts & Submission Map**: Checklist of deliverables

**Note**: The UI is a wrapper only; CLI remains the official path for production use.

---

## Evaluation

### Original Midterm Judge

**Run evaluation:**
```powershell
python .\src\eval\judge.py
```

**With strict MCP mode:**
```powershell
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="0"
python .\src\eval\judge.py
```

**Output:**
- Terminal summary table with metrics (screenshot-friendly)
- Report file: `src/eval/eval_report.json`

**Metrics:**
- `llm_correctness`: LLM-as-judge score (1-5) for factual correctness
- `exact_match`: Boolean (0/1) indicating exact match after normalization
- `context_hit`: Boolean (0/1) indicating whether retrieved context contains ground-truth substring
- `relevance_score`: LLM-as-judge score (1-5) for context relevance
- `recall_score`: LLM-as-judge score (1-5) for information recall

**Windows note**: Evaluation output is ASCII-safe. If you encounter encoding issues, set `PYTHONIOENCODING=utf-8`.

### Lesson 19 Eval Harness (Additive)

The eval harness provides comprehensive evaluation suites without modifying existing app code.

**Run code suite (20 tasks, k=1 by default):**
```powershell
python -m eval_harness.run --suite code --k 1
```

**Run model suite (15 tasks, k=3 by default):**
```powershell
python -m eval_harness.run --suite model --k 3
```

**Run HITL suite (10 tasks, k=1 by default):**
```powershell
python -m eval_harness.run --suite hitl --k 1
```

**Run all suites:**
```powershell
python -m eval_harness.run --suite all
```

**Limit tasks (for testing):**
```powershell
python -m eval_harness.run --suite code --limit 3
```

**HITL Labeling Workflows:**

**Option A: Integrated UI labeling** (if implemented in Streamlit UI)

**Option B: Export → Label → Import:**
```powershell
# Export HITL tasks for human labeling
python -m eval_harness.hitl.export_hitl --output hitl_export.csv

# After labeling, import labels
python -m eval_harness.hitl.import_hitl --file labeled.csv --run <run_id>
```

**Artifact storage:**
- All generated artifacts: `eval_harness/runs/<run_id>/`
- Individual trial results: `eval_harness/runs/<run_id>/trials/<task_id>__t<trial>.json`
- Aggregated report: `eval_harness/runs/<run_id>/report.json`

**Metrics:**
- `pass@1`: Fraction of tasks that pass on the first trial
- `pass@k`: Fraction of tasks that pass on at least one trial
- `pass^k`: Fraction of tasks that pass on ALL trials

**Missing API keys:**
If `OPENAI_API_KEY` is not set when running the model suite:
- The harness prints: "⚠️ OPENAI_API_KEY not set - skipping model judge"
- Model judge grades are marked with `uncertainty_flag: true`
- The suite continues gracefully (no stacktrace)
- Code and HITL suites run normally without API keys

---

## Repository Structure

```
capstone_insurance_claim_agents/
├── data/
│   ├── claim_timeline.md      # Synthetic claim timeline (single markdown document)
│   └── claim_timeline.pdf      # Generated PDF (≥10 pages)
├── src/
│   ├── indexing.py             # Index building + query engine setup
│   ├── main.py                 # CLI for interactive Q&A via agents
│   ├── agents/
│   │   ├── manager.py          # Router agent
│   │   ├── summarizer_agent.py # High-level / timeline agent
│   │   └── needle_agent.py    # Fine-grained factual agent (+ date tool integration)
│   ├── mcp_integration/
│   │   ├── client.py           # Date-difference tool (routes to MCP or legacy)
│   │   ├── date_server.py      # Real MCP server (FastMCP over STDIO)
│   │   └── date_client.py      # MCP client wrapper
│   └── eval/
│       ├── test_cases.json     # Evaluation questions + ground-truth answers
│       ├── judge.py            # LLM-as-a-judge evaluation script
│       └── eval_report.json    # Generated evaluation report
├── eval_harness/               # Lesson 19 eval harness (additive)
│   ├── run.py                  # CLI entry point
│   ├── runner.py               # Adapter that calls existing ManagerAgent.answer()
│   ├── types.py                # Data models (TaskSpec, TrialResult, etc.)
│   ├── report.py               # Metrics aggregation and reporting
│   ├── graders/
│   │   ├── code_graders.py    # Regex/substring/forbidden-pattern/context-hit graders
│   │   └── model_judge.py     # LLM-as-judge with structured JSON output
│   ├── hitl/
│   │   ├── export_hitl.py     # Export CSV/JSONL for human labeling
│   │   ├── import_hitl.py     # Import labels and compute agreement
│   │   └── labels/             # Stored labels (git-tracked if non-sensitive)
│   ├── tasks/
│   │   ├── code.jsonl          # 20 code-based tasks
│   │   ├── model.jsonl         # 15 model-based tasks
│   │   └── hitl.jsonl          # 10 HITL tasks
│   ├── schemas/
│   │   └── judge_output.schema.json  # JSON schema for model-judge output
│   └── runs/                   # Generated artifacts (gitignored)
├── streamlit_app.py            # Optional Streamlit grader dashboard
├── ui/
│   └── README.md               # UI-specific notes
├── requirements.txt            # Core dependencies
├── requirements-ui.txt         # Optional UI dependencies
└── README.md                   # This file
```

---

## Architecture Highlights

### Indexing Design

- **Hierarchical chunking**: 128-token leaf nodes for precise retrieval, 512-token mid-level for merging, 1024-token top-level for summaries
- **AutoMergingRetriever**: Dynamically merges related small chunks into parents when answering
- **SummaryIndex**: Separate index for high-level timeline questions using `tree_summarize` response mode
- **Table-aware indexing**: Markdown tables parsed into row-level nodes with metadata (`node_type: "table_row"`, `table: "Event Ledger"`, `row_index: N`)

### Agent Design

- **ManagerAgent (router)**: Simple keyword heuristic routing (e.g., "overview"/"summary" → SummarizationAgent, else → NeedleAgent)
- **SummarizationAgent**: Uses SummaryIndex for high-level overviews and timeline questions
- **NeedleAgent**: Uses AutoMergingRetriever for precise factual questions; integrates date-difference tool

### MCP Integration

- **Real MCP server**: `src/mcp_integration/date_server.py` implements FastMCP server over STDIO
- **MCP client**: `src/mcp_integration/date_client.py` wraps MCP client session with async context
- **Integration layer**: `src/mcp_integration/client.py` routes between MCP and legacy modes
- **Strict verification mode**: `USE_REAL_MCP=1` and `ALLOW_MCP_FALLBACK=0` ensures real MCP is used (provable via `[REAL MCP]` log lines)
- **Comfort mode**: `USE_REAL_MCP=1` and `ALLOW_MCP_FALLBACK=1` allows fallback to legacy on failure

### Evaluation Design

**Original midterm judge:**
- 8 test cases covering summary, needle, needle+tool, and table questions
- LLM-as-judge with three metrics: correctness, relevance, recall
- Exact match and context hit checks

**Lesson 19 eval harness:**
- **20 code-based tasks**: Fast, objective checks (regex, substring, forbidden patterns, context hit, source type)
- **15 model-based tasks**: LLM-as-judge with structured JSON output and schema validation
- **10 HITL tasks**: Export/import workflow for human labeling with agreement metrics
- **Multi-trial support**: `pass@1`, `pass@k`, `pass^k` metrics
- **Proof-carrying artifacts**: Each trial writes JSON with inputs, outputs, sources, and grades

---

## Safety & Operations Notes

- **API keys**: Never commit `.env` or show keys in screenshots/recordings
- **Rate limits**: Be aware of OpenAI API rate limits when running evaluations
- **MCP toggles**: Use `USE_REAL_MCP` and `ALLOW_MCP_FALLBACK` as demo switches
- **Windows encoding**: Evaluation output is ASCII-safe; set `PYTHONIOENCODING=utf-8` if needed
- **Virtual environment**: Always use `.venv` to avoid dependency conflicts

---

## Capstone Release Checklist

### For Recruiters / Graders

1. **Clone and setup** (see Quickstart above)
2. **Run interactive demo:**
   ```powershell
   python .\src\main.py
   ```
   Try these questions:
   - "Give me a brief overview of the claim, including the main events and dates."
   - "Did the insured refuse ambulance transport at the scene?"
   - "What was the amount of the vehicle repair estimate?" (table question)
3. **Run evaluation judge:**
   ```powershell
   python .\src\eval\judge.py
   ```
   Screenshot the terminal output showing metrics table.
4. **Verify MCP integration:**
   ```powershell
   $env:USE_REAL_MCP="1"
   $env:ALLOW_MCP_FALLBACK="0"
   python .\src\main.py
   ```
   Ask: "How many days passed between the accident and the final settlement date?"
   Verify `[REAL MCP]` appears in logs.
5. **Run eval harness (optional):**
   ```powershell
   python -m eval_harness.run --suite code --limit 3
   ```
6. **Check artifacts:**
   - `data/claim_timeline.md` and `data/claim_timeline.pdf` exist
   - `src/eval/eval_report.json` exists (after running judge)
   - `eval_harness/runs/` contains trial artifacts (after running harness)

### Screenshot Targets

- **Evaluation metrics table**: Terminal output from `judge.py` or Streamlit UI "Evaluation Results Summary" panel
- **MCP proof**: Terminal log showing `[REAL MCP]` line
- **Table bonus evidence**: Terminal output with `DEBUG_SOURCES=1` showing `node_type: "table_row"` in retrieved sources
- **Eval harness summary**: Terminal output from `eval_harness.run` showing `pass@1`, `pass@k`, `pass^k` metrics

---

## Recruiter Demo Script (60–90 seconds)

1. **Show the system answering a question:**
   ```powershell
   python .\src\main.py
   ```
   Ask: "Give me a brief overview of the claim, including the main events and dates."
   *(Highlights: multi-agent routing, hierarchical retrieval, summary generation)*

2. **Show evaluation metrics:**
   ```powershell
   python .\src\eval\judge.py
   ```
   *(Highlights: LLM-as-judge evaluation, multiple metrics, reproducible results)*

3. **Show MCP integration (if time permits):**
   ```powershell
   $env:USE_REAL_MCP="1"
   $env:ALLOW_MCP_FALLBACK="0"
   python .\src\main.py
   ```
   Ask: "How many days passed between the accident and the final settlement date?"
   *(Highlights: real MCP server/client, external tool integration, provable via logs)*

**Key talking points:**
- Production-ready RAG system with hierarchical indexing
- Multi-agent architecture with intelligent routing
- Real MCP integration (not just a mock)
- Comprehensive evaluation (original judge + Lesson 19 harness)
- Table-aware retrieval for structured data
- No-drift guarantee: eval harness and UI are purely additive

---

## Limitations and Future Work

**Current limitations:**
- Routing uses simple keyword heuristics (not LLM-based)
- Date tool uses canonical dates from synthetic data (not dynamically parsed)
- Single claim indexed (multi-claim scaling not addressed)
- Judge uses single model/prompt (no ablation or inter-judge agreement)

**Potential extensions:**
- Replace heuristic routing with LLM classifier or learned router
- Generalize date tool to extract dates from retrieved context
- Extend dataset to multiple claims with claim ID filtering
- Add web/notebook front-end for experimentation
- Implement LLM-based routing for more sophisticated agent selection

---

## Verification

To verify the system works and confirm no drift:

```powershell
# Compile check
python -m compileall src eval_harness

# Run demo (3 tasks)
python -m eval_harness.run --suite code --limit 3

# Check that no existing files were modified
git status
```

---

## License

This project is a capstone demonstration. All code is provided as-is for educational and portfolio purposes.
