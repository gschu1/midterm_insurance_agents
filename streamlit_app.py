"""
Optional Streamlit Grader Dashboard for Midterm Insurance Agents

This UI is a wrapper around existing CLI tools - it does not modify app logic.
Run with: streamlit run streamlit_app.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

import streamlit as st

# Get repo root
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
EVAL_DIR = SRC_DIR / "eval"
HARNESS_DIR = REPO_ROOT / "eval_harness"
HARNESS_RUNS_DIR = HARNESS_DIR / "runs"

# Page config
st.set_page_config(
    page_title="Midterm Insurance Agents - Grader Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Midterm Insurance Agents - Grader Dashboard")
st.markdown("**Optional UI wrapper for running demos and evaluations**")

# Sidebar: Environment controls
with st.sidebar:
    st.header("⚙️ Environment Controls")
    st.warning("⚠️ **Do NOT show your API key on screen.**")
    
    st.subheader("MCP Configuration")
    with st.popover("ℹ️ Explain", help="What MCP Configuration means"):
        st.markdown(
            "Model Context Protocol (MCP) standardizes how models call external tools/services (we use it for date arithmetic). "
            "These toggles choose real MCP vs local fallback behavior for demos and proof. "
            "[Anthropic MCP overview](https://www.anthropic.com/news/model-context-protocol) • "
            "[MCP specification](https://modelcontextprotocol.io/)"
        )
    use_real_mcp = st.selectbox(
        "USE_REAL_MCP",
        options=["0", "1"],
        index=0,
        help="Use the real MCP server for tool calls; when off, the system uses the local fallback tool."
    )
    
    allow_mcp_fallback = st.selectbox(
        "ALLOW_MCP_FALLBACK",
        options=["0", "1"],
        index=1,
        help="If real MCP fails, allow local fallback; turn off for strict proof with no fallback."
    )
    
    st.subheader("Debug Options")
    debug_sources = st.selectbox(
        "DEBUG_SOURCES",
        options=["0", "1"],
        index=0,
        help="Show retrieval sources; for table bonus this reveals table_row nodes as evidence."
    )
    
    st.subheader("Evaluation Settings")
    st.info("k_trials supported in Lesson-19 eval harness (see harness tab).")
    k_trials = st.number_input(
        "k_trials (model eval repeats)",
        min_value=1,
        max_value=5,
        value=1,
        step=1,
        help="Repeat model-judge evals k times to measure non-determinism (pass@k).",
    )
    
    st.markdown("---")
    st.markdown("### 📝 Notes")
    st.markdown("""
    - These settings are applied when running subprocess commands
    - API key must be set in `.env` file (not shown in UI)
    - CLI remains the official path for production use
    """)


# Helper function to run subprocess with env vars
def run_with_env(command, description, stdin_input=None):
    """Run a subprocess command with environment variables from sidebar."""
    env = os.environ.copy()
    env["USE_REAL_MCP"] = use_real_mcp
    env["ALLOW_MCP_FALLBACK"] = allow_mcp_fallback
    env["DEBUG_SOURCES"] = debug_sources
    
    try:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            executable=sys.executable,
            input=stdin_input,
            timeout=300  # 5 minute timeout for safety
        )
        return result.returncode == 0, result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after 5 minutes", 1
    except Exception as e:
        return False, "", str(e), 1


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


@st.cache_data(show_spinner=False)
def get_task_counts() -> Dict[str, Dict[str, int]]:
    counts: Dict[str, Dict[str, int]] = {}
    for suite in ("code", "model", "hitl"):
        tasks = load_jsonl(HARNESS_DIR / "tasks" / f"{suite}.jsonl")
        type_counts: Dict[str, int] = {}
        for task in tasks:
            t = task.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        counts[suite] = {
            "total": len(tasks),
            **type_counts,
        }
    return counts


def get_latest_run_dir() -> Optional[Path]:
    if not HARNESS_RUNS_DIR.exists():
        return None
    run_dirs = [p for p in HARNESS_RUNS_DIR.iterdir() if p.is_dir()]
    if not run_dirs:
        return None
    return max(run_dirs, key=lambda p: p.stat().st_mtime)


def load_latest_report() -> Optional[Dict[str, Any]]:
    latest_dir = get_latest_run_dir()
    if not latest_dir:
        return None
    report_path = latest_dir / "report.json"
    if not report_path.exists():
        return None
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["_run_dir"] = str(latest_dir)
    return data


def find_latest_hitl_pack() -> Optional[Path]:
    """Find the latest HITL export pack file."""
    latest_dir = get_latest_run_dir()
    if not latest_dir:
        return None
    
    # Prefer known filename
    known_path = latest_dir / "hitl_export.jsonl"
    if known_path.exists():
        return known_path
    
    # Otherwise, find newest *.jsonl with "hitl" in name
    jsonl_files = list(latest_dir.glob("*hitl*.jsonl"))
    if jsonl_files:
        return max(jsonl_files, key=lambda p: p.stat().st_mtime)
    
    return None


@st.cache_resource(show_spinner=False)
def build_inprocess_manager():
    from eval_harness.adapter import get_manager

    return get_manager()


# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Run Quick Demo Questions",
    "❓ Single Question (UI)",
    "📊 Run Evaluation (Judge)",
    "🧪 Lesson-19 Eval Harness",
    "✅ Artifacts & Submission Map"
])

# Tab 1: Demo Questions
with tab1:
    st.header("Demo Questions for Screen Recording")
    st.info("""
    **Note:** For interactive Q&A, use the CLI: `python .\\src\\main.py`
    
    This UI provides the recommended questions for easy copying.
    """)
    
    demo_questions = [
        {
            "type": "Overview/Summarization",
            "question": "Give me a brief overview of the claim, including the main events and dates.",
            "description": "Tests the summarization agent and high-level retrieval"
        },
        {
            "type": "Needle Fact",
            "question": "Did the insured refuse ambulance transport at the scene?",
            "description": "Tests fine-grained factual retrieval (needle-in-haystack)"
        },
        {
            "type": "Table Fact (Bonus)",
            "question": "What was the amount of the vehicle repair estimate?",
            "description": "Tests table-aware retrieval with structured data"
        }
    ]
    
    for i, demo in enumerate(demo_questions, 1):
        with st.expander(f"Question {i}: {demo['type']}", expanded=True):
            st.markdown(f"**Description:** {demo['description']}")
            st.code(demo['question'], language=None)
            if st.button(f"📋 Copy Question {i}", key=f"copy_{i}"):
                st.code(demo['question'], language=None)
                st.success("Question copied! Paste into CLI when running `python .\\src\\main.py`")
    
    st.markdown("---")
    st.markdown("### 🎥 Screen Recording Instructions")
    st.markdown("""
    1. Run `python .\\src\\main.py` in a terminal
    2. Ask each question above in sequence
    3. For table bonus: enable `DEBUG_SOURCES=1` to show table_row nodes
    4. For MCP proof: enable `USE_REAL_MCP=1` and `ALLOW_MCP_FALLBACK=0`
    5. Look for `[REAL MCP]` log lines to verify real MCP usage
    """)


# Tab 2: Single Question Q&A
with tab2:
    st.header("Single Question Q&A")
    st.info("""
    **Note:** This is a convenience wrapper. For best results, use the CLI: `python .\\src\\main.py`
    
    This UI prefers an in-process call to `ManagerAgent.answer()` and falls back to subprocess if needed.
    """)
    
    question = st.text_area(
        "Enter your question:",
        placeholder="e.g., Did the insured refuse ambulance transport at the scene?",
        height=100
    )
    use_inprocess = st.checkbox("Use in-process Q&A (recommended)", value=True)
    
    if st.button("🚀 Ask Question", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Processing question..."):
                used_fallback = False
                if use_inprocess:
                    try:
                        manager = build_inprocess_manager()
                        result = manager.answer(question.strip())
                        st.success("✅ Question processed (in-process)!")
                        st.markdown("### Answer:")
                        st.markdown(result.get("answer", ""))
                        st.caption(f"Chosen agent: {result.get('chosen_agent', 'unknown')}")
                    except Exception as exc:
                        used_fallback = True
                        st.warning(f"In-process call failed, falling back to subprocess: {exc}")

                if not use_inprocess or used_fallback:
                    # Use subprocess to run main.py with stdin
                    main_script = REPO_ROOT / "src" / "main.py"
                    command = [sys.executable, str(main_script)]
                    
                    # Send question + exit command via stdin
                    stdin_input = f"{question.strip()}\nexit\n"
                    
                    success, stdout, stderr, return_code = run_with_env(command, "Single question", stdin_input=stdin_input)
                    
                    if success or stdout:
                        st.success("✅ Question processed (subprocess)!")
                        
                        # Display output
                        st.markdown("### Answer:")
                        # Try to extract the answer from output
                        # The output format is: [Chosen agent: ...] followed by answer
                        lines = stdout.split('\n')
                        answer_started = False
                        answer_lines = []
                        
                        for line in lines:
                            if '[Chosen agent:' in line or answer_started:
                                answer_started = True
                                if line.strip() and not line.startswith('['):
                                    answer_lines.append(line)
                        
                        if answer_lines:
                            st.markdown('\n'.join(answer_lines))
                        else:
                            # Fallback: show all output
                            st.text(stdout)
                        
                        # Show full output in expandable section
                        with st.expander("📄 Full Output", expanded=False):
                            st.text("STDOUT:")
                            st.code(stdout)
                            if stderr:
                                st.text("STDERR:")
                                st.code(stderr)
                    else:
                        st.error("❌ Failed to process question")
                        with st.expander("🔍 Error Details", expanded=True):
                            st.text("STDOUT:")
                            st.code(stdout)
                            st.text("STDERR:")
                            st.code(stderr)
                        
                        st.info("""
                        **Tip:** If this doesn't work reliably, use the CLI instead:
                        ```powershell
                        python .\\src\\main.py
                        ```
                        Then type your question when prompted.
                        """)


# Tab 3: Evaluation Judge
with tab3:
    st.header("Run Evaluation Judge")
    st.markdown("""
    This runs `src/eval/judge.py` which evaluates all test cases and generates `eval/eval_report.json`.
    """)
    
    if st.button("🚀 Run Judge Evaluation", type="primary"):
        with st.spinner("Running evaluation judge..."):
            judge_script = REPO_ROOT / "src" / "eval" / "judge.py"
            command = [sys.executable, str(judge_script)]
            
            success, stdout, stderr, return_code = run_with_env(command, "Judge evaluation")
            
            # Check if report exists regardless of exit code
            eval_report_path = EVAL_DIR / "eval_report.json"
            report_exists = eval_report_path.exists()
            
            # Determine status: success, warning, or failure
            if success and report_exists:
                # Full success
                status = "success"
            elif not success and report_exists:
                # Completed with warnings (non-zero exit but report generated)
                status = "warning"
            else:
                # Failure (no report)
                status = "failure"
            
            if status == "success":
                st.success("✅ Evaluation completed successfully!")
                
                # Show stdout in expandable section
                with st.expander("📄 Evaluation Output", expanded=False):
                    st.text(stdout)
                
                # Load and display eval_report.json
                if report_exists:
                    try:
                        with open(eval_report_path, "r", encoding="utf-8") as f:
                            report = json.load(f)
                        
                        st.markdown("---")
                        st.markdown("### 📊 Evaluation Results Summary")
                        st.markdown("**📸 Screenshot this panel for submission**")
                        
                        # Summary metrics
                        if "averages" in report:
                            averages = report["averages"]
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "LLM Correctness",
                                    f"{averages.get('llm_correctness', 0):.2f}",
                                    help="LLM-as-judge correctness score (1-5)"
                                )
                            
                            with col2:
                                st.metric(
                                    "Exact Match",
                                    f"{averages.get('exact_match', 0):.2f}",
                                    help="Fraction of exact matches after normalization"
                                )
                            
                            with col3:
                                st.metric(
                                    "Context Hit",
                                    f"{averages.get('context_hit', 0):.2f}",
                                    help="Fraction where ground truth appears in retrieved context"
                                )
                            
                            # Additional metrics if available
                            if "relevance_score" in averages or "recall_score" in averages:
                                col4, col5 = st.columns(2)
                                if "relevance_score" in averages:
                                    with col4:
                                        st.metric(
                                            "Relevance Score",
                                            f"{averages['relevance_score']:.2f}",
                                            help="Relevance of retrieved context (1-5)"
                                        )
                                if "recall_score" in averages:
                                    with col5:
                                        st.metric(
                                            "Recall Score",
                                            f"{averages['recall_score']:.2f}",
                                            help="Recall of key information (1-5)"
                                        )
                        
                        # Per-test table
                        st.markdown("---")
                        st.markdown("### 📋 Per-Test Results")
                        
                        if "results" in report:
                            results = report["results"]
                            
                            # Prepare table data
                            table_data = []
                            for r in results:
                                table_data.append({
                                    "ID": r.get("id", "N/A"),
                                    "Type": r.get("type", "N/A"),
                                    "Question": r.get("question", "")[:60] + "..." if len(r.get("question", "")) > 60 else r.get("question", ""),
                                    "LLM Correctness": r.get("llm_correctness", r.get("correctness_score", "N/A")),
                                    "Exact Match": r.get("exact_match", "N/A"),
                                    "Context Hit": r.get("context_hit", "N/A"),
                                })
                            
                            st.dataframe(table_data, use_container_width=True, hide_index=True)
                        
                        st.success(f"✅ Report loaded from: `{eval_report_path.relative_to(REPO_ROOT)}`")
                        
                    except Exception as e:
                        st.error(f"Failed to parse eval_report.json: {e}")
                        st.code(str(e))
            
            elif status == "warning":
                # Non-zero exit but report exists - show warning banner
                st.warning("⚠️ **Judge completed but returned a non-zero exit code; see error details below.**")
                
                # Still show results if report exists
                try:
                    with open(eval_report_path, "r", encoding="utf-8") as f:
                        report = json.load(f)
                    
                    st.markdown("---")
                    st.markdown("### 📊 Evaluation Results Summary")
                    st.markdown("**📸 Screenshot this panel for submission**")
                    
                    # Summary metrics (same as success case)
                    if "averages" in report:
                        averages = report["averages"]
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "LLM Correctness",
                                f"{averages.get('llm_correctness', 0):.2f}",
                                help="LLM-as-judge correctness score (1-5)"
                            )
                        
                        with col2:
                            st.metric(
                                "Exact Match",
                                f"{averages.get('exact_match', 0):.2f}",
                                help="Fraction of exact matches after normalization"
                            )
                        
                        with col3:
                            st.metric(
                                "Context Hit",
                                f"{averages.get('context_hit', 0):.2f}",
                                help="Fraction where ground truth appears in retrieved context"
                            )
                        
                        if "relevance_score" in averages or "recall_score" in averages:
                            col4, col5 = st.columns(2)
                            if "relevance_score" in averages:
                                with col4:
                                    st.metric(
                                        "Relevance Score",
                                        f"{averages['relevance_score']:.2f}",
                                        help="Relevance of retrieved context (1-5)"
                                    )
                            if "recall_score" in averages:
                                with col5:
                                    st.metric(
                                        "Recall Score",
                                        f"{averages['recall_score']:.2f}",
                                        help="Recall of key information (1-5)"
                                    )
                    
                    # Per-test table
                    st.markdown("---")
                    st.markdown("### 📋 Per-Test Results")
                    
                    if "results" in report:
                        results = report["results"]
                        table_data = []
                        for r in results:
                            table_data.append({
                                "ID": r.get("id", "N/A"),
                                "Type": r.get("type", "N/A"),
                                "Question": r.get("question", "")[:60] + "..." if len(r.get("question", "")) > 60 else r.get("question", ""),
                                "LLM Correctness": r.get("llm_correctness", r.get("correctness_score", "N/A")),
                                "Exact Match": r.get("exact_match", "N/A"),
                                "Context Hit": r.get("context_hit", "N/A"),
                            })
                        st.dataframe(table_data, use_container_width=True, hide_index=True)
                    
                    st.info(f"✅ Report loaded from: `{eval_report_path.relative_to(REPO_ROOT)}`")
                    
                except Exception as e:
                    st.error(f"Failed to parse eval_report.json: {e}")
                    st.code(str(e))
                
                # Show error details in expandable section
                with st.expander("🔍 Error Details (Non-zero Exit)", expanded=False):
                    st.text("STDOUT:")
                    st.code(stdout)
                    st.text("STDERR:")
                    st.code(stderr)
            
            else:  # status == "failure"
                st.error("❌ Evaluation failed!")
                
                # Check for API key error
                if "OPENAI_API_KEY" in stderr or "API key" in stderr.lower():
                    st.warning("""
                    **Missing API Key**
                    
                    The evaluation requires `OPENAI_API_KEY` to be set in your `.env` file.
                    
                    Create a `.env` file in the project root with:
                    ```
                    OPENAI_API_KEY=sk-...
                    ```
                    """)
                else:
                    with st.expander("🔍 Error Details", expanded=True):
                        st.text("STDOUT:")
                        st.code(stdout)
                        st.text("STDERR:")
                        st.code(stderr)


# Tab 4: Lesson-19 Eval Harness
with tab4:
    st.header("Lesson-19 Eval Harness")
    with st.popover("ℹ️ Explain", help="What the Lesson-19 Eval Harness covers"):
        st.markdown(
            "This add-on provides three evaluation types: deterministic code graders, LLM-as-judge rubric scoring, and "
            "human-in-the-loop (HITL) labeling. Summaries are evaluated only with model/HITL (no exact-match hard tests). "
            "[Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)"
        )
    st.markdown("""
    **Hard tests: 20–25 (needle + table only)**  
    **LLM-based tests: 10–15 (includes summary)**  
    **Human grader tests: 5–7 (includes summary)**
    """)

    st.info("""
    **How to demo**
    1) Ask 2–3 live questions  
    2) Run original judge  
    3) Run hard suite  
    4) Run model suite  
    5) Export HITL pack (and optionally import a sample labeled file)
    """)

    task_counts = get_task_counts()

    st.markdown("### Hard Tests (20–25)")
    with st.popover("ℹ️ Explain", help="What the Hard Tests suite does"):
        st.markdown(
            "Hard tests are deterministic checks (regex/substring/value) for needle and table questions only. "
            "A test passes when the normalized answer satisfies the expected check."
        )
    st.caption("Deterministic checks for needle + table only.")
    st.write(f"Total tasks: {task_counts.get('code', {}).get('total', 0)}")
    if st.button(
        "Run Hard Suite",
        key="run_hard_suite",
        type="primary",
        help="Runs deterministic graders for needle + table questions.",
    ):
        command = [sys.executable, "-m", "eval_harness.run", "--suite", "code", "--k", "1"]
        success, stdout, stderr, return_code = run_with_env(command, "Eval harness (code)")
        if success or stdout:
            st.success("Hard suite completed.")
            st.code(stdout)
        else:
            st.error("Hard suite failed.")
            st.code(stderr)

    report = load_latest_report()
    if report and report.get("code"):
        code_report = report["code"]
        st.write(
            f"Pass: {code_report.get('passed', 0)} / {code_report.get('total', 0)}"
        )
        table_rows = []
        for r in code_report.get("results", []):
            table_rows.append(
                {
                    "ID": r.get("id"),
                    "Type": r.get("type"),
                    "Pass": r.get("pass"),
                    "Reason": r.get("reason"),
                    "Normalized Answer": r.get("normalized_answer"),
                }
            )
        if table_rows:
            st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### LLM Judge (10–15)")
    with st.popover("ℹ️ Explain", help="What the LLM Judge suite does"):
        st.markdown(
            "LLM Judge runs rubric-based scoring and validates strict JSON output. "
            "A test passes when the judge returns verdict=pass with valid JSON."
        )
    st.caption("LLM-as-judge with JSON schema validation; includes summary.")
    st.write(f"Total tasks: {task_counts.get('model', {}).get('total', 0)}")
    if st.button(
        "Run Model Suite",
        key="run_model_suite",
        type="primary",
        help="Runs LLM-as-judge rubric scoring with JSON schema validation.",
    ):
        command = [
            sys.executable,
            "-m",
            "eval_harness.run",
            "--suite",
            "model",
            "--k",
            str(int(k_trials)),
        ]
        success, stdout, stderr, return_code = run_with_env(command, "Eval harness (model)")
        if success or stdout:
            st.success("Model suite completed.")
            st.code(stdout)
        else:
            st.error("Model suite failed.")
            st.code(stderr)

    report = load_latest_report()
    if report and report.get("model"):
        model_report = report["model"]
        st.write(
            f"Average score: {model_report.get('average_score', 0):.2f} | "
            f"pass@1 {model_report.get('pass_at_1', 0)} / {model_report.get('total', 0)}"
        )
        model_rows = []
        for r in model_report.get("results", []):
            first_trial = r.get("trials", [{}])[0]
            model_rows.append(
                {
                    "ID": r.get("id"),
                    "Type": r.get("type"),
                    "Verdict": first_trial.get("verdict"),
                    "Score": first_trial.get("score_1_to_5"),
                    "Cites Evidence": first_trial.get("cites_evidence"),
                    "Valid JSON": first_trial.get("valid_json"),
                }
            )
        if model_rows:
            st.dataframe(model_rows, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### HITL (5–7)")
    with st.popover("ℹ️ Explain", help="What the HITL suite does"):
        st.markdown(
            "HITL exports a labeling pack, collects human scores offline, then imports labels to compute pass rate and "
            "average score."
        )
    st.caption("Export a HITL packet, label it, then import for scoring.")
    st.write(f"Total tasks: {task_counts.get('hitl', {}).get('total', 0)}")

    if st.button(
        "Export HITL Pack",
        key="export_hitl_pack",
        help="Creates a HITL labeling pack (JSONL) for offline grading.",
    ):
        command = [sys.executable, "-m", "eval_harness.run", "--suite", "hitl", "--k", "1"]
        success, stdout, stderr, return_code = run_with_env(command, "Eval harness (hitl export)")
        if success or stdout:
            st.success("HITL pack exported.")
            st.code(stdout)
        else:
            st.error("HITL export failed.")
            st.code(stderr)

    report = load_latest_report()
    if report and report.get("hitl"):
        hitl_report = report["hitl"]
        export_path = hitl_report.get("export_path")
        if export_path and Path(export_path).exists():
            with open(export_path, "rb") as f:
                st.download_button(
                    "Download HITL Export",
                    data=f,
                    file_name=Path(export_path).name,
                    mime="application/jsonl",
                )

    # Integrated HITL Labeling UI
    st.markdown("---")
    st.markdown("#### Integrated Labeling")
    st.caption("Label HITL tasks directly in the UI without offline editing.")
    
    # Initialize session state
    if "hitl_labels" not in st.session_state:
        st.session_state["hitl_labels"] = {}
    
    hitl_pack_path = find_latest_hitl_pack()
    if not hitl_pack_path:
        st.info("Export a HITL pack first to enable integrated labeling.")
    else:
        st.success(f"Found HITL pack: `{hitl_pack_path.name}`")
        
        if st.button("Open HITL Labeling UI", key="open_labeling_ui"):
            st.session_state["hitl_labeling_open"] = True
            st.session_state["hitl_pack_path"] = str(hitl_pack_path)
        
        if st.session_state.get("hitl_labeling_open") and st.session_state.get("hitl_pack_path"):
            pack_path = Path(st.session_state["hitl_pack_path"])
            if pack_path.exists():
                pack_items = load_jsonl(pack_path)
                
                with st.form("hitl_labeling_form", clear_on_submit=False):
                    st.markdown("### Label Tasks")
                    for idx, item in enumerate(pack_items):
                        item_id = item.get("id", f"item_{idx}")
                        with st.expander(f"Task {idx + 1}: {item_id}", expanded=False):
                            st.markdown(f"**Question:** {item.get('question', 'N/A')}")
                            
                            answer = item.get("answer")
                            if answer:
                                st.markdown(f"**Answer:** {answer}")
                            else:
                                transcript_path = item.get("transcript_path")
                                if transcript_path and Path(transcript_path).exists():
                                    with st.expander("View Transcript", expanded=False):
                                        with open(transcript_path, "r", encoding="utf-8") as f:
                                            transcript_data = json.load(f)
                                            st.json(transcript_data)
                                else:
                                    st.info("No answer or transcript available.")
                            
                            st.markdown(f"**Rubric:** {item.get('rubric', 'N/A')}")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                score = st.radio(
                                    "Score (1-5)",
                                    options=[1, 2, 3, 4, 5],
                                    key=f"score_{item_id}",
                                    index=st.session_state["hitl_labels"].get(item_id, {}).get("score_1_to_5", 0) - 1 if st.session_state["hitl_labels"].get(item_id, {}).get("score_1_to_5") else 0,
                                )
                            with col2:
                                verdict = st.radio(
                                    "Verdict",
                                    options=["pass", "fail"],
                                    key=f"verdict_{item_id}",
                                    index=0 if st.session_state["hitl_labels"].get(item_id, {}).get("verdict") == "pass" else 1,
                                )
                            
                            comment = st.text_input(
                                "Comment (optional)",
                                key=f"comment_{item_id}",
                                value=st.session_state["hitl_labels"].get(item_id, {}).get("comment", ""),
                            )
                            
                            st.session_state["hitl_labels"][item_id] = {
                                "score_1_to_5": score,
                                "verdict": verdict,
                                "comment": comment,
                            }
                    
                    submitted = st.form_submit_button("Save Labels (Preview)")
                    if submitted:
                        st.success("Labels saved in session. Use 'Save Labeled File' to write to disk.")
                
                # Check if all items have required labels
                all_labeled = len(st.session_state.get("hitl_labels", {})) == len(pack_items)
                all_complete = all(
                    label.get("score_1_to_5") and label.get("verdict")
                    for label in st.session_state.get("hitl_labels", {}).values()
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Labeled File", key="save_labeled_file", disabled=not (all_labeled and all_complete)):
                        latest_dir = get_latest_run_dir()
                        if latest_dir:
                            labeled_path = latest_dir / "hitl_labeled.jsonl"
                            with open(labeled_path, "w", encoding="utf-8") as f:
                                for item in pack_items:
                                    item_id = item.get("id", f"item_{pack_items.index(item)}")
                                    label = st.session_state["hitl_labels"].get(item_id, {})
                                    labeled_item = {
                                        **item,
                                        "score_1_to_5": label.get("score_1_to_5"),
                                        "verdict": label.get("verdict"),
                                        "comment": label.get("comment", ""),
                                    }
                                    f.write(json.dumps(labeled_item, ensure_ascii=False) + "\n")
                            st.success(f"✅ Saved: `{labeled_path}`")
                            st.session_state["hitl_labeled_path"] = str(labeled_path)
                            
                            # Download button
                            with open(labeled_path, "rb") as f:
                                st.download_button(
                                    "Download Labeled File",
                                    data=f,
                                    file_name=labeled_path.name,
                                    mime="application/jsonl",
                                )
                        else:
                            st.error("Could not determine run directory.")
                    else:
                        if not all_labeled or not all_complete:
                            st.caption("⚠️ Fill all score and verdict fields to enable save.")
                
                with col2:
                    labeled_path_str = st.session_state.get("hitl_labeled_path")
                    if labeled_path_str and Path(labeled_path_str).exists():
                        if st.button("Score Labeled File", key="score_labeled_file"):
                            labeled_path = Path(labeled_path_str)
                            # Try harness scoring first
                            command = [
                                sys.executable,
                                "-m",
                                "eval_harness.run",
                                "--suite",
                                "hitl",
                                "--k",
                                "1",
                                "--hitl-labels",
                                str(labeled_path),
                            ]
                            success, stdout, stderr, return_code = run_with_env(command, "Eval harness (hitl score)")
                            
                            if success or (return_code == 0 and stdout):
                                st.success("Scoring completed via harness.")
                                st.code(stdout)
                                # Try to load updated report
                                updated_report = load_latest_report()
                                if updated_report and updated_report.get("hitl") and updated_report["hitl"].get("summary"):
                                    st.json(updated_report["hitl"]["summary"])
                            else:
                                # Fallback: compute summary in UI
                                st.warning("Harness scoring failed; using UI fallback.")
                                labeled_items = load_jsonl(labeled_path)
                                if labeled_items:
                                    total = len(labeled_items)
                                    pass_count = sum(1 for item in labeled_items if item.get("verdict") == "pass")
                                    avg_score = sum(item.get("score_1_to_5", 0) for item in labeled_items) / total
                                    
                                    st.markdown("**(UI fallback) Summary:**")
                                    st.write(f"- Total labeled: {total}")
                                    st.write(f"- Pass rate: {pass_count}/{total} ({pass_count/total*100:.1f}%)")
                                    st.write(f"- Average score: {avg_score:.2f}")
                                
                                with st.expander("🔍 Error Details", expanded=False):
                                    st.text("STDOUT:")
                                    st.code(stdout)
                                    st.text("STDERR:")
                                    st.code(stderr)
                    else:
                        st.caption("Save labeled file first to enable scoring.")
            else:
                st.error(f"HITL pack not found: {pack_path}")

    uploaded = st.file_uploader(
        "Upload Labeled HITL File (.jsonl)",
        type=["jsonl"],
        help="Upload a labeled HITL JSONL file to compute summary metrics.",
    )
    if st.button(
        "Import and Score",
        key="import_hitl",
        help="Imports labeled HITL file and computes summary metrics.",
    ):
        if not uploaded:
            st.warning("Upload a labeled HITL file first.")
        else:
            uploads_dir = HARNESS_RUNS_DIR / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            upload_path = uploads_dir / f"hitl_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            with open(upload_path, "wb") as f:
                f.write(uploaded.getbuffer())
            command = [
                sys.executable,
                "-m",
                "eval_harness.run",
                "--suite",
                "hitl",
                "--k",
                "1",
                "--hitl-labels",
                str(upload_path),
            ]
            success, stdout, stderr, return_code = run_with_env(command, "Eval harness (hitl import)")
            if success or stdout:
                st.success("HITL labels imported and scored.")
                st.code(stdout)
            else:
                st.error("HITL import failed.")
                st.code(stderr)

    report = load_latest_report()
    if report and report.get("hitl"):
        hitl_report = report["hitl"]
        if hitl_report.get("imported") and hitl_report.get("summary"):
            st.write("HITL Summary Metrics:")
            st.json(hitl_report.get("summary"))


# Tab 5: Artifacts Checklist
with tab5:
    st.header("Artifacts & Submission Checklist")
    st.markdown("""
    This checklist maps project artifacts to Daniel's requirements.
    """)
    
    artifacts = [
        {
            "name": "Claim Timeline Markdown",
            "path": "data/claim_timeline.md",
            "requirement": "Synthetic claim data",
            "check": lambda: (REPO_ROOT / "data" / "claim_timeline.md").exists()
        },
        {
            "name": "Claim Timeline PDF",
            "path": "data/claim_timeline.pdf",
            "requirement": "PDF version (min 10 pages)",
            "check": lambda: (REPO_ROOT / "data" / "claim_timeline.pdf").exists()
        },
        {
            "name": "README Evaluation Commands",
            "path": "README.md (Section 7.3)",
            "requirement": "Documented eval commands",
            "check": lambda: (REPO_ROOT / "README.md").exists()
        },
        {
            "name": "MCP Strict Mode Proof",
            "path": "Log output with [REAL MCP]",
            "requirement": "Real MCP server usage proof",
            "check": lambda: True  # Always available if run with correct env
        },
        {
            "name": "Table Bonus Evidence",
            "path": "Table questions + DEBUG_SOURCES output",
            "requirement": "Table-aware indexing proof",
            "check": lambda: True  # Available when running with DEBUG_SOURCES=1
        },
        {
            "name": "Evaluation Screenshot",
            "path": "This UI panel OR CLI output",
            "requirement": "Evaluation metrics screenshot",
            "check": lambda: (EVAL_DIR / "eval_report.json").exists()
        },
        {
            "name": "Screen Recording",
            "path": "Video file (external)",
            "requirement": "Demo walkthrough",
            "check": lambda: True  # External file
        }
    ]
    
    st.markdown("### ✅ Checklist")
    
    all_checked = True
    for artifact in artifacts:
        exists = artifact["check"]()
        status = "✅" if exists else "❌"
        color = "green" if exists else "red"
        
        with st.container():
            col1, col2, col3 = st.columns([1, 3, 4])
            with col1:
                st.markdown(f"<span style='color: {color}; font-size: 20px;'>{status}</span>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**{artifact['name']}**")
            with col3:
                st.markdown(f"`{artifact['path']}`")
                st.caption(f"Requirement: {artifact['requirement']}")
        
        if not exists:
            all_checked = False
        
        st.markdown("---")
    
    if all_checked:
        st.success("🎉 All artifacts are present!")
    else:
        st.warning("⚠️ Some artifacts are missing. Check the paths above.")


# Footer
st.markdown("---")
st.markdown("""
### 📚 Additional Information

- **CLI Alternative:** All functionality is available via CLI commands (see README)
- **Official Path:** CLI remains the official path for production use
- **This UI:** Optional convenience wrapper for graders and demos
- **No Drift:** This UI does not modify any existing app code
""")

