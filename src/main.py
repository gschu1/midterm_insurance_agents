from indexing import get_query_engines
from agents.summarizer_agent import SummarizationAgent
from agents.needle_agent import NeedleAgent
from agents.manager import ManagerAgent


def main():
    # Build indexes and query engines
    engines = get_query_engines()

    # Instantiate agents
    summarizer = SummarizationAgent(engines["summary_engine"])
    needle = NeedleAgent(engines["needle_engine"])
    manager = ManagerAgent(summarizer, needle)

    print("Midterm – Insurance Claim Agents")
    print("Ask questions about the claim timeline.")
    print("Type 'exit' or 'quit' to leave.")

    while True:
        q = input("\nQuestion: ").strip()
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue

        result = manager.answer(q)

        print(f"\n[Chosen agent: {result['chosen_agent']}]")
        print(result["answer"])
        # If you want to debug retrieval later, you can also print result["sources"]


if __name__ == "__main__":
    main()
