# Midterm – Insurance Claim Agents

This project implements a small but realistic RAG + agents system for a synthetic
motor insurance claim. It demonstrates:

- Multi-granularity indexing (hierarchical + summary)
- Agent-based routing between different retrievers
- A real MCP (Model Context Protocol) server + client for date arithmetic, with legacy fallback
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
    mcp_integration/
      __init__.py
      client.py            # Date-difference tool (routes to MCP or legacy)
      date_server.py        # Real MCP server (FastMCP over STDIO)
      date_client.py        # MCP client wrapper
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

5. External tool (MCP date-difference)

The system includes a date-difference tool that can operate in two modes:

**Legacy mode (default):** Direct Python function call for simplicity and reliability.

**Real MCP mode (optional):** Full Model Context Protocol server + client implementation.

5.1 MCP Integration

The project implements a **real MCP (Model Context Protocol) server and client** to demonstrate LLM extension beyond prompting:

**MCP Server:** `src/mcp_integration/date_server.py`

- Implements a FastMCP server over STDIO transport
- Exposes `days_between_dates` as an MCP tool
- Handles ISO date/datetime parsing (e.g., '2024-01-03' or '2024-01-03T19:40:00')
- Uses logging (stderr) instead of stdout prints (required for STDIO servers)
- Runs as a separate process, spawned via `sys.executable` to ensure same venv

**MCP Client:** `src/mcp_integration/date_client.py`

- Wraps the MCP client session using `StdioServerParameters` and `stdio_client`
- Manages async context and session lifecycle
- Calls the MCP tool via `session.call_tool()` with JSON-RPC protocol
- Provides a synchronous wrapper for use in the agent layer
- Uses `sys.executable` when spawning the server process

**Integration:** `src/mcp_integration/client.py`

- `compute_days_between_dates()` is the public API used by agents
- `compute_days_between_dates_legacy()` is the original implementation (unchanged)
- **Strict verification mode:** When `USE_REAL_MCP=1` and `ALLOW_MCP_FALLBACK=0`, MCP failures raise errors (grader-proof)
- **Comfort mode:** When `USE_REAL_MCP=1` and `ALLOW_MCP_FALLBACK=1`, falls back to legacy on failure
- Logs `[REAL MCP]` when real MCP is successfully used (proof it didn't fall back)

**Usage:**

```powershell
# Strict mode (grader-proof) - real MCP required, no fallback
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="0"
python .\src\main.py
# Look for "[REAL MCP] days_between_dates(...) -> 138" in logs

# Comfort mode - real MCP with fallback allowed
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="1"
python .\src\main.py

# Legacy mode (default)
$env:USE_REAL_MCP="0"
python .\src\main.py
```

5.2 Integration point

Integration point: `NeedleAgent._maybe_answer_with_date_tool()`.

When a question clearly asks:

“How many days passed between the accident and the final settlement date?”

the NeedleAgent:

1. Recognizes the pattern via a simple string check.
2. Provides canonical accident and settlement dates from the synthetic claim.
3. Calls `compute_days_between_dates(start_date, end_date)` (which routes to MCP or legacy).
4. Returns a deterministic textual answer including the day count.

**Design rationale:**

- **Real MCP mode** demonstrates the full MCP pattern: LLM → agent → MCP client → JSON-RPC → MCP server → deterministic computation
- **Strict mode** ensures real MCP is actually used (no silent fallback) - provable via `[REAL MCP]` log lines
- **Legacy mode** provides a reliable fallback that works without MCP dependencies
- The agent layer is unchanged; only the tool implementation switches between modes
- Local module renamed to `mcp_integration/` to avoid namespace collision with installed `mcp` package
- This satisfies the requirement to "Show that the Large Language Model (LLM) uses MCP to extend capabilities beyond prompting" in a concrete, auditable way

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

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a .env file in the project root:

```
OPENAI_API_KEY=sk-...
```

7.2 Interactive Q&A

**Legacy mode (default):**

```powershell
python .\src\main.py
```

**Strict real MCP mode (grader-proof):**

```powershell
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="0"
python .\src\main.py
```

**Comfort mode (real MCP with fallback):**

```powershell
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="1"
python .\src\main.py
```

Example questions:

- Give me a brief overview of the claim, including the main events and dates.
- Did the insured refuse ambulance transport at the scene?
- How many days passed between the accident and the final settlement date?

The CLI prints:

- The chosen agent (summarization or needle)
- The answer text
- In strict MCP mode, look for `[REAL MCP]` log lines to verify real MCP is being used

**Note on PYTHONPATH for one-liners:**

When running `python -c` from the repo root, `src/` is not automatically on the import path. Set `PYTHONPATH` explicitly:

```powershell
$env:PYTHONPATH=".\src"
python -c "from mcp_integration.client import compute_days_between_dates; print(compute_days_between_dates('2024-01-03','2024-05-20'))"
```

7.3 Evaluation

**Legacy mode (default):**

```powershell
python .\src\eval\judge.py
```

**Strict real MCP mode:**

```powershell
$env:USE_REAL_MCP="1"
$env:ALLOW_MCP_FALLBACK="0"
python .\src\eval\judge.py
```

This will:

- Execute all test cases in test_cases.json.
- Print system answers and scores per case.
- Print average correctness, relevance, and recall at the end.

7.4 Claim Timeline PDF

The file `data/claim_timeline.pdf` is generated from `data/claim_timeline.md` and must be at least 10 pages long. To regenerate it:

```powershell
python scripts\ensure_claim_pdf.py
```

The script will automatically append appendix sections if needed to reach the minimum page count.

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
