import os
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

        # Debug mode: print top 3 source nodes with metadata
        if os.getenv("DEBUG_SOURCES") == "1":
            print("\n[DEBUG] Top 3 source nodes:")
            for i, sn in enumerate(getattr(response, "source_nodes", [])[:3], 1):
                try:
                    node = sn.node
                    metadata = node.metadata if hasattr(node, "metadata") else {}
                    node_type = metadata.get("node_type", "regular")
                    table = metadata.get("table", "-")
                    row_index = metadata.get("row_index", "-")
                    node_id = sn.node_id if hasattr(sn, "node_id") else "-"
                    score = sn.score if hasattr(sn, "score") else "-"
                    print(f"  {i}. node_id={node_id[:20]}... | type={node_type} | table={table} | row={row_index} | score={score}")
                except Exception:
                    print(f"  {i}. [error reading node]")

        return {
            "agent": "summarization",
            "question": q,
            "answer": str(response),
            "sources": sources,
        }
