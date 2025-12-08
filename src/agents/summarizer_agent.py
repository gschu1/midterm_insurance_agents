from typing import Any, Dict, List

from llama_index.core.query_engine import BaseQueryEngine


class SummarizationAgent:
    """
    Agent specialized in high-level / timeline questions
    over the insurance claim.

    It uses a SummaryIndex-backed query engine.
    """

    def __init__(self, query_engine: BaseQueryEngine):
        self.query_engine = query_engine

    def answer(self, question: str) -> Dict[str, Any]:
        q = question.strip()
        response = self.query_engine.query(q)

        sources: List[Dict[str, Any]] = []
        for sn in getattr(response, "source_nodes", [])[:5]:
            try:
                node = sn.node
                sources.append(
                    {
                        "node_id": sn.node_id,
                        "score": sn.score,
                        "text": node.get_content(metadata_mode="none")[:500],
                    }
                )
            except AttributeError:
                pass

        return {
            "agent": "summarization",
            "question": q,
            "answer": str(response),
            "sources": sources,
        }
