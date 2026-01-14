import sys
from pathlib import Path
from typing import Any, Dict

# Ensure we can import from src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from indexing import get_query_engines  # noqa: E402
from agents.summarizer_agent import SummarizationAgent  # noqa: E402
from agents.needle_agent import NeedleAgent  # noqa: E402
from agents.manager import ManagerAgent  # noqa: E402

_manager: ManagerAgent | None = None


def get_manager() -> ManagerAgent:
    global _manager
    if _manager is None:
        engines = get_query_engines()
        summarizer = SummarizationAgent(engines["summary_engine"])
        needle = NeedleAgent(engines["needle_engine"])
        _manager = ManagerAgent(summarizer, needle)
    return _manager


def answer_question(question: str) -> Dict[str, Any]:
    manager = get_manager()
    result = manager.answer(question)
    return result

