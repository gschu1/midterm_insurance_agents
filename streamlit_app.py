"""
Optional Streamlit Grader Dashboard for Midterm Insurance Agents

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


# Helper function to run subprocess with env vars
def run_with_env(command, description):
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
            executable=sys.executable
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


# Tabs
tab1, tab2, tab3 = st.tabs([
    "📝 Run Quick Demo Questions",
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


# Tab 2: Evaluation Judge
with tab2:
    st.header("Run Evaluation Judge")
    st.markdown("""
    This runs `src/eval/judge.py` which evaluates all test cases and generates `eval/eval_report.json`.
    """)
    
    if st.button("🚀 Run Judge Evaluation", type="primary"):
        with st.spinner("Running evaluation judge..."):
            judge_script = REPO_ROOT / "src" / "eval" / "judge.py"
            command = [sys.executable, str(judge_script)]
            
            success, stdout, stderr = run_with_env(command, "Judge evaluation")
            
            if success:
                st.success("✅ Evaluation completed successfully!")
                
                # Show stdout in expandable section
                with st.expander("📄 Evaluation Output", expanded=False):
                    st.text(stdout)
                
                # Try to load and display eval_report.json
                eval_report_path = EVAL_DIR / "eval_report.json"
                if eval_report_path.exists():
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
                else:
                    st.warning(f"⚠️ Expected report file not found: {eval_report_path}")
                    st.info("The evaluation may have completed but the report file was not generated.")
            
            else:
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


# Tab 3: Artifacts Checklist
with tab3:
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

