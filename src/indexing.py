import os
from pathlib import Path

from dotenv import load_dotenv

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    SummaryIndex,
    Settings,
)
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.query_engine import RetrieverQueryEngine


# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def init_llama_settings() -> None:
    """
    Load environment variables and configure the global LlamaIndex settings.
    """
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Create a .env file in the project root with OPENAI_API_KEY=..."
        )

    # Configure LLM + embedding model (adjust models if needed)
    Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0.0)
    Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

    # Optional global chunk size hint (not critical but fine to set)
    Settings.chunk_size = 1024


def build_indexes():
    """
    Build:
    - hierarchical nodes over the claim timeline
    - a VectorStoreIndex on leaf nodes
    - an AutoMergingRetriever
    - a SummaryIndex over the full documents

    Returns a dict with the main objects.
    """
    init_llama_settings()

    # 1. Load the claim timeline document(s)
    documents = SimpleDirectoryReader(str(DATA_DIR)).load_data()
    if not documents:
        raise RuntimeError(f"No documents found in {DATA_DIR}")

    # 2. Build hierarchical nodes (multi-granularity chunking)
    # Default chunk sizes roughly: [2048, 512, 128] – we make them explicit.
    node_parser = HierarchicalNodeParser.from_defaults(
        chunk_sizes=[1024, 512, 128]
    )
    nodes = node_parser.get_nodes_from_documents(documents)

    # Leaf nodes are the smallest chunks; these will be embedded.
    leaf_nodes = get_leaf_nodes(nodes)

    # 3. Set up storage + base vector index on leaf nodes
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)

    base_index = VectorStoreIndex(
        leaf_nodes,
        storage_context=storage_context,
    )

    base_retriever = base_index.as_retriever(similarity_top_k=6)

    # 4. Auto-merging retriever: replaces many tiny chunks
    #    with their parents when that’s more coherent.
    auto_merging_retriever = AutoMergingRetriever(
        base_retriever,
        storage_context=storage_context,
        verbose=True,
    )

    # 5. Summary index over the whole documents
    #    (used later by the Summarization Agent).
    summary_index = SummaryIndex.from_documents(documents)

    return {
        "storage_context": storage_context,
        "documents": documents,
        "nodes": nodes,
        "leaf_nodes": leaf_nodes,
        "base_index": base_index,
        "auto_retriever": auto_merging_retriever,
        "summary_index": summary_index,
    }

def get_query_engines():
    """
    Convenience helper:
    - builds indexes
    - returns two query engines:
      * summary_engine: for high-level / timeline questions
      * needle_engine: for precise, 'needle-in-haystack' questions
    """
    idx = build_indexes()

    # High-level summary engine over the SummaryIndex
    summary_engine = idx["summary_index"].as_query_engine(
        response_mode="tree_summarize"
    )

    # Needle engine over the auto-merging retriever
    needle_engine = RetrieverQueryEngine.from_args(
        idx["auto_retriever"],
        response_mode="compact",
    )

    return {
        "summary_engine": summary_engine,
        "needle_engine": needle_engine,
    }

if __name__ == "__main__":
    idx = build_indexes()
    print("✅ Indexes built successfully.")
    print(f"- Documents loaded: {len(idx['documents'])}")
    print(f"- Total nodes:      {len(idx['nodes'])}")
    print(f"- Leaf nodes:       {len(idx['leaf_nodes'])}")
