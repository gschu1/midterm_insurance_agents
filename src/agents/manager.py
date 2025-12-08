from typing import Any, Dict


class ManagerAgent:
    """
    Simple router agent that decides whether a question should go to
    the SummarizationAgent or the NeedleAgent, based on heuristics.
    """

    def __init__(self, summarization_agent, needle_agent):
        self.summarization_agent = summarization_agent
        self.needle_agent = needle_agent

    def _route(self, question: str) -> str:
        q = question.lower()

        # Heuristic: words strongly suggestive of summaries / timelines
        summary_keywords = [
            "overview",
            "summary",
            "summarize",
            "high-level",
            "high level",
            "timeline",
            "chronology",
            "in general",
            "overall",
            "across the claim",
            "over the course",
        ]

        if any(kw in q for kw in summary_keywords):
            return "summarization"

        # Default route: needle agent
        return "needle"

    def answer(self, question: str) -> Dict[str, Any]:
        route = self._route(question)

        if route == "summarization":
            result = self.summarization_agent.answer(question)
        else:
            route = "needle"
            result = self.needle_agent.answer(question)

        # annotate result
        result["chosen_agent"] = route
        return result
