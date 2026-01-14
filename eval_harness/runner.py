"""
Runner adapter that calls the existing midterm app without modifications.

This module imports and uses the existing ManagerAgent and related code
exactly as-is, without any refactoring.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src/ to path so we can import existing modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Import existing app code (no modifications)
from indexing import get_query_engines  # noqa: E402
from agents.summarizer_agent import SummarizationAgent  # noqa: E402
from agents.needle_agent import NeedleAgent  # noqa: E402
from agents.manager import ManagerAgent  # noqa: E402


def build_manager() -> ManagerAgent:
    """
    Build the ManagerAgent using existing code.
    
    This is a thin wrapper around the existing build pattern.
    """
    engines = get_query_engines()
    summarizer = SummarizationAgent(engines["summary_engine"])
    needle = NeedleAgent(engines["needle_engine"])
    return ManagerAgent(summarizer, needle)


def run_trial(question: str) -> Dict[str, Any]:
    """
    Run a single trial: ask the question and return the result.
    
    This calls the existing app exactly as it would be called in production.
    No modifications to the app code.
    
    Returns:
        Dict with:
        - answer: str
        - chosen_agent: str
        - sources: List[Dict] with node_id, score, text, and potentially metadata
        - Any other fields returned by manager.answer()
    """
    manager = build_manager()
    result = manager.answer(question)
    
    # Ensure we have the expected structure
    return {
        "answer": result.get("answer", ""),
        "chosen_agent": result.get("chosen_agent", result.get("agent", "unknown")),
        "sources": result.get("sources", []),
        "question": result.get("question", question),
        # Preserve any other fields
        **{k: v for k, v in result.items() if k not in ["answer", "chosen_agent", "sources", "question"]}
    }

