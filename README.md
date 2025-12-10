# Midterm – Insurance Claim Agents

This project implements a small but realistic RAG + agents system for a synthetic
motor insurance claim. It demonstrates:

- Multi-granularity indexing (hierarchical + summary)
- Agent-based routing between different retrievers
- A simple external tool for deterministic date arithmetic (MCP-style)
- LLM-as-a-judge evaluation for correctness, relevance, and recall

The code is organized so it can be run from the command line and inspected as a
reference implementation of the midterm assignment.

---

## 1. Repository structure

```text
midterm_insurance_agents/
  data/
    claim_timeline.md      # Synthetic claim timeline (single markdown document)
  src/
    indexing.py            # Index building + query engine setup
    main.py                # CLI for interactive Q&A via agents
    agents/
      __init__.py
      manager.py           # Router agent
      summarizer_agent.py  # High-level / timeline agent
      needle_agent.py      # Fine-grained factual agent (+ date tool integration)
    mcp/
      __init__.py
      client.py            # Date-difference tool (MCP-style external function)
    eval/
      test_cases.json      # Evaluation questions + ground-truth answers
      judge.py             # LLM-as-a-judge evaluation script
  README.md
  requirements.txt
  .env                     # API key (not committed)
2. Data design – synthetic claim timeline
The system works over a single synthetic claim file:

data/claim_timeline.md

This document is structured into five logical documents:

Initial loss report (FNOL) – accident description and initial injuries

Emergency room report – diagnosis and treatment

Adjuster site visit report – vehicle/scene assessment

Physiotherapy progress report – follow-up treatment and recovery

Settlement email thread – negotiations and final settlement

Design choices:

A single file with clear section headings keeps ingestion simple while
still providing realistic heterogeneity (intake notes, medical reports,
adjuster notes, and emails).

The text includes both:

High-level timeline information (dates and phases of the claim), and

At least one “needle-in-haystack” detail:

The insured initially refuses ambulance transport at the scene.

Numeric details (e.g. NIS 45,000 settlement, specific dates) support both
factual questions and the date-difference tool.

This structure is enough to exercise both summary-style and fine-grained
retrieval in a controlled, explainable way.

3. Indexing and retrieval design
All indexing logic lives in src/indexing.py.

3.1 LLM and embedding configuration
The project uses LlamaIndex with:

gpt-3.5-turbo as the LLM (Settings.llm)

text-embedding-ada-002 as the embedding model (Settings.embed_model)

Configuration is done once in init_llama_settings() and reused across
indexing and evaluation.

3.2 Hierarchical nodes and chunk sizes
The core design choice is hierarchical chunking with explicit sizes:

python
Copy code
node_parser = HierarchicalNodeParser.from_defaults(
    chunk_sizes=[1024, 512, 128]
)
128-token leaf chunks:

Used for precise retrieval (“needle” questions).

Small enough to avoid burying rare facts in large blobs.

512-token mid-level chunks:

Serve as intermediate units AutoMergingRetriever can merge into when more
context is needed.

1024-token top-level chunks:

Roughly correspond to sections or multi-paragraph spans.

Useful for holistic reasoning and for building summaries.

Design rationale:

The hierarchy balances recall and coherence:

Small chunks improve the chance that a specific fact is retrieved.

Larger merged chunks keep answers contextually coherent when needed.

Explicit chunk sizes make the design easier to explain and reproduce.

3.3 Base index and auto-merging retriever
The leaf nodes (128-token chunks) are embedded and indexed via:

python
Copy code
base_index = VectorStoreIndex(leaf_nodes, storage_context=storage_context)
base_retriever = base_index.as_retriever(similarity_top_k=6)
On top of this, an AutoMergingRetriever is used:

python
Copy code
auto_merging_retriever = AutoMergingRetriever(
    base_retriever,
    storage_context=storage_context,
    verbose=True,
)
Design rationale:

VectorStoreIndex on leaf nodes:

Keeps the index fine-grained for high recall.

AutoMergingRetriever:

Dynamically merges related small chunks into their parents when answering.

Allows the system to recover a more coherent passage without manually
tuning large chunk sizes.

Verbose logging is enabled to make merging behaviour visible for
debugging and demonstration.

3.4 Summary index
In addition to the hierarchical index, a SummaryIndex is built:

python
Copy code
summary_index = SummaryIndex.from_documents(documents)
summary_engine = summary_index.as_query_engine(
    response_mode="tree_summarize"
)
Design rationale:

SummaryIndex is used for high-level and timeline questions.

The tree_summarize response mode encourages the LLM to synthesize across
sections rather than answer from a single local chunk.

Separating the summary view from the fine-grained view makes it natural to
assign them to different agents.

3.5 Query engines
indexing.py exposes a helper:

python
Copy code
get_query_engines() -> {
  "summary_engine": ...,
  "needle_engine":  ...
}
summary_engine: query engine over the SummaryIndex

needle_engine: RetrieverQueryEngine over the AutoMergingRetriever

These engines are passed into the agents, so agents do not need to know about
document ingestion or index construction.

4. Agent design and routing
All agent logic lives in src/agents/.

4.1 SummarizationAgent
File: src/agents/summarizer_agent.py

Uses the summary_engine from get_query_engines().

Intended for:

High-level overviews of the claim.

Questions about the overall timeline / phases.

Behaviour:

Calls summary_engine.query(question) and returns:

The answer text.

A small set of source nodes with node IDs, scores, and short text snippets
for evaluation.

4.2 NeedleAgent
File: src/agents/needle_agent.py

Uses the needle_engine (AutoMergingRetriever).

Intended for:

Precise factual questions (dates, amounts, yes/no).

Questions relying on details that may only appear once.

Behaviour:

First checks whether the question matches a specific pattern that should use
the date-difference tool (see section 5).

If not tool-eligible, calls needle_engine.query(question) and returns:

The answer text.

Source nodes with node IDs, scores, and short text snippets.

Design rationale:

The agent is a thin wrapper over a specialized query engine:

It does not implement its own LLM; it delegates to the engine’s LLM.

Its only additional logic is routing to the external tool when appropriate.

4.3 ManagerAgent (router)
File: src/agents/manager.py

Receives the user question.

Decides which specialized agent to invoke.

Routing strategy:

Simple keyword heuristic:

If the question contains terms like “overview”, “summary”, “high-level”,
“timeline”, etc., route to SummarizationAgent.

Otherwise route to NeedleAgent.

Design rationale:

The router is intentionally simple and explainable.

A heuristic router is sufficient for the midterm and easy to defend:

It makes the separation between “summary” and “needle” behaviour explicit.

It avoids the complexity and extra latency of LLM-based routing.

5. External tool (MCP-style date-difference)
Tool implementation: src/mcp/client.py

python
Copy code
def compute_days_between_dates(start: str, end: str) -> int:
    """
    Compute the number of days between two ISO dates (YYYY-MM-DD).
    """
    ...
Integration point: NeedleAgent._maybe_answer_with_date_tool().

When a question clearly asks:

“How many days passed between the accident and the final settlement date?”

the NeedleAgent:

Recognizes the pattern via a simple string check.

Provides canonical accident and settlement dates from the synthetic claim.

Calls compute_days_between_dates(start_date, end_date).

Returns a deterministic textual answer including the day count.

Design rationale:

The tool demonstrates the MCP pattern (LLM + structured tool call) in a
minimal way:

The computation is delegated to a deterministic function, separate from
the LLM.

The answer is constructed by the agent, using the tool result.

For the midterm, the tool is implemented as a direct Python function rather
than a full MCP server:

Keeps the infrastructure simple and focused on the core concepts.

Still allows a clear explanation of how it would be exposed as an MCP tool
in a larger system.

6. LLM-as-a-judge evaluation
Evaluation code lives in src/eval/.

6.1 Test cases
File: src/eval/test_cases.json

Contains 8 test cases, each with:

id – numeric identifier

type – label (e.g., summary, needle, needle+tool)

question – input to the system

ground_truth – short, precise expected answer

Coverage:

High-level summary question.

Factual questions about:

Accident date

Hospital name

Refusal of ambulance

Settlement date

Settlement amount

Return-to-work date

A specific date-difference question (for the external tool path).

6.2 Judge script
File: src/eval/judge.py

Behaviour:

Builds the ManagerAgent via build_manager().

Loads test cases from test_cases.json.

For each case:

Calls manager.answer(question) to get:

System answer text.

Retrieved context snippets (from sources).

Concatenates context snippets into a single context string.

Calls a separate judge model (gpt-3.5-turbo) with:

Question

Ground truth

System answer

Retrieved context

The judge model outputs a JSON object with:

correctness_score (1–5)

relevance_score (1–5)

recall_score (1–5)

Short explanations for each dimension.

At the end, prints average scores across all test cases.

Design rationale:

Correctness: measures how close the system answer is to the ground truth.

Relevance: measures whether the retrieved context is actually about the
question.

Recall: measures whether the key information needed to answer the
question appears in the retrieved context.

Having three separate metrics makes it possible to distinguish:

Retrieval failures (low recall).

Over-broad or off-topic retrieval (low relevance).

Answer-generation issues (low correctness despite good context).

7. Running the system
7.1 Setup
Create and activate a virtual environment:

bash
Copy code
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\activate
Install dependencies:

bash
Copy code
pip install -r requirements.txt
Create a .env file in the project root:

text
Copy code
OPENAI_API_KEY=sk-...
7.2 Interactive Q&A
Run:

bash
Copy code
python .\src\main.py
Example questions:

Give me a brief overview of the claim, including the main events and dates.

Did the insured refuse ambulance transport at the scene?

How many days passed between the accident and the final settlement date?

The CLI prints:

The chosen agent (summarization or needle)

The answer text

7.3 Evaluation
Run:

bash
Copy code
python .\src\eval\judge.py
This will:

Execute all test cases in test_cases.json.

Print system answers and scores per case.

Print average correctness, relevance, and recall at the end.

8. Limitations and possible extensions
Current limitations:

Routing uses simple keyword heuristics rather than an LLM-based classifier.

The date-difference tool uses canonical dates from the synthetic data rather
than parsing them dynamically from retrieved text.

Only one claim is indexed; multi-claim scaling is not addressed.

The judge uses a single model and prompt; no ablation or inter-judge
agreement analysis is performed.

Potential future work:

Replace heuristic routing with an LLM classifier or a learned router.

Generalize the date tool to extract dates from retrieved context before
computing differences.

Extend the dataset to multiple claims and add filtering by claim ID.

Add a web or notebook front-end for easier experimentation.

This implementation focuses on clarity and explainability of design choices:
each layer (data, indexing, agents, tool, evaluation) is separated and can be
reasoned about independently while still forming a coherent end-to-end system.
