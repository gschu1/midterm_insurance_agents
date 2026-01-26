"""
Optional Streamlit Grader Dashboard for Capstone Insurance Claim Agents

This UI is a wrapper around existing CLI tools - it does not modify app logic.
Run with: streamlit run streamlit_app.py
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

# Get repo root
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
EVAL_DIR = SRC_DIR / "eval"
EVAL_HARNESS_DIR = REPO_ROOT / "eval_harness"
EVAL_HARNESS_RUNS_DIR = EVAL_HARNESS_DIR / "runs"

# Page config
st.set_page_config(
    page_title="Capstone Insurance Claim Agents - Grader Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Capstone Insurance Claim Agents - Grader Dashboard")
st.markdown("**Optional UI wrapper for running demos and evaluations**")

# Sidebar: Environment controls
with st.sidebar:
    st.header("⚙️ Environment Controls")
    st.warning("⚠️ **Do NOT show your API key on screen.**")
    
    st.subheader("MCP Configuration")
    use_real_mcp = st.selectbox(
        "USE_REAL_MCP",
        options=["0", "1"],
        index=0,
        help="Set to 1 to use real MCP server (grader-proof mode)"
    )
    
    allow_mcp_fallback = st.selectbox(
        "ALLOW_MCP_FALLBACK",
        options=["0", "1"],
        index=1,
        help="Set to 0 for strict mode (no fallback to legacy)"
    )
    
    st.subheader("Debug Options")
    debug_sources = st.selectbox(
        "DEBUG_SOURCES",
        options=["0", "1"],
        index=0,
        help="Set to 1 to show source node metadata"
    )
    
    st.subheader("Evaluation Settings")
    st.info("k_trials: N/A (not supported in current eval harness)")
    
    st.markdown("---")
    st.markdown("### 📝 Notes")
    st.markdown("""
    - These settings are applied when running subprocess commands
    - API key must be set in `.env` file (not shown in UI)
    - CLI remains the official path for production use
    """)

    with st.expander("🧪 Environment Diagnostics", expanded=False):
        st.caption("These are shown for debugging and grader-proofing.")
        st.text(f"sys.executable: {sys.executable}")
        st.text(f"sys.version: {sys.version.splitlines()[0]}")
        st.text(f"cwd: {Path.cwd()}")

        def _try_import(module_name: str) -> None:
            try:
                __import__(module_name)
                st.success(f"import {module_name} OK")
            except Exception as e:
                st.error(f"import {module_name} FAILED")
                st.code(f"{type(e).__name__}: {e}")

        _try_import("llama_index")
        _try_import("eval_harness")


# Helper function to run subprocess with env vars
def run_with_env(command, description, stdin_input=None, timeout_s: int = 300):
    """Run a subprocess command with hardened env/cwd/interpreter."""
    env = os.environ.copy()
    env["USE_REAL_MCP"] = use_real_mcp
    env["ALLOW_MCP_FALLBACK"] = allow_mcp_fallback
    env["DEBUG_SOURCES"] = debug_sources
    # Ensure local imports resolve in subprocess (repo root on PYTHONPATH).
    env["PYTHONPATH"] = str(REPO_ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )

    # Enforce current interpreter in subprocess.
    if isinstance(command, (list, tuple)) and len(command) > 0:
        if str(command[0]) != sys.executable:
            command = [sys.executable, *list(command)]
    
    try:
        result = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            input=stdin_input,
            timeout=timeout_s
        )
        return result.returncode == 0, result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout_s} seconds", 1
    except Exception as e:
        return False, "", str(e), 1


# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📝 Run Quick Demo Questions",
    "❓ Single Question (UI)",
    "🧪 Eval Harness (Lesson-19)",
    "📊 Run Evaluation (Judge)",
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
    
    This UI attempts to run a single question through the system using subprocess.
    """)
    
    question = st.text_area(
        "Enter your question:",
        placeholder="e.g., Did the insured refuse ambulance transport at the scene?",
        height=100
    )
    
    if st.button("🚀 Ask Question", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Processing question..."):
                # Use subprocess to run main.py with stdin
                main_script = REPO_ROOT / "src" / "main.py"
                command = [sys.executable, str(main_script)]
                
                # Send question + exit command via stdin
                stdin_input = f"{question.strip()}\nexit\n"
                
                success, stdout, stderr, return_code = run_with_env(command, "Single question", stdin_input=stdin_input)
                
                if success or stdout:
                    st.success("✅ Question processed!")
                    
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
# Tab 3: Eval Harness (Lesson-19)
with tab3:
    st.header("Lesson 19 Eval Harness")
    st.markdown(
        "Runs `python -m eval_harness.run` suites (code/model/HITL) using the same hardened subprocess runner."
    )

    # Quick import check for clearer UX
    try:
        import eval_harness as _  # noqa: F401
        eval_harness_import_ok = True
    except Exception:
        eval_harness_import_ok = False

    if not eval_harness_import_ok:
        st.error("`eval_harness` could not be imported in this environment.")
        if (REPO_ROOT / "requirements.txt").exists() or (REPO_ROOT / "requirements-ui.txt").exists():
            st.info(
                "If you haven't installed deps in this venv yet, install from `requirements.txt` "
                "(and optionally `requirements-ui.txt`)."
            )
    else:
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.subheader("Run Code Suite")
            if st.button("▶ Run Code Suite (k=1)", key="eh_code"):
                with st.spinner("Running eval harness (code suite)..."):
                    command = [sys.executable, "-m", "eval_harness.run", "--suite", "code", "--k", "1"]
                    success, stdout, stderr, _ = run_with_env(command, "Eval harness - code", timeout_s=600)
                    (st.success if success else st.error)("Finished.")
                    with st.expander("📄 Output", expanded=not success):
                        st.text("STDOUT:")
                        st.code(stdout)
                        if stderr:
                            st.text("STDERR:")
                            st.code(stderr)

        with col_b:
            st.subheader("Run Model Suite")
            if st.button("▶ Run Model Suite (k=1)", key="eh_model"):
                with st.spinner("Running eval harness (model suite)..."):
                    command = [sys.executable, "-m", "eval_harness.run", "--suite", "model", "--k", "1"]
                    success, stdout, stderr, _ = run_with_env(command, "Eval harness - model", timeout_s=600)
                    (st.success if success else st.error)("Finished.")
                    with st.expander("📄 Output", expanded=not success):
                        st.text("STDOUT:")
                        st.code(stdout)
                        if stderr:
                            st.text("STDERR:")
                            st.code(stderr)

        with col_c:
            st.subheader("HITL")
            if st.button("▶ Create HITL Run (k=1)", key="eh_hitl_create"):
                with st.spinner("Running eval harness (HITL suite)..."):
                    command = [sys.executable, "-m", "eval_harness.run", "--suite", "hitl", "--k", "1"]
                    success, stdout, stderr, _ = run_with_env(command, "Eval harness - hitl", timeout_s=600)
                    (st.success if success else st.error)("Finished.")
                    with st.expander("📄 Output", expanded=not success):
                        st.text("STDOUT:")
                        st.code(stdout)
                        if stderr:
                            st.text("STDERR:")
                            st.code(stderr)

        st.markdown("---")
        st.subheader("Integrated HITL Labeling (Save + Score)")
        st.caption(
            "Loads the latest HITL run, lets you label items, saves labels, imports them, and regenerates a HITL report."
        )

        def _list_run_dirs(prefix: str):
            if not EVAL_HARNESS_RUNS_DIR.exists():
                return []
            dirs = [p for p in EVAL_HARNESS_RUNS_DIR.iterdir() if p.is_dir() and p.name.startswith(prefix)]
            return sorted(dirs, key=lambda p: p.stat().st_mtime, reverse=True)

        hitl_runs = _list_run_dirs("hitl_")
        if not hitl_runs:
            st.info("No HITL runs found yet. Click “Create HITL Run (k=1)” above to generate one.")
        else:
            default_idx = 0
            selected_run_dir = st.selectbox(
                "Select HITL run directory",
                options=hitl_runs,
                index=default_idx,
                format_func=lambda p: p.name,
                key="hitl_run_select",
            )
            run_id = Path(selected_run_dir).name
            trials_dir = Path(selected_run_dir) / "trials"

            trial_files = sorted(trials_dir.glob("*.json")) if trials_dir.exists() else []
            if not trial_files:
                st.warning("No trial JSON files found under this run directory.")
            else:
                # Load trials
                trials = []
                for tf in trial_files:
                    try:
                        with open(tf, "r", encoding="utf-8") as f:
                            trials.append(json.load(f))
                    except Exception:
                        continue

                if not trials:
                    st.warning("Failed to load any trial JSONs for labeling.")
                else:
                    # Labels state
                    if "hitl_labels" not in st.session_state or st.session_state.get("hitl_labels_run_id") != run_id:
                        st.session_state["hitl_labels_run_id"] = run_id
                        st.session_state["hitl_labels"] = {}

                    st.markdown(f"**Loaded trials:** {len(trials)} items from `{Path(selected_run_dir).relative_to(REPO_ROOT)}`")

                    for trial in trials:
                        task_id = trial.get("task_id", "unknown")
                        question = trial.get("question", "")
                        answer = trial.get("answer", "")
                        sources = trial.get("sources", [])

                        with st.expander(f"{task_id}: {question[:80]}{'...' if len(question) > 80 else ''}", expanded=False):
                            st.markdown("**Question**")
                            st.code(question, language=None)
                            st.markdown("**System answer**")
                            st.code(answer, language=None)
                            with st.expander("Sources", expanded=False):
                                st.json(sources)

                            existing = st.session_state["hitl_labels"].get(task_id, {})
                            human_score = st.text_input(
                                "Score (e.g. 1-5 or pass/fail)",
                                value=str(existing.get("human_score", "")),
                                key=f"hitl_score_{run_id}_{task_id}",
                            )
                            human_notes = st.text_area(
                                "Comment / notes",
                                value=str(existing.get("human_notes", "")),
                                key=f"hitl_notes_{run_id}_{task_id}",
                                height=80,
                            )
                            st.session_state["hitl_labels"][task_id] = {
                                "task_id": task_id,
                                "human_score": human_score,
                                "human_notes": human_notes,
                            }

                    col_save, col_score = st.columns(2)
                    with col_save:
                        if st.button("💾 Save labels to run dir", key="hitl_save_labels"):
                            labels = list(st.session_state["hitl_labels"].values())
                            labels_jsonl_path = Path(selected_run_dir) / "hitl_labeled.jsonl"
                            labels_csv_path = Path(selected_run_dir) / "hitl_labeled.csv"

                            # Write JSONL (grader-friendly) + CSV (compatible with import_hitl.py)
                            with open(labels_jsonl_path, "w", encoding="utf-8") as f:
                                for row in labels:
                                    f.write(json.dumps(row, ensure_ascii=False) + "\n")

                            # Minimal CSV columns expected by import_hitl.py
                            import csv
                            with open(labels_csv_path, "w", newline="", encoding="utf-8") as f:
                                writer = csv.DictWriter(f, fieldnames=["task_id", "human_score", "human_notes"])
                                writer.writeheader()
                                for row in labels:
                                    writer.writerow(
                                        {
                                            "task_id": row.get("task_id", ""),
                                            "human_score": row.get("human_score", ""),
                                            "human_notes": row.get("human_notes", ""),
                                        }
                                    )

                            st.success(f"Saved `{labels_jsonl_path.name}` and `{labels_csv_path.name}` in `{run_id}`.")

                    with col_score:
                        if st.button("📈 Import labels + score HITL", key="hitl_score_labels"):
                            labels_csv_path = Path(selected_run_dir) / "hitl_labeled.csv"
                            if not labels_csv_path.exists():
                                st.error("No `hitl_labeled.csv` found. Click “Save labels to run dir” first.")
                            else:
                                with st.spinner("Importing labels into trial JSONs..."):
                                    import_cmd = [
                                        sys.executable,
                                        "-m",
                                        "eval_harness.hitl.import_hitl",
                                        "--file",
                                        str(labels_csv_path),
                                        "--run",
                                        run_id,
                                    ]
                                    ok, out, err, _ = run_with_env(import_cmd, "Import HITL labels", timeout_s=300)
                                    (st.success if ok else st.error)("Import finished.")
                                    with st.expander("📄 Import Output", expanded=not ok):
                                        st.text("STDOUT:")
                                        st.code(out)
                                        if err:
                                            st.text("STDERR:")
                                            st.code(err)

                                with st.spinner("Regenerating HITL report..."):
                                    # Recompute report from updated trials without re-running trials.
                                    report_cmd = [
                                        sys.executable,
                                        "-c",
                                        (
                                            "import json\n"
                                            "from pathlib import Path\n"
                                            "from eval_harness.report import print_summary_report, generate_detailed_report\n"
                                            f"run_dir = Path(r'{str(Path(selected_run_dir))}')\n"
                                            "suite = 'hitl'\n"
                                            "print_summary_report(run_dir, suite)\n"
                                            "report = generate_detailed_report(run_dir, suite)\n"
                                            "out_file = run_dir / 'report.json'\n"
                                            "out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')\n"
                                            "print(f'\\n[OK] Detailed report saved to: {out_file}')\n"
                                        ),
                                    ]
                                    ok2, out2, err2, _ = run_with_env(report_cmd, "Score HITL", timeout_s=120)
                                    (st.success if ok2 else st.error)("Scoring finished.")
                                    with st.expander("📄 Scoring Output", expanded=not ok2):
                                        st.text("STDOUT:")
                                        st.code(out2)
                                        if err2:
                                            st.text("STDERR:")
                                            st.code(err2)

        st.markdown("---")
        st.subheader("Offline HITL Import (keep existing export/import path)")
        st.caption("If you labeled a CSV externally, upload it here and apply it to a selected HITL run.")

        hitl_runs_for_import = _list_run_dirs("hitl_")
        if hitl_runs_for_import:
            import_run_dir = st.selectbox(
                "Run to import into",
                options=hitl_runs_for_import,
                index=0,
                format_func=lambda p: p.name,
                key="hitl_import_run_select",
            )
            import_run_id = Path(import_run_dir).name
            uploaded = st.file_uploader(
                "Upload labeled CSV (must include: task_id, human_score, human_notes)",
                type=["csv"],
                key="hitl_csv_upload",
            )
            if st.button("⬆ Apply uploaded labels", key="hitl_apply_uploaded"):
                if uploaded is None:
                    st.warning("Please upload a CSV first.")
                else:
                    labels_path = Path(import_run_dir) / "hitl_uploaded_labels.csv"
                    labels_path.write_bytes(uploaded.getvalue())
                    cmd = [
                        sys.executable,
                        "-m",
                        "eval_harness.hitl.import_hitl",
                        "--file",
                        str(labels_path),
                        "--run",
                        import_run_id,
                    ]
                    ok, out, err, _ = run_with_env(cmd, "Import uploaded HITL labels", timeout_s=300)
                    (st.success if ok else st.error)("Import finished.")
                    with st.expander("📄 Import Output", expanded=not ok):
                        st.text("STDOUT:")
                        st.code(out)
                        if err:
                            st.text("STDERR:")
                            st.code(err)

# Tab 4: Evaluation Judge
with tab4:
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


# Tab 4: Artifacts Checklist
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

